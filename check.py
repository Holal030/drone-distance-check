"""Расчёт только трёх расстояний на учебной геометрии, без вывода о допуске полёта."""
import argparse
import json
import math
import time
from pathlib import Path

from shapely.geometry import shape


BASE = Path(__file__).resolve().parent


def evaluate(case, rules):
    result = {'id': case['id'], 'status': 'insufficient_data', 'checks': []}
    if case.get('as_of') != rules['snapshot_date']:
        return {**result, 'reason': 'Для этой даты редакция норм не проверена'}
    if case.get('crs') != 'LOCAL_METRES':
        return {**result, 'reason': 'Нужны координаты в общей плоской системе в метрах'}
    if case.get('operation') != 'bas_pesticide_application':
        return {**result, 'reason': 'Этот вид работ в примере не поддержан'}
    try:
        field = shape(case['field'])
        if field.geom_type != 'Polygon' or not field.is_valid or field.is_empty or field.area <= 0:
            raise ValueError('Некорректный контур участка')
        bounds = field.bounds
        if not all(math.isfinite(v) for v in bounds):
            raise ValueError('Неконечные координаты участка')
        for rule in rules['rules']:
            kind = rule['object_kind']
            if case.get('catalog_complete', {}).get(kind) is not True:
                result['checks'].append({'rule': rule['id'], 'status': 'insufficient_data',
                                         'reason': 'Полнота объектов этой категории не подтверждена'})
                continue
            objects = [o for o in case.get('objects', []) if o.get('kind') == kind]
            for obj in objects:
                geometry = shape(obj['geometry'])
                if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in {'Point', 'Polygon'}:
                    raise ValueError('Нет пригодной геометрии объекта ' + obj.get('id', ''))
                distance = field.distance(geometry)
                if not math.isfinite(distance):
                    raise ValueError('Не удалось вычислить расстояние')
                # Для п. 282 "не менее" допускает равенство. Для п. 286 в примере
                # "в пределах" консервативно включает граничное значение.
                conflict = distance <= rule['distance_m'] if rule['comparison'] == 'within_inclusive' else distance < rule['distance_m']
                result['checks'].append({'rule': rule['id'], 'source_point': rule['point'],
                    'object': obj['id'], 'distance_m': round(distance, 6),
                    'threshold_m': rule['distance_m'], 'status': 'conflict' if conflict else 'no_conflict_in_example'})
            if not objects:
                result['checks'].append({'rule': rule['id'], 'status': 'no_objects_in_complete_test_catalog'})
    except (KeyError, TypeError, ValueError) as error:
        return {**result, 'reason': str(error)}
    states = {c['status'] for c in result['checks']}
    # Найденное нарушение показываем и при неполноте других входов.
    result['status'] = ('conflict' if 'conflict' in states else 'insufficient_data' if 'insufficient_data' in states
                        else 'no_conflict_in_example')
    result['complete_input'] = 'insufficient_data' not in states
    return result


def run(output):
    started = time.perf_counter()
    rules = json.loads((BASE / 'rules.json').read_text(encoding='utf-8'))
    cases = json.loads((BASE / 'cases.json').read_text(encoding='utf-8'))
    results = [evaluate(c, rules) for c in cases]
    failures = []
    for case, result in zip(cases, results):
        if result['status'] != case['expected_status']:
            failures.append(case['id'] + ': неверный статус')
        if 'expected_distance_m' in case:
            observed = [x['distance_m'] for x in result['checks'] if 'distance_m' in x]
            if len(observed) != 1 or not math.isclose(observed[0], case['expected_distance_m'], abs_tol=1e-6):
                failures.append(case['id'] + ': неверное расстояние')
    report = {'snapshot_date': rules['snapshot_date'], 'synthetic_geometry': True,
              'cases': len(cases), 'passed': len(cases)-len({f.split(':')[0] for f in failures}),
              'failures': failures, 'calculation_seconds': round(time.perf_counter()-started, 6),
              'results': results, 'scope': 'Только перечисленные расстояния; не разрешение обработки или полёта'}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=BASE/'results')
    args = parser.parse_args()
    report = run(args.output)
    print(f"Проверки: {report['passed']}/{report['cases']}; расчёт {report['calculation_seconds']} с")
    raise SystemExit(bool(report['failures']))

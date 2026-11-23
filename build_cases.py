"""Фикстуры с расстояниями, заданными до расчёта: прямоугольник x=0..100, y=0..100."""
import copy
import json
from pathlib import Path

base = {'as_of': '2026-11-17', 'crs': 'LOCAL_METRES', 'operation': 'bas_pesticide_application',
        'field': {'type': 'Polygon', 'coordinates': [[[0,0],[100,0],[100,100],[0,100],[0,0]]]},
        'catalog_complete': {'settlement': True, 'permanent_apiary': True, 'person_or_domestic_animal': True},
        'objects': []}
cases=[]
for kind, threshold in [('settlement',700), ('permanent_apiary',5000), ('person_or_domestic_animal',700)]:
    for offset in [-1,0,1]:
        distance=threshold+offset
        case=copy.deepcopy(base)
        # Объект справа от вертикальной границы x=100, напротив середины стороны.
        geom={'type':'Point','coordinates':[100+distance,50]}
        if kind in {'settlement','permanent_apiary'}:
            x=100+distance
            geom={'type':'Polygon','coordinates':[[[x,20],[x+20,20],[x+20,80],[x,80],[x,20]]]}
        case.update(id=f'{kind}_{distance}', objects=[{'id':'object1','kind':kind,'geometry':geom}],
                    expected_distance_m=distance,
                    expected_status='conflict' if offset<0 or (offset==0 and kind=='person_or_domestic_animal') else 'no_conflict_in_example')
        cases.append(case)

inside=copy.deepcopy(base)
inside.update(id='person_inside_field',objects=[{'id':'person','kind':'person_or_domestic_animal','geometry':{'type':'Point','coordinates':[50,50]}}],expected_distance_m=0,expected_status='conflict')
cases.append(inside)
for name, change in [
    ('unknown_apiaries',{'catalog_complete':{'settlement':True,'permanent_apiary':False,'person_or_domestic_animal':True}}),
    ('wrong_date',{'as_of':'2026-11-18'}),
    ('geographic_degrees',{'crs':'EPSG:4326'}),
    ('other_operation',{'operation':'ordinary_flight'}),
    ('invalid_field',{'field':{'type':'Polygon','coordinates':[[[0,0],[100,100],[0,100],[100,0],[0,0]]]}}),
    ('missing_geometry',{'objects':[{'id':'missing','kind':'permanent_apiary'}]}),
]:
    case=copy.deepcopy(base);case.update(id=name,expected_status='insufficient_data',**change);cases.append(case)
conflict_unknown=copy.deepcopy(cases[0]);conflict_unknown.update(id='conflict_with_unknown_apiaries')
conflict_unknown['catalog_complete']['permanent_apiary']=False
cases.append(conflict_unknown)
Path(__file__).with_name('cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8')

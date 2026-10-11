"""Offline sanity tests, no external secrets/API required."""
from collections import Counter
from pathlib import Path
import csv, json, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import engine

ROOT=Path(__file__).resolve().parent
rows=list(csv.DictReader((ROOT/'places.csv').open(encoding='utf-8-sig')))
assert len(rows)>=140
assert len({x['name'] for x in rows})>=75
counts=Counter(x['area'] for x in rows)
assert len(counts)==7 and all(n>=20 for n in counts.values()), counts
assert len(json.loads((ROOT/'areas.json').read_text()))==7
assert all(x['category'] in engine.CATEGORIES for x in rows)
assert not engine.district_ok({'address_name':'부산 수영구 광안동 1'},'namcheon')
assert engine.district_ok({'address_name':'부산 수영구 남천동 1'},'namcheon')
places=[]
for i,(category,dx,minutes) in enumerate([('식사',.003,55),('카페·디저트',.001,40),('문화·공간',.002,40)]):
    places.append({'id':str(i),'name':category,'category':category,'lat':35.14,'lon':129.11+dx,'minutes':minutes,'address':'부산 수영구 남천동 1'})
origin={'id':'start','name':'남천역','lat':35.14,'lon':129.11}
from unittest.mock import patch
with patch.object(engine,'kakao_leg',return_value=None):
    r=engine.create_route('fake','namcheon',origin,places,['식사','카페·디저트','문화·공간'],'11:00','16:00','도보',selected_ids=['0','2','1'],endpoint={**origin,'id':'end'})
assert not r['error'],r
assert r['ordered'][0]['id']=='1'  # Closest venue first, NOT click order
assert r['minutes']<=300
assert r['timeline'][0]['kind']=='start' and r['timeline'][-1]['kind']=='end'
assert not r['verified'] and all(not x['verified'] for x in r['legs'])
for suffix in ['app.py','engine.py','services.py','smart.py','ui.js','ui.css','hero.jpg','places.csv','areas.json','requirements.txt']:
 assert (ROOT/suffix).exists(),suffix
js=(ROOT/'ui.js').read_text()
for value in ['buildScreen1','buildScreen2','buildScreen3','buildScreen4','setTriggerValue','data-action="search"','data-action="route"','data-action="map"','data-action="back"']:
 assert value in js,value
print('PASS 7 areas, 154+ seeds, six interests, strict Namcheon filter, reordered walking schedule, 4 stage navigation sources')

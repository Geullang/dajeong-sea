"""Kakao place validation, public road/pedestrian routing and itinerary calculations.
Never represent straight-line approximations as verified routing.
"""
import csv, json, math, re, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote
from functools import lru_cache
import requests
ROOT=Path(__file__).resolve().parent
AREAS=json.loads((ROOT/'data/areas.json').read_text(encoding='utf-8'))
with (ROOT/'data/places.csv').open(encoding='utf-8-sig',newline='') as f:SEEDS=list(csv.DictReader(f))
AREA={a['id']:a for a in AREAS}
CATEGORIES=['식사','카페·디저트','독립서점','소품샵','문화·공간','자연·풍경']
DISCOVERY={
 '식사':['맛집','한식','식당'],
 '카페·디저트':['로스터리','베이커리','카페'],
 '독립서점':['독립서점','책방'],
 '소품샵':['소품샵','편집샵'],
 '문화·공간':['전시','문화공간','박물관','갤러리'],
 '자연·풍경':['공원','전망대','산책로']
}

def distance(a,b):
 if not a or not b:return float('inf')
 lat1,lon1=a;lat2,lon2=b;r=6371.0088
 p1,p2=map(math.radians,[lat1,lat2]);dl=p2-p1;da=math.radians(lon2-lon1)
 v=math.sin(dl/2)**2+math.cos(p1)*math.cos(p2)*math.sin(da/2)**2
 return r*2*math.asin(min(1,math.sqrt(v)))

def kakao_search(key,query,center=None,radius=None,page=1):
 if not key:return []
 args={'query':query,'size':15,'page':page}
 if center:
  args.update({'y':center[0],'x':center[1],'sort':'distance'})
 if radius:args['radius']=int(radius)
 try:
  r=requests.get('https://dapi.kakao.com/v2/local/search/keyword.json',params=args,headers={'Authorization':'KakaoAK '+key},timeout=4)
  r.raise_for_status()
  return r.json().get('documents',[])
 except (requests.RequestException,ValueError):return []

def find_origin(key,text):
 text=(text or '').strip()
 if not text:return None
 docs=kakao_search(key,'부산 '+text)
 if not docs:
  try:
   r=requests.get('https://dapi.kakao.com/v2/local/search/address.json',params={'query':text},headers={'Authorization':'KakaoAK '+key},timeout=6)
   docs=r.json().get('documents',[]) if r.ok else []
  except Exception:docs=[]
 if not docs:return None
 d=docs[0]
 try:
  return {'name':d.get('place_name') or text,'address':d.get('road_address_name') or d.get('address_name') or text,'lat':float(d['y']),'lon':float(d['x'])}
 except (TypeError,KeyError,ValueError):return None

def _simple(s):return re.sub(r'[^0-9a-z가-힣]','',s.lower())

def match_exact(name,doc):
 a=_simple(name);b=_simple(doc.get('place_name',''))
 if not a or not b:return False
 return a in b or b in a if min(len(a),len(b))>=4 else a==b

def category_for(doc):
 tag=doc.get('category_name','');name=doc.get('place_name','')
 if any(w in name+tag for w in ['독립서점','책방']):return '독립서점'
 if any(w in name+tag for w in ['소품','문구','편집샵','편집숍','굿즈','공예품']):return '소품샵'
 if any(w in name+tag for w in ['베이커리','빵집','카페','커피','제과','디저트','로스터','다방']):return '카페·디저트'
 if any(w in tag for w in ['공원','해수욕','관광명소','전망대','자연','산책','해변']):return '자연·풍경'
 if any(w in name+tag for w in ['갤러리','박물관','미술관','전시','문화시설','문화공간','공연장','도서관','문화센터','서점']):return '문화·공간'
 if doc.get('category_group_code')=='CE7':return '카페·디저트'
 if doc.get('category_group_code')=='FD6' or '음식점' in tag:return '식사'
 if '관광' in tag:return '문화·공간'
 return None

def cleaned(doc,seed=None):
 try:
  lat=float(doc['y']);lon=float(doc['x'])
 except (KeyError,TypeError,ValueError):return None
 cat=(seed or {}).get('category') or category_for(doc)
 if cat not in CATEGORIES:return None
 name=(seed or {}).get('name') or doc['place_name']
 why=(seed or {}).get('why') or '부산의 동네 문화와 분위기를 살피며 모둠의 취향에 맞는지 확인해 보세요.'
 intro=(seed or {}).get('description') or f"카카오맵에 등록된 {cat} 장소입니다. 아래 상세 정보에서 방문 가능 여부를 확인해 보세요."
 return {'name':name,'kakao_name':doc.get('place_name',''),'category':cat,
  'description':intro,'why':why,
  'minutes':int((seed or {}).get('minutes') or {'식사':65,'카페·디저트':35,'독립서점':30,'소품샵':25,'문화·공간':45,'자연·풍경':30}[cat]),
  'notice':(seed or {}).get('notice') or '방문 전 영업시간·휴무 및 예약 가능 여부를 확인하세요.',
  'budget_note':(seed or {}).get('budget_note') or '가격·입장료 확인 필요',
  'lat':lat,'lon':lon,'address':doc.get('road_address_name') or doc.get('address_name',''),
  'phone':doc.get('phone') or '', 'url':doc.get('place_url') or '',
  'kakao_id':str(doc.get('id','')),'editorial':bool(seed), 'hours':'운영시간·휴무: 카카오 장소 상세에서 확인',
  'reservation':'예약·단체석: 장소별 확인 필요'}

def candidates_for_area(area_id,key,max_count=50):
 """Show only Kakao-matched venues; widen with nearby actual POI searches if editorial entries are missing."""
 area=AREA[area_id];center=area['center'];radius=area['radius'];out=[];used=set()
 # Fail fast if Kakao is unreachable; do not execute dozens of stalled queries.
 if not kakao_search(key,'카페',center,radius):return []
 def add(doc,seed=None):
  v=cleaned(doc,seed)
  if not v or v['kakao_id'] in used:return False
  if distance(center,(v['lat'],v['lon']))>radius/1000+.4:return False
  # Kakao may return a different region for generic names; location radius is decisive.
  out.append(v);used.add(v['kakao_id']);return True
 for seed in SEEDS:
  if seed['area']!=area_id:continue
  # first query nearby, then name + 부산 to discover alternate names
  docs=kakao_search(key,seed['name'],center,radius)
  doc=next((d for d in docs if match_exact(seed['name'],d)),None)
  if doc:add(doc,seed)
 # Curated ranks come first. Discovery consists only of actual Kakao place records.
 if len(out)<max(20,max_count):
  for cat in CATEGORIES:
   if len(out)>=max_count:break
   for term in DISCOVERY[cat]:
    if len(out)>=max_count or sum(x['category']==cat for x in out)>=8:break
    for p in [1,2]:
     if len(out)>=max_count or sum(x['category']==cat for x in out)>=8:break
     for d in kakao_search(key,term,center,radius,page=p):
      # Reject off-topic results and incorrect categories; no 'fake' filler.
      actual=category_for(d)
      if actual!=cat:continue
      if any(x in d.get('place_name','') for x in ['CU ','GS25','세븐일레븐','이마트24','스타벅스','투썸플레이스','메가MGC']):continue
      add(d)
 if len(out)>=max_count:
  # keep all curated first, then diverse other places
  out=out[:max_count]
 return out

def decode_polyline(shape,precision=6):
 coords=[];index=0;lat=lon=0;factor=10**precision
 while index<len(shape):
  vals=[]
  for _ in range(2):
   result=shift=0
   while True:
    b=ord(shape[index])-63;index+=1;result|=(b&0x1f)<<shift;shift+=5
    if b<0x20:break
   vals.append(~(result>>1) if result&1 else (result>>1))
  lat+=vals[0];lon+=vals[1];coords.append((lat/factor,lon/factor))
 return coords

def valhalla_route(a,b,mode):
 costing='pedestrian' if mode=='도보' else 'auto'
 payload={'locations':[{'lat':a[0],'lon':a[1]},{'lat':b[0],'lon':b[1]}],
  'costing':costing,'directions_options':{'units':'kilometers'}}
 try:
  r=requests.get('https://valhalla1.openstreetmap.de/route',params={'json':json.dumps(payload,separators=(',',':'))},timeout=12)
  r.raise_for_status();t=r.json()['trip']
  legs=t['legs'];secs=float(t['summary']['time']);kilometers=float(t['summary']['length'])
  shape=[]
  for leg in legs:shape.extend(decode_polyline(leg['shape'],6))
  if not shape or secs<0:raise ValueError('empty route')
  return {'minutes':math.ceil(secs/60),'km':kilometers,'shape':shape,'verified':True,'provider':'Valhalla/OSM 공개 경로'}
 except (requests.RequestException,ValueError,KeyError,IndexError,TypeError):
  km=distance(a,b)
  factor=1.4 if mode=='도보' else 1.5
  speed=4.0 if mode=='도보' else 18.0
  return {'minutes':max(3,math.ceil(km*factor/speed*60)),'km':round(km*factor,2),
   'shape':[a,b],'verified':False,'provider':'직선거리 보정 추정(실제 길찾기 아님)'}


def _estimated_leg(a,b,mode):
 km=distance(a,b)
 factor=1.4 if mode=='도보' else 1.5
 speed=4.0 if mode=='도보' else 18.0
 return {'minutes':max(3,math.ceil(km*factor/speed*60)),'km':round(km*factor,2),
         'shape':[a,b],'verified':False,'provider':'직선거리 보정 추정(실제 길찾기 아님)'}

def _valhalla_batch(points,mode):
 payload={'locations':[{'lat':p[0],'lon':p[1]} for p in points],
          'costing':'pedestrian' if mode=='도보' else 'auto',
          'directions_options':{'units':'kilometers'}}
 r=requests.get('https://valhalla1.openstreetmap.de/route',
     params={'json':json.dumps(payload,separators=(',',':'))},
     headers={'X-Client-Id':'dajeong-sea.streamlit.app','User-Agent':'dajeong-sea-mulkkobang/1.0'},timeout=14)
 r.raise_for_status()
 t=r.json()['trip'];legs=t['legs']
 if len(legs)!=len(points)-1:raise ValueError('leg count mismatch')
 result=[]
 for leg in legs:
  summary=leg['summary'];shape=decode_polyline(leg['shape'],6)
  if len(shape)<2:raise ValueError('invalid geometry')
  result.append({'minutes':max(1,math.ceil(float(summary['time'])/60)),
   'km':float(summary['length']),'shape':shape,'verified':True,'provider':'Valhalla/OSM 공개 경로'})
 return result

def _osrm_batch(points,mode):
 # Dedicated foot/car demo profiles (NOT router.project-osrm.org driving for pedestrians).
 profile='routed-foot' if mode=='도보' else 'routed-car'
 coords=';'.join(f'{lon:.6f},{lat:.6f}' for lat,lon in points)
 url=f'https://routing.openstreetmap.de/{profile}/route/v1/driving/{coords}'
 r=requests.get(url,params={'steps':'true','geometries':'geojson','overview':'full'},
     headers={'User-Agent':'dajeong-sea-mulkkobang/1.0'},timeout=14)
 r.raise_for_status();v=r.json();legs=v['routes'][0]['legs']
 if len(legs)!=len(points)-1:raise ValueError('leg count mismatch')
 result=[]
 for leg in legs:
  shape=[]
  for step in leg.get('steps',[]):
   for lon,lat in step.get('geometry',{}).get('coordinates',[]):shape.append((lat,lon))
  if len(shape)<2:raise ValueError('invalid foot/car geometry')
  result.append({'minutes':max(1,math.ceil(float(leg['duration'])/60)),
    'km':float(leg['distance'])/1000,'shape':shape,'verified':True,'provider':'OSRM/OSM 공개 경로'})
 return result

def batch_routes(points,mode):
 """At most two routing requests for the whole route, so public demo servers aren't hammered.
 A failed real network route returns explicit non-verified estimates.
 """
 if len(points)<2:return []
 for backend in (_valhalla_batch,_osrm_batch):
  try:return backend(points,mode)
  except (requests.RequestException,ValueError,TypeError,KeyError,IndexError):continue
 return [_estimated_leg(points[i],points[i+1],mode) for i in range(len(points)-1)]

def optimize_order(origin,spots):
 """Haversine is used ONLY for sorting; final leg times query the road graph."""
 if len(spots)<2:return spots[:]
 remain=spots[:];out=[];cur=origin
 while remain:
  best=min(remain,key=lambda p:distance(cur,(p['lat'],p['lon'])))
  out.append(best);remain.remove(best);cur=(best['lat'],best['lon'])
 # Two-opt reduces crossovers without masquerading as pedestrian routing.
 def cost(seq):
  pos=origin;val=0
  for p in seq:
   nxt=(p['lat'],p['lon']);val+=distance(pos,nxt);pos=nxt
  return val
 for loop in range(2):
  improved=False
  for i in range(len(out)-2):
   for j in range(i+2,len(out)+1):
    cand=out[:i]+list(reversed(out[i:j]))+out[j:]
    if cost(cand)+1e-8<cost(out):out=cand;improved=True
  if not improved:break
 return out

def plan_schedule(origin,spots,start,end,mode='도보',meal_buffer=0,route_fn=valhalla_route,batch_route_fn=None):
 """start/end are HH:MM. Does not pretend unverified hours are known."""
 day=datetime(2027,1,9)
 beginning=datetime.combine(day.date(),datetime.strptime(start,'%H:%M').time())
 deadline=datetime.combine(day.date(),datetime.strptime(end,'%H:%M').time())
 if deadline<=beginning:raise ValueError('종료 시각은 시작 시각보다 늦어야 합니다.')
 if not spots:raise ValueError('장소를 한 곳 이상 선택하세요.')
 order=optimize_order((origin['lat'],origin['lon']),spots)
 coords=[(origin['lat'],origin['lon'])]+[(p['lat'],p['lon']) for p in order]
 batch=(batch_route_fn or batch_routes)(coords,mode) if route_fn is valhalla_route else None
 if batch is not None and len(batch)!=len(order):raise ValueError('경로 구간 수가 맞지 않습니다.')
 at=beginning;last=(origin['lat'],origin['lon']);legs=[];schedule=[]
 for idx,spot in enumerate(order):
  here=(spot['lat'],spot['lon'])
  leg=batch[idx] if batch is not None else route_fn(last,here,mode)
  travel=int(leg['minutes'])+(5 if mode=='택시' else 0)
  at+=timedelta(minutes=travel)
  arrive=at
  stay=int(spot['minutes'])+int(meal_buffer if spot['category']=='식사' else 0)
  at+=timedelta(minutes=stay)
  schedule.append({'number':idx+1,'name':spot['name'],'category':spot['category'],
   'arrive':arrive.strftime('%H:%M'),'leave':at.strftime('%H:%M'),'stay':stay,
   'travel':travel,'trip_km':leg['km'],'verified':leg['verified'],
   'provider':leg['provider'],'notice':spot['notice'],'address':spot['address']})
  legs.append(leg);last=here
 return {'schedule':schedule,'legs':legs,'ordered':order,'start':start,'end':at.strftime('%H:%M'),
  'deadline':end,'minutes':int((at-beginning).total_seconds()//60),'fits':at<=deadline,
  'over_minutes':max(0,int((at-deadline).total_seconds()//60)),
  'all_verified':all(x['verified'] for x in legs)}

def route_link(locations,mode='도보'):
 """User-facing Kakao Maps place location; separate from Valhalla real-route output."""
 parts=[]
 for p in locations:
  parts.append(quote(p['name']))
 return 'https://map.kakao.com/?q='+quote('부산 '+locations[-1]['name']) if locations else 'https://map.kakao.com/'

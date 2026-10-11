"""Kakao place validation, public road/pedestrian routing and itinerary calculations.
Never represent straight-line approximations as verified routing.
"""
import csv, json, math, re, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote
from functools import lru_cache
import requests
# v2 deployment-safe data loader: supports flat root uploads, original folders,
# and an embedded copy if either data file is accidentally omitted on GitHub.
import base64, zlib, io
ROOT=Path(__file__).resolve().parent
_EMBEDDED_AREAS="eNqVlN2K2lAQx+/3KQ5ey5IPo2tfZdmLrIordBX8oJRSSFdbRAUt1Ro/t0u16pKl2RqLgtB36WVmAn2ETqJLq55YCglk5nDO5Hf+/5nzE8Ze0ctYIBUPPGOBtHodu0pk0oHgJktxws3DzRS/9aHeeVqIJdL5RJaWzr2YMVk5FUNiNLgNRSl6KgpRyQsvtpuyajxVyNEmSRKEbS5XuMyn8s83VVYLBsUSFsvY0Rg+vsWBzsBY4nDM8MbAgfVUPhWjf6Qdv27HjQClXgf3SZIv1HRSPQCxrffYKsMXwz3enq/pXJO+jmIpsrSDJUYjPlgyF2tbs6bZiwaM1wzMJgzWMLdgZjK6VnqcYfkQrVbho8Uz1xmuSPUS3E+ddo0hHV/T/gGl7GoVCvGhZIULhZ9a2Gu4N0gCOZ2mbZJiAws/WjjRoNJkqI+cXolD9YNP9ZKIkvHMPhTqb4jrGIpwFvmbRFBEPkiYr46rRnXk6TIp4+e10+ozez6F+5lnD30EQx0afea0HuyFsc/zs7fwwVFjV/l9GKdlYdciaRh2m05leVSh8I4+IZ9Wkn2o6h0wH7FkeApNyPEmVvtO1dy01BpWvUNpuiM+Sz6rptL+LPQFcw3bFprT40TiruciEcVHKoEP9XXp1A1sN7DUp8Z5oJlAcZDhuzuyo72qkfU4VEU+1WUmVzhoobmFZZ0uzx0PYM42RjgKJcjijv2k8Nl/KfXHYduJBN81dyiRTpvqzF6acDc4BPvQ9cBOLn4D5pr5BA=="
_EMBEDDED_PLACES="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"
def _data_bytes(filename, fallback):
    for candidate in (ROOT/'data'/filename, ROOT/filename):
        if candidate.is_file():
            return candidate.read_bytes()
    return zlib.decompress(base64.b64decode(fallback))
AREAS=json.loads(_data_bytes('areas.json', _EMBEDDED_AREAS).decode('utf-8-sig'))
SEEDS=list(csv.DictReader(io.StringIO(_data_bytes('places.csv', _EMBEDDED_PLACES).decode('utf-8-sig'))))
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
  # Kakao center-radius alone included venues outside Namcheon-dong. Require the legal address as well.
  if area_id=='namcheon':
   land_addr=doc.get('address_name','')
   if not re.search(r"(?:부산(?:광역시)?\s+)?수영구\s+남천동(?:\s|$)",land_addr):return False
  # For other areas, apply the documented area center radius pending hand-curated polygons.
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

def plan_schedule(origin,spots,start,end,mode='도보',meal_buffer=0,route_fn=valhalla_route,batch_route_fn=None,fixed_order=False):
 """start/end are HH:MM. Does not pretend unverified hours are known."""
 day=datetime(2027,1,9)
 beginning=datetime.combine(day.date(),datetime.strptime(start,'%H:%M').time())
 deadline=datetime.combine(day.date(),datetime.strptime(end,'%H:%M').time())
 if deadline<=beginning:raise ValueError('종료 시각은 시작 시각보다 늦어야 합니다.')
 if not spots:raise ValueError('장소를 한 곳 이상 선택하세요.')
 order=spots[:] if fixed_order else optimize_order((origin['lat'],origin['lon']),spots)
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

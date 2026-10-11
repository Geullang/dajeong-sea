"""Real Kakao place and pedestrian routing, compact automatic route planning.
No fabricated venues, photo licences, or map-travel-time claims.
"""
import concurrent.futures, base64, math, re, requests
from datetime import datetime, timedelta
from itertools import permutations, product
from functools import lru_cache
from services import AREA, AREAS, SEEDS, kakao_search, cleaned, match_exact, find_origin, distance, CATEGORIES

SIGHTS={'독립서점','소품샵','문화·공간','자연·풍경'}

def district_ok(doc, area_id):
    addr=(doc.get('address_name') or doc.get('road_address_name') or '')
    if area_id=='namcheon':
        # Strict legal district matching: radius alone is not enough.
        return bool(re.search(r'수영구\s+남천동(?:\s|$)',addr))
    center=AREA[area_id]['center']
    return distance(center,(float(doc['y']),float(doc['x']))) <= AREA[area_id]['radius']/1000

def _verify(seed, area_id, key):
    if not key:return None
    area=AREA[area_id]
    docs=kakao_search(key,seed['name'],area['center'],area['radius'])
    for doc in docs:
        if match_exact(seed['name'],doc) and district_ok(doc,area_id):
            place=cleaned(doc,seed)
            if place:
                place['id']=f"{area_id}:{place['kakao_id']}"
                place['area']=area_id
                return place
    return None

@lru_cache(maxsize=32)
def verified_places(area_id,key):
    seeds=[x for x in SEEDS if x['area']==area_id]
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        results=list(pool.map(lambda x:_verify(x,area_id,key),seeds))
    seen=set();res=[]
    for x in results:
        if x and x['kakao_id'] not in seen:
            seen.add(x['kakao_id']);res.append(x)
    return res

def compact_recommendations(places,interests,limit=3):
    # Prioritize one from each requested category and no endless catalog.
    out=[]
    for category in interests:
        catlist=[p for p in places if p['category']==category]
        out.extend(catlist[:limit])
    return out

def route_length_estimate(a,b,mode='도보'):
    return distance((a['lat'],a['lon']),(b['lat'],b['lon']))*(1.35 if mode=='도보' else 1.5)

def _rough_minutes(a,b,mode):
    return route_length_estimate(a,b,mode)/ (4 if mode=='도보' else 18)*60

def _candidate_sequences(origin,places,interests,budget_mins,mode,selected_ids=None):
    if selected_ids:
        pool=[p for p in places if p['id'] in selected_ids]
        if not pool:return []
        # Even manually selected candidates should be reordered.
        bundles=[tuple(pool[:5])]
    else:
        meal=[p for p in places if p['category']=='식사'][:4] if '식사' in interests else []
        cafe=[p for p in places if p['category']=='카페·디저트'][:4] if '카페·디저트' in interests else []
        sights=[p for p in places if p['category'] in interests and p['category'] in SIGHTS][:7]
        groups=([meal] if meal else []) + ([cafe] if cafe else []) + ([sights] if sights else [])
        if not groups:return []
        bundles=list(product(*groups))
        if budget_mins>=240 and sights:
            for m in (meal or [None]):
                for c in (cafe or [None]):
                    for i in range(min(5,len(sights))):
                        for j in range(i+1,min(5,len(sights))):
                            bundles.append(tuple(x for x in (m,c,sights[i],sights[j]) if x))
    results=[]
    for bundle in bundles:
        if len({p['id'] for p in bundle})!=len(bundle):continue
        # Limit scan to no more than five stops to keep routing affordable.
        for order in permutations(bundle):
            a=origin;travel=0;dist=0;stay=0
            for p in order:
                d=route_length_estimate(a,p,mode);dist+=d
                travel+=_rough_minutes(a,p,mode);stay+=int(p['minutes']);a=p
            if max(route_length_estimate(order[i],order[j],mode) for i in range(len(order)) for j in range(len(order)))> (2.7 if mode=='도보' else 7):continue
            duration=travel+stay
            if duration>budget_mins*.98:continue
            # Avoid excessive time left empty, long trips and far apart stops; favor diverse sights.
            priority=sum(12 for p in order if p['category'] in SIGHTS)
            score=travel*3+dist*10+abs(budget_mins-duration)*.05-priority
            results.append((score,order))
    return [list(x[1]) for x in sorted(results,key=lambda x:x[0])[:8]]

def kakao_leg(key,a,b,mode):
    if mode!='도보' or not key:return None
    try:
        r=requests.get('https://dapi.kakao.com/v2/routing/walk',params={
            'start_x':a['lon'],'start_y':a['lat'],'end_x':b['lon'],'end_y':b['lat']},
            headers={'Authorization':'KakaoAK '+key},timeout=11)
        r.raise_for_status();route=r.json()['route'];p=route['properties']
        shape=[]
        for leg in route.get('legs',[]):
            for step in leg.get('steps',[]):
                for x,y in step.get('path',{}).get('points',[]):
                    shape.append([float(y),float(x)])
        if not shape:return None
        return {'minutes':max(1,math.ceil(p['totalTime']/60)),'km':round(p['totalDistance']/1000,2),
                'shape':shape,'verified':True,'source':'카카오 도보 경로'}
    except (requests.RequestException,KeyError,TypeError,ValueError,IndexError):return None

def each_leg(key,a,b,mode):
    actual=kakao_leg(key,a,b,mode)
    if actual:return actual
    est=route_length_estimate(a,b,mode)
    return {'minutes':max(1,math.ceil(_rough_minutes(a,b,mode))), 'km':round(est,2),
            'shape':[[a['lat'],a['lon']],[b['lat'],b['lon']]], 'verified':False,
            'source':'직선거리 보정 추정 · 실제 길찾기 아님'}

def create_route(key,area_id,origin,places,interests,start,end,mode,selected_ids=None,endpoint=None):
    begin=datetime.strptime(start,'%H:%M');finish=datetime.strptime(end,'%H:%M')
    budget=int((finish-begin).total_seconds()//60)
    if budget<=0:return {'error':'종료 시각은 시작보다 늦어야 합니다.'}
    choices=_candidate_sequences(origin,places,interests,budget,mode,selected_ids)
    if not choices:return {'error':'이 지역에서 조건에 맞는 장소 조합을 찾지 못했습니다. 관심 분야나 시간을 조정해 주세요.'}
    # Compare up to 8 promising orders with REAL Kakao pedestrian legs when available.
    points={origin['id']:origin}
    for p in places:points[p['id']]=p
    if endpoint:points[endpoint['id']]=endpoint
    legs_cache={}
    def link(a,b):
        if a['id']==b['id']:return {'minutes':0,'km':0,'shape':[[a['lat'],a['lon']]],'verified':True,'source':'동일 장소'}
        k=(a['id'],b['id'])
        if k not in legs_cache:legs_cache[k]=each_leg(key,a,b,mode)
        return legs_cache[k]
    good=[]
    for order in choices:
        path=[origin]+order+([endpoint] if endpoint else [])
        travel_legs=[link(a,b) for a,b in zip(path,path[1:])]
        mins=sum(p['minutes'] for p in order)+sum(v['minutes'] for v in travel_legs)
        km=sum(v['km'] for v in travel_legs)
        if mins<=budget:
            score=mins*.5+sum(x['minutes'] for x in travel_legs)*2+(0 if len(order)>=3 else 25)
            good.append((score,order,path,travel_legs,mins,km))
    if not good:
        return {'error':'실제 구간 이동시간을 계산하니 지정한 시간 안에 맞는 코스가 없습니다. 종료 시각을 늘리거나 방문지를 줄여 주세요.'}
    _,order,path,legs,mins,km=min(good,key=lambda x:x[0])
    current=begin;timeline=[{'id':origin['id'],'name':origin['name'],'arrive':start,'leave':start,'minutes':0,'kind':'start','lat':origin['lat'],'lon':origin['lon']}]
    for i,p in enumerate(order):
        current+=timedelta(minutes=legs[i]['minutes']);arrival=current.strftime('%H:%M')
        current+=timedelta(minutes=int(p['minutes']))
        timeline.append({'id':p['id'],'name':p['name'],'arrive':arrival,'leave':current.strftime('%H:%M'),
                         'minutes':int(p['minutes']),'kind':'stop','category':p['category'],
                         'lat':p['lat'],'lon':p['lon'], 'place':p})
    if endpoint:
        current+=timedelta(minutes=legs[-1]['minutes'])
        timeline.append({'id':endpoint['id'],'name':endpoint['name'],'arrive':current.strftime('%H:%M'),
                         'leave':current.strftime('%H:%M'),'minutes':0,'kind':'end',
                         'lat':endpoint['lat'],'lon':endpoint['lon']})
    shape=[]
    for leg in legs:
        seg=leg['shape'];shape.extend(seg if not shape else seg[1:])
    return {'error':None,'area':area_id,'origin':origin,'ordered':order,'timeline':timeline,
            'end':endpoint,'minutes':mins,'travel_minutes':sum(l['minutes'] for l in legs),
            'km':round(km,2),'legs':legs,'shape':shape,'verified':all(l['verified'] for l in legs),
            'start':start,'finish':current.strftime('%H:%M'), 'budget':budget,'mode':mode,
            'recommendation':'가까운 동네 장소를 연결하고, 도보 이동과 체류 시간을 고려해 순서를 정했습니다.'}

# Optional Google Places photos, looked up on demand and NEVER put into persistent cache.
def photo_for_place(place,key):
    if not key:return None
    try:
        query=f"{place['name']} 부산"
        r=requests.post('https://places.googleapis.com/v1/places:searchText',
            headers={'X-Goog-Api-Key':key,'X-Goog-FieldMask':'places.displayName,places.location,places.photos,places.id',
                     'Content-Type':'application/json'},
            json={'textQuery':query,'languageCode':'ko','maxResultCount':3},timeout=8)
        r.raise_for_status()
        for hit in r.json().get('places',[]):
            name=hit.get('displayName',{}).get('text','')
            loc=hit.get('location',{})
            if not match_exact(place['name'],{'place_name':name}):continue
            if distance((place['lat'],place['lon']),(loc.get('latitude',0),loc.get('longitude',0)))>.28:continue
            pictures=hit.get('photos') or []
            if not pictures:continue
            first=pictures[0]
            result=requests.get(f"https://places.googleapis.com/v1/{first['name']}/media",
                headers={'X-Goog-Api-Key':key},params={'maxWidthPx':550},timeout=10)
            result.raise_for_status()
            mime=result.headers.get('content-type','image/jpeg').split(';')[0]
            if not mime.startswith('image/') or len(result.content)>1200000:return None
            authors=[{'name':a.get('displayName',''),'url':a.get('uri','')} for a in first.get('authorAttributions',[])]
            return {'src':f'data:{mime};base64,'+base64.b64encode(result.content).decode('ascii'),
                    'attributions':authors,'google':True}
    except (requests.RequestException,ValueError,KeyError,TypeError):return None
    return None

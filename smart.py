"""Automatic district-first, compact-route recommendation; no LLM or extra key.

Pure functions can be tested offline. The first-stage score uses spherical distance
ONLY to rank options; final duration and geometry must come from route service.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from itertools import permutations, product
from math import ceil
from typing import Iterable
from services import AREA, distance, plan_schedule

SIGHT_CATS = ('독립서점','소품샵','문화·공간','자연·풍경')


def is_in_area(place: dict, area_id: str) -> bool:
    """Strict for Namcheon: not merely within a broad circle around Namcheon."""
    if area_id == 'namcheon':
        return '수영구 남천동' in place.get('address','').replace('부산광역시 ', '').replace('부산 ', '') or (
            '남천동' in place.get('address','') and '수영구' in place.get('address',''))
    area = AREA[area_id]
    return distance(area['center'], (place['lat'],place['lon'])) <= area['radius']/1000


def candidate_groups(places: Iterable[dict], area_id: str, interests: list[str]) -> dict[str,list[dict]]:
    """Pick at most 7 candidates per activity rather than show 50 search results."""
    local = [p for p in places if is_in_area(p, area_id)]
    groups = {}
    if '식사' in interests:
        groups['식사'] = [p for p in local if p['category'] == '식사'][:7]
    if '카페·디저트' in interests:
        groups['카페·디저트'] = [p for p in local if p['category'] == '카페·디저트'][:7]
    sights = [p for p in local if p['category'] in SIGHT_CATS and p['category'] in interests]
    # Preserve editorial priority, then add variety to avoid two nearby generic parks.
    if any(cat in interests for cat in SIGHT_CATS):
        groups['구경거리'] = sights[:10]
    return groups


def _travel_estimate(a, b, mode):
    km = distance((a['lat'],a['lon']), (b['lat'],b['lon']))
    speed = 3.8 if mode=='도보' else 17.0
    return km * (1.42 if mode=='도보' else 1.5)/speed * 60


def _rough_score(origin, ordered, start_hhmm, minutes_limit, mode):
    # Search-time estimate is NOT a verified walking/vehicle route.
    all_stops = [origin] + list(ordered)
    dists = [distance((a['lat'],a['lon']), (b['lat'],b['lon'])) for a,b in zip(all_stops,all_stops[1:])]
    between = dists[1:]
    if between and max(between) > (1.35 if mode=='도보' else 2.5):
        return None
    # Limit the spread of the stops even when visiting all fits five hours.
    for a,b in product(ordered, repeat=2):
        if distance((a['lat'],a['lon']), (b['lat'],b['lon'])) > (1.85 if mode=='도보' else 3.2):
            return None
    travel=sum(_travel_estimate(a,b,mode)+(5 if mode=='택시' else 0) for a,b in zip(all_stops,all_stops[1:]))
    stay=sum(int(p['minutes'])+(10 if p['category']=='식사' else 0) for p in ordered)
    total=travel+stay
    if total>minutes_limit: return None
    # Meal between about 11:20 and 14:30 when possible, but avoid inflexible scheduling.
    elapsed=0; meal_penalty=0
    daystart=datetime.strptime(start_hhmm,'%H:%M')
    for a,p in zip(all_stops,ordered):
        elapsed+=_travel_estimate(a,p,mode)+(5 if mode=='택시' else 0)
        if p['category']=='식사':
            arrival=daystart+timedelta(minutes=elapsed)
            clock=arrival.hour*60+arrival.minute
            if clock<11*60+20:meal_penalty=(11*60+20-clock)*.10
            elif clock>14*60+30:meal_penalty=(clock-(14*60+30))*.20
        elapsed+=int(p['minutes'])+(10 if p['category']=='식사' else 0)
    # Fewer disconnected journeys are valued over maximizing number of clicks.
    # Keep editorial picks where possible, but never at the expense of huge detours.
    editorial_bonus=sum(7 for p in ordered if p.get('editorial'))
    diversity_bonus=6 if len({p['category'] for p in ordered})>=4 else 0
    return travel*2.5 + sum(dists)*8 + meal_penalty - editorial_bonus - diversity_bonus


def suggest_route(origin, places, area_id, interests, start='10:00', end='15:00', mode='도보',
                  max_attractions=2, excluded=None, forced=None):
    """Return a suggested order; NOT a verified itinerary.

    Auto-selects the places, unlike the old app which merely sorts clicks. Prefers
    1 meal, 1 cafe, 1-2 attractions if requested, and discards spread-out options.
    """
    excluded = set(excluded or ())
    forced = forced or {}
    duration = int((datetime.strptime(end,'%H:%M')-datetime.strptime(start,'%H:%M')).total_seconds()//60)
    if duration<=0:raise ValueError('종료 시간은 시작보다 늦어야 합니다.')
    groups = candidate_groups(places,area_id,interests)
    missing=[activity for activity,v in groups.items() if not v]
    if missing: return {'ordered':[], 'error':'이 지역에서 확인된 장소가 없는 분야: '+', '.join(missing)}
    if not groups:return {'ordered':[], 'error':'원하는 활동을 하나 이상 선택해 주세요.'}
    pool=[]
    if '식사' in groups:pool.append(groups['식사'])
    if '카페·디저트' in groups:pool.append(groups['카페·디저트'])
    if '구경거리' in groups:
        # 1–2 attractions, and prefer two only when time and geographic compactness permit.
        pool.append(groups['구경거리'])
        if max_attractions>1 and duration>=210 and len(groups['구경거리'])>=2:
            pool.append(groups['구경거리'])
    slot_names=(['식사'] if '식사' in groups else []) + (['카페·디저트'] if '카페·디저트' in groups else []) + (['구경거리'] * (len(pool) - int('식사' in groups) - int('카페·디저트' in groups)))
    for i,category in enumerate(slot_names):
        if category in forced:
            hit=[p for p in pool[i] if p['name']==forced[category]]
            if hit:pool[i]=hit
    # If 4 stops are not feasible, keep all three activity types and one attraction.
    for poolset in ([pool, pool[:-1]] if len(pool)>3 else [pool]):
        best=None
        # Small bounded search; don't call expensive external routing for every permutation.
        for bundle in product(*poolset):
            names=[p['name'] for p in bundle]
            if len(set(names))!=len(bundle) or any(n in excluded for n in names):continue
            for perm in permutations(bundle):
                score=_rough_score(origin,perm,start,duration,mode)
                if score is None:continue
                if best is None or score<best[0]:best=(score,list(perm))
        if best:return {'ordered':best[1], 'score':best[0], 'error':None,
                        'activities':list(groups), 'estimated_only':True}
    return {'ordered':[], 'error':'시간 또는 이동 거리 조건 안에서 세 활동을 연결하는 코스를 찾지 못했습니다. 출발지나 이동수단을 조정해 주세요.'}


def build_verified_itinerary(origin, places, area_id, interests, start, end, mode='도보',
                             force=None, excluded=None, planner=plan_schedule):
    """Select *then* verify road graph; reduce optional 2nd sight if too long."""
    guess=suggest_route(origin,places,area_id,interests,start,end,mode,excluded=excluded,forced=force)
    if not guess['ordered']:return {'error':guess['error']}
    # Final schedule remains a road-network estimate, not real-time traffic.
    plan=planner(origin,guess['ordered'],start,end,mode,meal_buffer=10,fixed_order=True)
    if not plan['fits'] and len(guess['ordered'])>=4:
        mandatory_sights=[p for p in guess['ordered'] if p['category'] in SIGHT_CATS]
        drop=mandatory_sights[-1]['name']
        shorter=[p for p in guess['ordered'] if p['name']!=drop]
        # Rather than preserve bad order, reoptimize mandatory three with same rules.
        slim=suggest_route(origin,places,area_id,interests,start,end,mode,max_attractions=1,forced=force,excluded=excluded)
        if slim['ordered']:
            shortplan=planner(origin,slim['ordered'],start,end,mode,meal_buffer=10,fixed_order=True)
            if shortplan['fits'] or shortplan['minutes']<plan['minutes']:plan=shortplan
    return {'error':None,'plan':plan, 'area':area_id}

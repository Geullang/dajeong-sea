import math
import json
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="2027 겨울 물꼬방 | 산책 코스 메이커", page_icon="🌊", layout="centered")
st.markdown("""<style>.block-container{max-width:850px;padding-top:1.1rem}.intro{background:#eff8f8;padding:16px 19px;border-radius:16px;margin-bottom:12px}.place{padding:6px 0}.muted{color:#66717b;font-size:.91rem}h1,h2,h3{letter-spacing:-.04em}</style>""", unsafe_allow_html=True)

# 장소 소개는 편집자가 작성한 추천 문구입니다. 주소·전화·좌표는 카카오 로컬 API로 확인합니다.
AREAS = {
    "남천동·광안리": {"center": (35.145,129.113), "spots": [
        ("남천해변공원", "볼거리·서점·소품샵", "광안대교와 바다를 한눈에 바라보며 여유롭게 걷기 좋은 곳이에요.", "겨울 바닷바람에 대비하세요.", 25),
        ("삼익비치 산책길", "볼거리·서점·소품샵", "오래된 주거지와 바다가 만나는 남천동의 산책 풍경을 느껴보세요.", "1월에는 벚꽃이 피지 않습니다.", 20),
        ("인디고서원", "볼거리·서점·소품샵", "책과 인문학을 좋아하는 선생님들에게 특별히 권하고 싶은 공간입니다.", "예약제·방문 가능 여부를 미리 확인하세요.", 25),
        ("샵메이커즈", "볼거리·서점·소품샵", "독립출판물과 디자인 소품을 둘러보며 취향을 발견하는 즐거움이 있습니다.", "영업 여부와 위치를 확인하세요.", 25),
        ("무슈뱅상", "빵집", "바게트와 크루아상 등 빵 자체의 풍미를 즐기는 분에게 어울리는 작은 빵집입니다.", "인기 빵은 일찍 품절될 수 있어요.", 20),
        ("메트르 아티정", "빵집", "여러 종류의 프랑스식 제과·제빵을 비교해 고르는 재미가 있는 곳입니다.", "당일 영업과 인기 메뉴 재고를 확인하세요.", 20),
        ("옵스 남천점", "빵집", "부산에서 친숙하게 만날 수 있는 베이커리로, 선물용 빵을 고르기에도 좋습니다.", "혼잡할 수 있어요.", 20),
        ("크레스트커피바", "카페", "책방과 빵집을 둘러본 뒤 대화를 나누며 쉬어가기 좋은 후보입니다.", "4인 좌석과 영업시간을 확인하세요.", 40),
        ("히떼로스터리 광안점", "카페", "커피 맛에 관심 있는 선생님들이 즐기기 좋은 로스터리 카페입니다.", "좌석과 운영시간을 확인하세요.", 40),
        ("마잘 로스터스", "카페", "산책 도중 커피 한 잔의 여유를 즐기기 위한 후보입니다.", "정확한 매장 위치와 영업 여부를 확인하세요.", 40),
        ("고옥", "식사", "장어덮밥으로 특별한 한 끼를 즐기고 싶은 모둠에 추천합니다.", "예산이 비교적 높을 수 있고 대기가 생길 수 있습니다.", 70),
        ("다이도코로 광안리본점", "식사", "가라아게 등 일본 가정식 메뉴로 편안하게 식사하고 싶을 때 좋습니다.", "4인 좌석과 메뉴 가격을 확인하세요.", 60),
        ("거북이동네 부산남천점", "식사", "함께 고기를 구우며 느긋하게 이야기 나누고 싶은 모둠에 어울립니다.", "대기와 식사 시간을 넉넉히 잡으세요.", 75),
    ]},
    "광안리 해변": {"center": (35.153,129.119), "spots": [
        ("광안리해수욕장", "볼거리·서점·소품샵", "광안대교를 바라보며 부산의 바다를 만나는 대표 산책길입니다.", "겨울 바람과 해변 혼잡을 고려하세요.", 35),
        ("밀락더마켓", "볼거리·서점·소품샵", "바다 근처에서 여러 매장과 공간을 한 번에 둘러보기 좋습니다.", "입점 매장과 운영시간이 달라질 수 있습니다.", 40),
        ("민락수변공원", "볼거리·서점·소품샵", "해안선을 따라 바다 풍경을 감상하며 쉬어가기 좋은 곳입니다.", "기상 상황을 확인하세요.", 30),
        ("옵스 남천점", "빵집", "부산의 베이커리 문화를 맛보기 좋은 후보입니다.", "이 지역에서 이동거리가 길 수 있습니다.", 20),
        ("히떼로스터리 광안점", "카페", "커피를 좋아하는 선생님들이 찾기 좋은 로스터리 카페입니다.", "좌석 확인이 필요합니다.", 40),
        ("다이도코로 광안리본점", "식사", "일본 가정식으로 든든하게 저녁을 마무리하기 좋습니다.", "대기와 영업시간을 확인하세요.", 60),
    ]},
    "영도": {"center": (35.078,129.044), "spots": [
        ("흰여울문화마을", "볼거리·서점·소품샵", "바다를 따라 이어지는 골목과 풍경을 즐길 수 있는 곳입니다.", "경사와 계단이 많습니다.", 60),
        ("태종대", "볼거리·서점·소품샵", "탁 트인 해안 경관이 인상적인 부산의 대표 명소입니다.", "이동거리와 운영시설을 확인하세요.", 75),
        ("국립해양박물관", "볼거리·서점·소품샵", "바다와 해양문화를 함께 살펴볼 수 있는 공간입니다.", "전시·휴관 일정을 확인하세요.", 70),
    ]},
    "해운대": {"center": (35.162,129.163), "spots": [
        ("해운대해수욕장", "볼거리·서점·소품샵", "겨울 바다를 보며 산책하기 좋은 해변입니다.", "강풍에 유의하세요.", 40),
        ("해운대블루라인파크 미포정거장", "볼거리·서점·소품샵", "해안 풍경을 따라 이동하는 열차를 체험할 수 있습니다.", "별도 승차권 예약·시간표 확인이 필요합니다.", 70),
        ("청사포", "볼거리·서점·소품샵", "항구와 바다 풍경을 여유롭게 감상할 수 있는 곳입니다.", "미포에서 이동 시간을 고려하세요.", 45),
    ]},
    "보수동 책방골목": {"center": (35.102,129.024), "spots": [
        ("보수동 책방골목", "볼거리·서점·소품샵", "헌책방을 둘러보며 오래된 책의 이야기를 만나는 곳입니다.", "서점별 운영시간이 다릅니다.", 60),
        ("국제시장", "볼거리·서점·소품샵", "부산의 골목과 상점 풍경을 둘러보는 재미가 있습니다.", "혼잡할 수 있습니다.", 45),
        ("부평깡통시장", "식사", "다양한 먹거리를 나누어 맛보는 시장 산책에 어울립니다.", "좌석·메뉴·가격은 점포별로 다릅니다.", 50),
    ]},
    "도모헌 일대": {"center": (35.156,129.107), "spots": [
        ("도모헌", "볼거리·서점·소품샵", "정원과 문화공간을 둘러보며 차분한 시간을 보내기 좋습니다.", "전시 및 휴관일을 확인하세요.", 60),
    ]},
}
CATS = ["볼거리·서점·소품샵", "빵집", "카페", "식사"]
ICONS = ["📚", "🥐", "☕", "🍽️"]
PHOTO_MANIFEST = Path(__file__).parent / "photos.json"
PHOTO_DIR = Path(__file__).parent / "photos"

@st.cache_data(show_spinner=False)
def photo_catalog():
    try:
        return json.loads(PHOTO_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

def photo_for(name):
    """Only display explicitly supplied, verified photographs. No unrelated stock images."""
    entry = photo_catalog().get(name, {})
    if isinstance(entry, str):
        entry = {"file": entry}
    filename = entry.get("file", "")
    if filename and Path(filename).name == filename:
        path = PHOTO_DIR / filename
        if path.is_file():
            return str(path), entry.get("credit", "")
    return None, None

ORIGINS = {"보다스테이 2·3호": "부산 광안리 보다스테이", "보다스테이 더펜트": "부산 보다스테이 더펜트", "광안리273": "부산 광안리273"}

@st.cache_data(ttl=60*60*12, show_spinner=False)
def kakao_find(query, lat=None, lon=None):
    try:
        key = st.secrets["KAKAO_REST_API_KEY"]
        params = {"query": query, "size": 10}
        if lat is not None and lon is not None:
            params.update({"x": lon, "y": lat, "sort": "distance"})
        r = requests.get("https://dapi.kakao.com/v2/local/search/keyword.json", headers={"Authorization": f"KakaoAK {key}"}, params=params, timeout=8)
        r.raise_for_status()
        return r.json().get("documents", []), ""
    except KeyError:
        return [], "Streamlit Secrets에 KAKAO_REST_API_KEY가 없습니다."
    except requests.RequestException as e:
        return [], f"카카오 장소 조회 실패: {type(e).__name__} (API 활성화·쿼터·키 설정을 확인하세요.)"


def resolve(name, center):
    docs, error = kakao_find(f"부산 {name}", *center)
    if not docs:
        return None, error
    normalized = name.replace(" ", "")
    match = next((d for d in docs if normalized in d["place_name"].replace(" ", "") or d["place_name"].replace(" ", "") in normalized), docs[0])
    return {"name": match["place_name"], "address": match.get("road_address_name") or match.get("address_name"), "phone": match.get("phone", ""), "url": match.get("place_url", ""), "lat": float(match["y"]), "lon": float(match["x"]), "category": match.get("category_name", "")}, error


def distance_km(a, b):
    r = 6371
    dlat = math.radians(b[0]-a[0]); dlon = math.radians(b[1]-a[1])
    z = math.sin(dlat/2)**2 + math.cos(math.radians(a[0]))*math.cos(math.radians(b[0]))*math.sin(dlon/2)**2
    return 2*r*math.asin(math.sqrt(z))


def order_nearby(places, origin):
    remaining = places.copy(); result = []; here = origin
    while remaining:
        p = min(remaining, key=lambda x: distance_km(here, (x["geo"]["lat"], x["geo"]["lon"])))
        result.append(p); remaining.remove(p)
        here = (p["geo"]["lat"], p["geo"]["lon"])
    return result

for key, value in {"phase": 1, "selected": [], "route": []}.items():
    if key not in st.session_state: st.session_state[key] = value

st.caption("전국국어교사모임 · 부산 · 2027년 1월 9일 토요일")
st.title("🌊 2027 겨울 물꼬방")
st.header("산책 코스 메이커")
st.markdown("*가벼운 마음이 멀리 간다*  ")
st.caption("By 물꼬방 약국")
st.markdown('<div class="intro">책과 사람, 골목과 바다를 만나는 부산의 오후.<br>많이 방문하는 것보다 우리 모둠에게 잘 맞는 곳을 고르는 산책을 제안합니다.</div>', unsafe_allow_html=True)
st.progress(st.session_state.phase/3, text=f"{st.session_state.phase} / 3 단계")

if st.session_state.phase == 1:
    st.subheader("1. 우리 모둠의 산책 조건")
    origin_opt = st.radio("출발 장소", ["현재 위치 자동 확인", *ORIGINS, "다른 장소 직접 입력"], index=1)
    origin_name = ORIGINS.get(origin_opt, "")
    current_coords = None
    if origin_opt == "현재 위치 자동 확인":
        st.info("아래 '현재 위치 가져오기' 버튼을 누르면 브라우저의 위치 권한을 요청합니다. 허용하지 않으면 직접 주소를 입력할 수 있습니다.")
        # Browser geolocation requires a custom browser component; this deployment uses a reliable manual fallback.
        st.caption("현재 배포판에서는 자동 GPS가 지원되지 않습니다. 위치 권한을 임의로 사용하지 않습니다.")
        origin_name = st.text_input("현재 있는 장소 또는 주소", placeholder="예: 부산 광안리해수욕장")
    elif origin_opt == "다른 장소 직접 입력":
        origin_name = st.text_input("출발 장소명 또는 주소", placeholder="예: 부산역")
    area = st.selectbox("탐방 지역", list(AREAS))
    col1, col2 = st.columns(2)
    times = [f"{h:02d}:{m:02d}" for h in range(12,22) for m in (0,30)]
    with col1: start = st.selectbox("시작 시간", times, index=5)
    with col2: end = st.selectbox("종료 시간", times, index=14)
    col1, col2 = st.columns(2)
    with col1: people = st.selectbox("모둠 인원", list(range(2,11)), index=2)
    with col2: budget = st.selectbox("1인 식사 예산", ["15,000원 이하", "15,000~20,000원", "20,000~30,000원", "제한 없음"], index=1)
    mode = st.radio("이동 방식", ["도보 중심", "탐방 지역까지 택시, 이후 도보", "자가 운전"], index=1)
    st.caption("추천 문구는 물꼬방 취향에 맞춰 편집했습니다. 장소 위치·전화번호는 카카오에서 조회합니다.")
    if st.button("추천 장소 만나기 →", type="primary", use_container_width=True):
        if not origin_name.strip(): st.error("출발 장소를 입력해 주세요.")
        elif end <= start: st.error("종료 시간은 시작 시간보다 늦어야 합니다.")
        else:
            st.session_state.trip = dict(origin=origin_name, area=area, start=start, end=end, people=people, budget=budget, mode=mode)
            st.session_state.selected = []
            st.session_state.phase = 2
            st.rerun()

elif st.session_state.phase == 2:
    trip = st.session_state.trip; config = AREAS[trip["area"]]
    st.subheader(f"2. {trip['area']}에서 무엇을 만날까요?")
    st.write("모둠의 취향에 맞는 장소를 골라보세요. 각 장소의 이야기를 먼저 읽고, 가고 싶은 곳만 체크하면 됩니다.")
    st.caption("장소별 실제 사진은 사용 권한을 확인한 파일부터 표시합니다. 사진이 없는 장소에는 준비 중 안내가 나옵니다.")
    selected = set(st.session_state.selected)
    for cat, icon in zip(CATS, ICONS):
        st.markdown(f"### {icon} {cat}")
        matches = [(i, p) for i,p in enumerate(config["spots"]) if p[1] == cat]
        if not matches: st.caption("이 지역에서 확인된 추천 후보가 아직 없습니다.")
        for i, (name, _, description, warning, stay) in matches:
            with st.container(border=True):
                left, right = st.columns([1.25, 2], gap="medium")
                with left:
                    photo, credit = photo_for(name)
                    if photo:
                        st.image(photo, use_container_width=True)
                        if credit: st.caption(f"사진: {credit}")
                    else:
                        st.markdown("<div style='background:#e9f3f5;border-radius:14px;min-height:140px;display:flex;align-items:center;justify-content:center;color:#617b84;text-align:center'>📷<br>장소 사진 준비 중</div>", unsafe_allow_html=True)
                with right:
                    checked = st.checkbox(f"{name}", value=i in selected, key=f"choose_{trip['area']}_{i}")
                    st.write(description)
                    st.caption(f"⏱ 권장 체류 {stay}분")
                    st.caption(f"⚠️ {warning}")
                    if checked: selected.add(i)
                    else: selected.discard(i)
    st.session_state.selected = sorted(selected)
    st.write(f"**{len(selected)}곳 선택됨**")
    a,b = st.columns(2)
    if a.button("← 조건 바꾸기", use_container_width=True): st.session_state.phase=1; st.rerun()
    if b.button("우리 산책 코스 만들기 →", type="primary", use_container_width=True, disabled=not selected):
        st.session_state.phase=3; st.session_state.route=[]; st.rerun()

else:
    trip = st.session_state.trip; config = AREAS[trip["area"]]
    st.subheader("3. 우리 모둠의 다정한 산책")
    st.caption(f"2027. 1. 9. (토) · {trip['people']}명 · {trip['mode']} · {trip['area']}")
    if st.button("← 장소 다시 고르기"): st.session_state.phase=2; st.rerun()
    with st.spinner("카카오에서 장소 위치와 연락처를 확인하고 있어요..."):
        places = []
        errors = []
        for idx in st.session_state.selected:
            item = config["spots"][idx]
            geo, err = resolve(item[0], config["center"])
            if geo: places.append({"id":idx,"item":item,"geo":geo})
            else: errors.append(f"{item[0]}: {err or '검색 결과 없음'}")
        origin_geo, origin_error = resolve(trip["origin"], config["center"])
    if errors:
        st.warning("일부 장소의 카카오 검색 결과를 확인하지 못했습니다. " + "; ".join(errors))
    if not places:
        st.error("장소 위치를 확인할 수 없습니다. 카카오 API 설정과 검색어를 확인해 주세요.")
        st.stop()
    origin_point = (origin_geo["lat"], origin_geo["lon"]) if origin_geo else config["center"]
    if not origin_geo: st.warning("출발지 위치를 확인하지 못해 탐방 지역 중심점을 임시 기준으로 사용했습니다. 정확한 출발 동선은 아닙니다.")
    if not st.session_state.route:
        st.session_state.route = [p["id"] for p in order_nearby(places, origin_point)]
    ids = [p["id"] for p in places]
    st.session_state.route = [i for i in st.session_state.route if i in ids] + [i for i in ids if i not in st.session_state.route]
    st.markdown("#### 추천 방문 순서")
    st.caption("장소 좌표 간 직선거리를 줄이는 순서입니다. 실제 도보 길찾기나 교통시간을 계산한 결과는 아닙니다.")
    for pos, idx in enumerate(st.session_state.route):
        p = next(p for p in places if p["id"]==idx)
        a,b,c = st.columns([6,1,1])
        a.write(f"**{pos+1}. {p['item'][0]}**")
        if b.button("↑", key=f"up_{idx}", disabled=pos==0):
            st.session_state.route[pos-1],st.session_state.route[pos]=st.session_state.route[pos],st.session_state.route[pos-1];st.rerun()
        if c.button("↓", key=f"down_{idx}", disabled=pos==len(st.session_state.route)-1):
            st.session_state.route[pos+1],st.session_state.route[pos]=st.session_state.route[pos],st.session_state.route[pos+1];st.rerun()
    ordered = [next(p for p in places if p["id"]==idx) for idx in st.session_state.route]
    st.markdown("#### 🗺️ 선택한 장소와 방문 순서")
    coordinates = [(p["geo"]["lat"],p["geo"]["lon"]) for p in ordered]
    fmap = folium.Map(location=[sum(x[0] for x in coordinates)/len(coordinates),sum(x[1] for x in coordinates)/len(coordinates)], zoom_start=14, control_scale=True)
    for i,p in enumerate(ordered,1):
        folium.Marker([p["geo"]["lat"],p["geo"]["lon"]], tooltip=f"{i}. {p['item'][0]}", popup=p["item"][0], icon=folium.Icon(color="blue", icon="info-sign")).add_to(fmap)
    if len(coordinates)>1: folium.PolyLine(coordinates, color="#147c9a", weight=4, opacity=.8, dash_array="7,7").add_to(fmap)
    st_folium(fmap, width=None, height=370, returned_objects=[])
    st.caption("점선은 장소를 직선으로 이은 위치 관계도입니다. 실제 보행 경로가 아닙니다.")
    st.markdown("#### ⏰ 추천 일정")
    now = datetime.strptime(trip["start"], "%H:%M")
    deadline = datetime.strptime(trip["end"], "%H:%M")
    rows=[]; previous=origin_point; notes=[]
    for i,p in enumerate(ordered):
        coords=(p["geo"]["lat"],p["geo"]["lon"])
        km=distance_km(previous,coords)
        if i==0 and trip["mode"]!="도보 중심":
            move_label=f"첫 이동 약 {km:.1f}km (택시·차량 소요시간 별도 확인)"
            move_min=20
        else:
            move_label=f"직선거리 약 {km:.1f}km (실제 도보 거리는 더 길 수 있음)"
            move_min=max(5,math.ceil(km*1000/65))
        move_start=now; now+=timedelta(minutes=move_min)
        rows.append({"시간":f"{move_start:%H:%M}–{now:%H:%M}","장소":"이동", "활동":move_label})
        name,cat,description,warning,stay=p["item"]
        arrive=now;now+=timedelta(minutes=stay)
        rows.append({"시간":f"{arrive:%H:%M}–{now:%H:%M}","장소":name,"활동":description})
        notes.append((name,warning,p["geo"]))
        previous=coords
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.metric("임시 일정 종료 예상", now.strftime("%H:%M"))
    if now>deadline: st.error("설정한 종료 시간을 초과합니다. 장소 수나 체류 시간을 줄여 보세요.")
    else: st.success("임시 시간표상 종료 시간 이내입니다. 실제 이동·대기 시간은 더 걸릴 수 있습니다.")
    st.markdown("#### 📌 방문 전에 알아둘 점")
    for name,warning,geo in notes:
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.write(warning)
            st.caption(f"📍 {geo['address']}")
            if geo["phone"]: st.write(f"☎️ {geo['phone']}")
            if geo["url"]: st.link_button("카카오맵에서 위치·영업정보 확인",geo["url"])
    st.info("영업시간·휴무·가격·예약 가능 여부는 카카오 로컬 검색만으로 검증할 수 없습니다. 방문 전 매장에 확인해 주세요. 일정표의 이동시간은 단순 추정치입니다.")
    text_lines=["🌊 2027 겨울 물꼬방 산책 코스 메이커",f"출발: {trip['origin']} / {trip['start']}",f"지역: {trip['area']} / {trip['people']}명", ""]
    text_lines += [f"{r['시간']} | {r['장소']} | {r['활동']}" for r in rows]
    text_lines += ["", "방문 전 확인 사항"]+[f"{name}: {warning} / {geo['phone']} / {geo['url']}" for name,warning,geo in notes]
    st.download_button("📄 우리 모둠 일정 저장", "\n".join(text_lines), file_name="mulkkobang_walk_2027.txt", mime="text/plain", use_container_width=True)
    if st.button("처음부터 다시",use_container_width=True): st.session_state.phase=1;st.session_state.selected=[];st.session_state.route=[];st.rerun()

st.divider()
st.caption("물꼬방 약국 기획 · 장소 추천 문구는 편집 정보 · 위치와 연락처는 카카오 로컬 검색 결과 · GPS·실제 길찾기는 추가 개발 예정 · 장소 사진은 제공된 검증 사진만 표시")

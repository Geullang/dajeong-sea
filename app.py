import math
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="다정한 바다 | 산책 코스 메이커", page_icon="🌊", layout="wide")
st.markdown("""<style>
.block-container{max-width:1000px;padding-top:1.5rem}
h1,h2,h3{letter-spacing:-.03em}
</style>""", unsafe_allow_html=True)

# 카카오 장소 검색 API가 제공하는 정보만 표시합니다.
# 실제 API 키는 GitHub 코드가 아닌 Streamlit의 Secrets에 저장합니다.
API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
CATEGORIES = [
    ("📚 볼거리·서점·소품샵", ["서점", "소품샵", "명소"]),
    ("🥖 빵집", ["베이커리"]),
    ("☕ 카페", ["카페"]),
    ("🍽️ 식당", ["식당"]),
]
AREAS = {
    "남천동": ("부산 남천동", 129.113, 35.143, 2600),
    "광안리 책과 산책": ("부산 광안리", 129.119, 35.153, 2400),
    "도모헌 일대": ("부산 도모헌", 129.108, 35.158, 2400),
    "영도": ("부산 영도", 129.073, 35.075, 5000),
    "해운대 요트": ("부산 수영만요트경기장", 129.137, 35.161, 3000),
    "해운대 해변열차": ("부산 해운대 미포", 129.170, 35.159, 3000),
    "보수동 책방골목": ("부산 보수동", 129.027, 35.102, 2500),
}
ORIGINS = ["현위치 (주소 직접 입력)", "보다스테이 2·3호", "보다스테이 더펜트", "광안리273", "다른 장소 직접 입력"]


def api_key():
    try:
        return st.secrets["KAKAO_REST_API_KEY"]
    except (KeyError, FileNotFoundError):
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def kakao_search(query, x=None, y=None, radius=None, size=10):
    key = api_key()
    if not key:
        raise RuntimeError("Streamlit Secrets에 KAKAO_REST_API_KEY가 없습니다.")
    params = {"query": query, "size": size, "sort": "accuracy"}
    if x is not None and y is not None:
        params.update({"x": x, "y": y, "radius": radius or 3000})
    try:
        response = requests.get(
            API_URL,
            headers={"Authorization": f"KakaoAK {key}"},
            params=params,
            timeout=10,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "알 수 없음"
        raise RuntimeError(f"카카오 장소 검색 실패 (HTTP {code}). 카카오맵 활성화 및 REST API 키를 확인해 주세요.") from exc
    except requests.RequestException as exc:
        raise RuntimeError("카카오 서버와 통신하지 못했습니다. 잠시 후 다시 시도해 주세요.") from exc
    return response.json().get("documents", [])


def get_places(area):
    label, x, y, radius = AREAS[area]
    found = {}
    for category_index, (_, terms) in enumerate(CATEGORIES):
        for term in terms:
            for raw in kakao_search(f"{label} {term}", x, y, radius, size=12):
                pid = raw.get("id")
                if not pid or pid in found:
                    continue
                try:
                    lat, lon = float(raw["y"]), float(raw["x"])
                except (ValueError, KeyError):
                    continue
                found[pid] = {
                    "id": pid,
                    "name": raw.get("place_name", "이름 없음"),
                    "category": category_index,
                    "category_name": raw.get("category_name", ""),
                    "address": raw.get("road_address_name") or raw.get("address_name") or "주소 정보 없음",
                    "phone": raw.get("phone", ""),
                    "url": raw.get("place_url", ""),
                    "lat": lat,
                    "lon": lon,
                }
    return list(found.values())


def distance_km(a, b):
    # 두 좌표 사이의 직선거리. 실제 도보/차량 이동거리와 다릅니다.
    r1, r2 = math.radians(a["lat"]), math.radians(b["lat"])
    dr, dl = r2 - r1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dr / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def approximate_order(places):
    # 출발지 주소를 좌표로 확인하지 않았으므로, 선택한 장소 사이의 직선거리만 활용합니다.
    if not places:
        return []
    remaining = places[:]
    output = [remaining.pop(0)]
    while remaining:
        best = min(remaining, key=lambda p: distance_km(output[-1], p))
        output.append(best)
        remaining.remove(best)
    return output


for k, initial in {"phase": 1, "selected_ids": [], "ordered_ids": [], "places": []}.items():
    if k not in st.session_state:
        st.session_state[k] = initial

st.caption("전국국어교사모임 · 부산의 오후")
st.title("🌊 다정한 바다 · 산책 코스 메이커")
st.write("가고 싶은 곳은 우리가 고르고, 함께 걸을 길은 더 편하게.")
st.progress(st.session_state.phase / 3, text=f"{st.session_state.phase} / 3 단계")

if st.session_state.phase == 1:
    st.subheader("1. 우리 모둠의 산책 조건")
    st.info("2027년 1월 9일 토요일 · 부산 모둠별 자유 탐방")
    origin_choice = st.radio("출발 장소", ORIGINS, index=1)
    custom = ""
    if origin_choice in (ORIGINS[0], ORIGINS[-1]):
        custom = st.text_input("출발 장소명 또는 주소", placeholder="현재 있는 카페, 식당, 주소 등")
    area = st.selectbox("탐방 지역", list(AREAS))
    a, b = st.columns(2)
    times = [f"{h:02d}:{m:02d}" for h in range(13, 20) for m in (0, 30)]
    with a:
        start = st.selectbox("시작 시간", times, index=3)
    with b:
        end = st.selectbox("종료 시간", times, index=12)
    a, b = st.columns(2)
    with a:
        people = st.selectbox("모둠 인원", range(2, 11), index=2)
    with b:
        budget = st.selectbox("1인 식사 예산", ["15,000원 이하", "15,000~20,000원", "20,000~30,000원", "제한 없음"], index=1)
    mode = st.radio("이동 방식", ["도보 중심", "탐방 지역까지 택시, 이후 도보", "자가 운전"], index=1)
    st.caption("현위치는 자동으로 수집하지 않습니다. 식사 예산은 장소 검색 결과에 가격 정보가 없어 참고 조건으로만 기록됩니다.")
    if st.button("추천 장소 고르기 →", type="primary", use_container_width=True):
        origin = custom.strip() if origin_choice in (ORIGINS[0], ORIGINS[-1]) else origin_choice
        if end <= start:
            st.error("종료 시간이 시작 시간보다 늦어야 합니다.")
        elif not origin:
            st.error("출발 장소를 입력해 주세요.")
        else:
            st.session_state.trip = dict(origin=origin, area=area, start=start, end=end,
                                         people=people, budget=budget, mode=mode)
            with st.spinner("카카오맵에서 실제 장소를 검색하는 중입니다..."):
                try:
                    found = get_places(area)
                except RuntimeError as exc:
                    st.error(str(exc))
                else:
                    if not found:
                        st.warning("검색된 장소가 없습니다. 다른 지역을 선택해 주세요.")
                    else:
                        st.session_state.places = found
                        st.session_state.selected_ids = []
                        st.session_state.ordered_ids = []
                        st.session_state.phase = 2
                        st.rerun()

elif st.session_state.phase == 2:
    trip = st.session_state.trip
    st.subheader(f"2. {trip['area']}에서 어디에 들를까요?")
    st.success("카카오 장소 검색 API에서 가져온 실제 장소 목록입니다.")
    st.caption("사진·영업시간·가격은 검색 API에서 제공하지 않습니다. 방문 전 카카오맵에서 확인해 주세요. 검색 결과는 최대 1시간 동안 임시 저장됩니다.")
    selected = set(st.session_state.selected_ids)
    for category_index, (heading, _) in enumerate(CATEGORIES):
        st.markdown(f"### {heading}")
        cat_places = [p for p in st.session_state.places if p["category"] == category_index]
        if not cat_places:
            st.caption("이 지역의 검색 결과가 없습니다.")
        for p in cat_places:
            with st.container(border=True):
                checked = st.checkbox(p["name"], value=p["id"] in selected, key=f"place_{p['id']}")
                st.caption(p["category_name"])
                st.write(f"📍 {p['address']}")
                if p["phone"]:
                    st.write(f"☎️ {p['phone']}")
                if p["url"]:
                    st.markdown(f"[카카오맵에서 장소 확인]({p['url']})")
                if checked:
                    selected.add(p["id"])
                else:
                    selected.discard(p["id"])
    st.session_state.selected_ids = list(selected)
    st.write(f"**{len(selected)}곳 선택됨**")
    a, b = st.columns(2)
    if a.button("← 조건 수정", use_container_width=True):
        st.session_state.phase = 1
        st.rerun()
    if b.button("선택 완료 · 동선 만들기 →", type="primary", use_container_width=True, disabled=not selected):
        chosen = [p for p in st.session_state.places if p["id"] in selected]
        st.session_state.ordered_ids = [p["id"] for p in approximate_order(chosen)]
        st.session_state.phase = 3
        st.rerun()

else:
    trip = st.session_state.trip
    by_id = {p["id"]: p for p in st.session_state.places}
    st.subheader("3. 우리 모둠의 다정한 산책")
    st.caption(f"2027.01.09 (토) · {trip['people']}명 · {trip['area']} · {trip['mode']}")
    st.warning("방문 순서는 장소 간 직선거리를 참고한 간이 추천입니다. 실제 도보·차량 경로, 이동 시간, 영업 여부를 검증한 일정은 아닙니다.")
    if st.button("← 장소 다시 고르기"):
        st.session_state.phase = 2
        st.rerun()
    st.write("**방문 순서 조정**")
    for i, pid in enumerate(st.session_state.ordered_ids[:]):
        p = by_id[pid]
        c1, c2, c3 = st.columns([5, 1, 1])
        c1.write(f"{i+1}. {p['name']}")
        if c2.button("↑", key=f"u{i}", disabled=i == 0):
            x = st.session_state.ordered_ids
            x[i-1], x[i] = x[i], x[i-1]
            st.rerun()
        if c3.button("삭제", key=f"d{i}"):
            st.session_state.ordered_ids.remove(pid)
            st.rerun()
    ordered = [by_id[pid] for pid in st.session_state.ordered_ids]
    if ordered:
        st.write("**선택한 장소 위치 지도**")
        st.map(pd.DataFrame([{"lat": p["lat"], "lon": p["lon"]} for p in ordered]))
        st.caption("지도에는 장소 위치만 표시됩니다. 지도 위에 실제 이동 경로가 그려지는 것은 아닙니다.")
    when = datetime.strptime(trip["start"], "%H:%M")
    end = datetime.strptime(trip["end"], "%H:%M")
    output = ["다정한 바다 산책 코스 | 2027.01.09", f"출발: {trip['origin']}, {trip['start']}", f"지역: {trip['area']}"]
    for i, p in enumerate(ordered):
        t1 = when.strftime("%H:%M")
        when += timedelta(minutes=40)  # 사용자 편의를 위한 임시 체류시간
        t2 = when.strftime("%H:%M")
        with st.container(border=True):
            st.markdown(f"**{t1}–{t2} · {p['name']}**")
            st.write(f"📍 {p['address']}")
            if p["phone"]:
                st.write(f"☎️ {p['phone']}")
            if p["url"]:
                st.markdown(f"[카카오맵에서 위치·영업정보 확인]({p['url']})")
        output.append(f"{t1}-{t2} {p['name']} | {p['address']} | {p['url']}")
        if i < len(ordered) - 1:
            when += timedelta(minutes=15)  # 실제 이동 소요시간이 아닌 임시 여유시간
    st.metric("임시 일정 종료 예상", when.strftime("%H:%M"))
    st.caption("장소별 체류 40분, 장소 간 여유 15분으로 가정한 시간표입니다. 실제 이동 시간은 포함되지 않습니다.")
    if when > end:
        st.error("임시 시간표가 종료 시간을 초과합니다. 방문 장소를 줄여 주세요.")
    else:
        st.info("임시 시간표는 설정한 종료 시간 안에 들어옵니다. 실제 이동시간과 영업시간은 별도로 확인해 주세요.")
    st.download_button("📄 일정 텍스트 저장", data="\n".join(output), file_name="dajeong-sea-route.txt", mime="text/plain")
    if st.button("처음부터 다시"):
        st.session_state.phase = 1
        st.rerun()

st.divider()
st.caption("카카오 장소 검색 연동 버전 v0.4 · API 키는 Streamlit Secrets에서만 읽습니다 · 사진/실시간 영업시간/실제 경로는 미연결")

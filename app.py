import streamlit as st
from datetime import datetime, timedelta
from urllib.parse import quote

st.set_page_config(page_title='다정한 바다 | 산책 코스 메이커', page_icon='🌊', layout='wide')
st.markdown('''<style>
.block-container{max-width:1000px;padding-top:1.5rem}h1,h2,h3{letter-spacing:-.03em}
.card-note{background:#eaf7f9;border-radius:12px;padding:12px;margin:8px 0}
</style>''', unsafe_allow_html=True)

CATEGORIES=['볼거리·서점·소품샵','빵집','카페','식당']
DATA={
'남천동':[
('인디고서원',0,'인문학 서적과 문화 활동 공간','부산 수영구 수영로408번길 28',25,0,'사전 방문 가능 여부 확인'),
('샵메이커즈',0,'독립출판물과 디자인 소품','부산 수영구 남천동로 5',25,0,'운영시간 확인'),
('남천해변공원',0,'광안대교를 바라보는 산책','부산 수영구 남천동',20,0,'겨울 바닷바람 주의'),
('무슈뱅상',1,'프랑스식 하드빵과 바게트','부산 수영구 광남로48번길 19',15,0,'조기 품절·마감 확인'),
('메트르 아티정',1,'크루아상과 페이스트리','부산 수영구 남천동로22번길 21',15,0,'당일 영업 확인'),
('옵스 남천점',1,'부산의 대표적인 베이커리','부산 수영구 황령대로489번길 37',15,0,'혼잡 가능성'),
('크레스트커피바',2,'커피를 마시며 쉬기 좋은 공간','부산 수영구 광남로48번길 12',40,7000,'4인 좌석 확인'),
('히떼로스터리 광안점',2,'로스터리 카페','부산 수영구 수영로510번길 57',40,7000,'4인 좌석 확인'),
('마잘 로스터스',2,'해안가 방향 카페','부산 수영구 광안해변로 21',40,7000,'영업 여부 확인'),
('다이도코로 광안리본점',3,'일본 가정식 정식','부산 수영구 남천동',55,15000,'4인 좌석·가격 확인'),
('거북이동네 부산남천점',3,'고기구이 식사','부산 수영구 수영로 414',65,19000,'메뉴·총금액 확인'),
('하나돈까스 남천점',3,'돈가스 메뉴','부산 수영구 남천동',55,15000,'영업·가격 확인'),
],
'광안리 책과 산책':[('광안리 해변',0,'광안대교 풍경 감상','부산 수영구 광안해변로',25,0,'겨울 바람 주의')],
'도모헌 일대':[('도모헌',0,'문화 공간 및 정원','부산 수영구 황령산로7번길 60',50,0,'운영·휴관 확인')],
'영도':[('흰여울문화마을',0,'해안 산책 골목','부산 영도구 영선동4가',45,0,'계단과 경사 주의')],
'해운대 요트':[('수영만요트경기장',0,'요트 체험 출발 후보','부산 해운대구 해운대해변로 84',60,0,'사전 예약·요금·기상 확인')],
'해운대 해변열차':[('미포정거장',0,'해변열차 탑승 후보','부산 해운대구 달맞이길62번길 13',60,0,'승차권·시간표 확인')],
'보수동 책방골목':[('보수동 책방골목',0,'헌책방과 골목 구경','부산 중구 책방골목길',45,0,'상점별 운영시간 확인')]
}

for k, v in {'phase':1,'selected':[],'ordered':[]}.items():
    if k not in st.session_state: st.session_state[k]=v

st.caption('전국국어교사모임 · 부산의 오후')
st.title('🌊 다정한 바다 · 산책 코스 메이커')
st.write('가고 싶은 곳은 우리가 고르고, 함께 걸을 길은 더 편하게.')
st.progress(st.session_state.phase/3, text=f'{st.session_state.phase} / 3 단계')

if st.session_state.phase==1:
    st.subheader('1. 우리 모둠의 산책 조건')
    st.info('2027년 1월 9일 토요일 · 부산 모둠별 자유 탐방')
    origins=['현위치 (현재 버전에서는 직접 주소 입력)','보다스테이 2·3호','보다스테이 더펜트','광안리273','다른 장소 직접 입력']
    origin=st.radio('출발 장소', origins, index=1)
    if origin in (origins[0],origins[4]):
        custom=st.text_input('출발 장소명 또는 주소',placeholder='현재 있는 카페, 식당, 주소 등')
    else: custom=''
    area=st.selectbox('탐방 지역',list(DATA),index=0)
    a,b=st.columns(2)
    times=[f'{h:02d}:{m:02d}' for h in range(13,20) for m in (0,30)]
    with a: start=st.selectbox('시작 시간',times,index=3)
    with b: end=st.selectbox('종료 시간',times,index=12)
    a,b=st.columns(2)
    with a: people=st.selectbox('모둠 인원',range(2,11),index=2)
    with b: budget=st.selectbox('1인 식사 예산', ['15,000원 이하','15,000~20,000원','20,000~30,000원','제한 없음'],index=1)
    mode=st.radio('이동 방식',['도보 중심','탐방 지역까지 택시, 이후 도보','자가 운전'],index=1)
    st.session_state.trip=dict(origin=(custom if origin in (origins[0],origins[4]) else origin),area=area,start=start,end=end,people=people,budget=budget,mode=mode)
    if st.button('추천 장소 고르기 →',type='primary',use_container_width=True):
        if end<=start: st.error('종료 시간이 시작 시간보다 늦어야 합니다.')
        elif not st.session_state.trip['origin']: st.error('출발 장소를 입력해 주세요.')
        else:
            st.session_state.phase=2
            st.session_state.selected=[]
            st.rerun()

elif st.session_state.phase==2:
    trip=st.session_state.trip
    st.subheader(f"2. {trip['area']}에서 어디에 들를까요?")
    st.warning('현재는 동작 확인용 시제품입니다. 장소 정보는 시연용 후보이며 실시간 검색·사진·영업시간 검증은 API 연결 후 제공합니다.')
    items=DATA[trip['area']]
    selection=set(st.session_state.selected)
    icons=['📚','🥖','☕','🍽️']
    for cat in range(4):
        st.markdown(f'### {icons[cat]} {CATEGORIES[cat]}')
        cat_items=[(idx,p) for idx,p in enumerate(items) if p[1]==cat]
        if not cat_items:
            st.caption('현재 시연용 후보가 없습니다. 실제 장소 API 연결 후 제공됩니다.')
        for idx,p in cat_items:
            with st.container(border=True):
                c1,c2=st.columns([1,4])
                with c1:
                    st.markdown(f'<div style="font-size:56px;text-align:center;background:#e9f4f7;border-radius:14px;padding:18px">{icons[cat]}</div>',unsafe_allow_html=True)
                    st.caption('시연 이미지')
                with c2:
                    checked=st.checkbox(p[0],value=idx in selection,key=f'item_{trip["area"]}_{idx}')
                    st.write(p[2])
                    st.caption(f'📍 {p[3]} · 확인: {p[6]}')
                    if p[5]: st.caption(f'예상 이용비 {p[5]:,}원 · 시연 값')
                    if checked: selection.add(idx)
                    else: selection.discard(idx)
    st.session_state.selected=sorted(selection)
    st.write(f'**{len(selection)}곳 선택됨**')
    a,b=st.columns(2)
    if a.button('← 조건 수정',use_container_width=True):
        st.session_state.phase=1; st.rerun()
    if b.button('선택 완료 · 동선 만들기 →',type='primary',use_container_width=True,disabled=not selection):
        st.session_state.ordered=sorted(selection,key=lambda i:items[i][1])
        st.session_state.phase=3;st.rerun()

else:
    trip=st.session_state.trip
    items=DATA[trip['area']]
    st.subheader('3. 우리 모둠의 다정한 산책')
    st.caption(f"2027.01.09 (토) · {trip['people']}명 · {trip['area']} · {trip['mode']}")
    st.warning('이동시간은 실측 경로가 아닌 임시 배정치입니다. API 연결 전에는 영업시간·전화번호·방문 가능 여부가 확인되지 않습니다.')
    if st.button('← 장소 다시 고르기'):
        st.session_state.phase=2;st.rerun()
    st.write('**방문 순서 조정**')
    for i,idx in enumerate(st.session_state.ordered):
        p=items[idx]
        c1,c2,c3=st.columns([5,1,1])
        c1.write(f'{i+1}. {p[0]}')
        if c2.button('↑',key=f'u{i}',disabled=i==0):
            x=st.session_state.ordered
            x[i-1],x[i]=x[i],x[i-1];st.rerun()
        if c3.button('삭제',key=f'd{i}'):
            st.session_state.ordered.remove(idx);st.rerun()
    when=datetime.strptime(trip['start'],'%H:%M')
    end=datetime.strptime(trip['end'],'%H:%M')
    move=10 if trip['mode']=='도보 중심' else 20
    when+=timedelta(minutes=move)
    output=[f"다정한 바다 산책 코스 | 2027.01.09",f"출발: {trip['origin']}, {trip['start']}",f"지역: {trip['area']}"]
    for i,idx in enumerate(st.session_state.ordered):
        p=items[idx]
        t1=when.strftime('%H:%M')
        when+=timedelta(minutes=p[4])
        t2=when.strftime('%H:%M')
        with st.container(border=True):
            st.markdown(f'**{t1}–{t2}  ·  {p[0]}**')
            st.write(p[2])
            st.caption(f"📍 {p[3]} · 확인 사항: {p[6]}")
            q=quote(p[0]+' '+p[3])
            st.markdown(f'[카카오맵에서 찾기](https://map.kakao.com/?q={q}) · [네이버지도에서 찾기](https://map.naver.com/p/search/{q})')
        output.append(f'{t1}-{t2} {p[0]} | {p[3]}')
        if i<len(st.session_state.ordered)-1: when+=timedelta(minutes=12)
    st.metric('임시 일정 종료 예상',when.strftime('%H:%M'))
    if when>end:st.error('설정한 종료 시간을 초과합니다. 방문 장소나 체류 시간을 조정해 주세요.')
    else:st.success('임시 배정상 종료 시간 이내입니다. 실제 이동 시간과 영업시간은 검증되지 않았습니다.')
    st.download_button('📄 일정 텍스트 저장',data='\n'.join(output),file_name='dajeong-sea-route.txt',mime='text/plain')
    if st.button('처음부터 다시'):
        st.session_state.phase=1;st.rerun()

st.divider()
st.caption('시제품 v0.3 · 실시간 장소 검색/AI 추천/실제 경로/실제 사진은 아직 미연결 · API 키를 GitHub에 올리지 마세요.')

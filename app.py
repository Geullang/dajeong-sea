"""다정한 바다 산책 코스 메이커 | 물꼬방 2027-01-09 부산 자유탐방."""
from __future__ import annotations
import base64, csv, hashlib, html, io, json, os, zlib
from datetime import datetime, time
from pathlib import Path
from urllib.parse import quote
import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from zipfile import ZipFile, BadZipFile
from artwork import file_for,art_bytes
from services import AREA,AREAS,CATEGORIES,candidates_for_area,find_origin,plan_schedule,distance

ROOT=Path(__file__).resolve().parent
PUBLIC_URL=os.environ.get('PUBLIC_APP_URL','https://dajeong-sea-jnbtnkxhn5vhxwskczvu7p.streamlit.app/')
st.set_page_config(page_title='다정한 바다 | 물꼬방 산책 코스 메이커',page_icon='🌊',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Nanum+Myeongjo:wght@400;700&display=swap');
:root{--cream:#fbf8f0;--ink:#243c4b;--sea:#4a8498;--line:#d8e6e6}
html,body,[class*="css"],.stApp{font-family:'Noto Sans KR',sans-serif}
.stApp{background:linear-gradient(160deg,#fbf8f0 0%,#f8faf8 55%,#f4f8f8 100%);color:var(--ink)}
.block-container{max-width:1120px;padding:1.1rem 1.8rem 5rem}
h1,h2,h3{letter-spacing:-.035em;color:#26495b}
h1{font-size:2.6rem!important}h2{font-size:1.55rem!important}
.stButton>button[kind='primary'],button[data-testid='stBaseButton-primary']{background:#366f86;color:#fff;border-radius:22px;border:0;font-weight:700}
.stButton>button{border-radius:22px;border:1px solid #bcd4d8}
[data-testid='stMetric']{background:white;border:1px solid #e5eeee;padding:12px;border-radius:15px}
[data-testid='stVerticalBlockBorderWrapper']{background:rgba(255,255,255,.74);border-radius:20px}
[data-testid='stImage'] img{border-radius:16px;object-fit:cover}
div[data-baseweb="tag"]{background:#d5e9e8!important;color:#2e6072!important}
div[data-baseweb="tag"] span{color:#2e6072!important}
[data-testid='stForm']{border-radius:20px}
.hero-caption{text-align:center;margin:-.4rem 0 1.5rem;color:#687f86;font-size:.93rem}
.kicker{letter-spacing:.18em;color:#558ea0;text-align:center;font-size:.83rem;font-weight:700;margin-top:8px}
.hero-title{font-family:'Nanum Myeongjo',serif;text-align:center;font-size:clamp(1.8rem,4.5vw,3.25rem);font-weight:700;color:#2b5368;margin:6px 0}
.hero-sub{font-family:'Nanum Myeongjo',serif;text-align:center;font-size:1.15rem;color:#627a88;line-height:1.8}
.section-note{font-size:.88rem;color:#68828b}
.byline{font-size:.77rem;letter-spacing:.16em;text-align:center;color:#8a9393;margin-top:6px}
.area-note{border-left:3px solid #95bfcd;padding:12px 16px;color:#496774;background:#f0f7f7;border-radius:2px 12px 12px 2px;margin:12px 0 20px}
hr{border-color:#e0e8e4}
@media(max-width:700px){.block-container{padding:.6rem .9rem 4rem}h1{font-size:1.9rem!important}.hero-title{font-size:1.9rem!important}}
</style>''',unsafe_allow_html=True)


def safe(s):return html.escape(str(s or ''))

def image_for(p):
 # Individual JPG illustrations are packed in ONE ZIP to make GitHub web upload
 # possible (<100 uploaded files). Every member is a distinct complete JPG.
 filename=file_for(p['name'])
 bundle=ROOT/'assets'/'illustrations.zip'
 if bundle.exists():
  try:
   with ZipFile(bundle) as z:
    if filename in z.namelist():return io.BytesIO(z.read(filename))
  except (OSError, BadZipFile):pass
 # Places newly discovered by Kakao receive a fresh unique illustration.
 return io.BytesIO(art_bytes(p['name'],p['category']))

@st.cache_data(ttl=2400,show_spinner=False)
def load_area(area_id,_key):return candidates_for_area(area_id,_key,max_count=55)


from exports import pack_share,unpack_share,ics_text

def make_map(origin,plan):
 coords=[(origin['lat'],origin['lon'])]+[(p['lat'],p['lon']) for p in plan['ordered']]
 m=folium.Map(location=coords[min(1,len(coords)-1)],zoom_start=13,tiles='OpenStreetMap',control_scale=True)
 folium.Marker(coords[0],tooltip='출발: '+origin['name'],icon=folium.Icon(color='darkblue',icon='home',prefix='fa')).add_to(m)
 for n,p in enumerate(plan['ordered'],1):
  tooltip=html.escape(f"{n}. {p['name']} · {plan['schedule'][n-1]['arrive']}")
  folium.Marker((p['lat'],p['lon']),tooltip=tooltip,
    popup=folium.Popup(f'<b>{safe(p["name"])}</b><p>{safe(p["address"])}</p>',max_width=260),
    icon=folium.DivIcon(html=f'<div style="height:29px;width:29px;background:#39798d;color:white;border:2px solid #fff;border-radius:50%;font-size:14px;font-weight:bold;text-align:center;line-height:26px;box-shadow:0 2px 4px #777">{n}</div>')).add_to(m)
 for leg in plan['legs']:
  folium.PolyLine(locations=leg['shape'],color='#2a748f' if leg['verified'] else '#cc8b65',
   weight=4,opacity=.9,dash_array=None if leg['verified'] else '7,8',tooltip=('공개 보행/차량 경로' if leg['verified'] else '실제 경로 미검증 · 추정선')).add_to(m)
 m.fit_bounds(coords,padding=(30,30))
 return m

if 'selected' not in st.session_state:st.session_state.selected={}
if 'route' not in st.session_state:st.session_state.route=None
if 'loaded_token' not in st.session_state:
 st.session_state.loaded_token=str(st.query_params.get('plan',''))
 st.session_state.shared=unpack_share(st.session_state.loaded_token)
shared=st.session_state.shared

# Hero picture is a purpose-made original painting, not a location photograph.
st.markdown('<div class="kicker">🌊 2027 겨울 물꼬방</div>',unsafe_allow_html=True)
st.markdown('<div class="hero-title">다정한 바다<br>산책 코스 메이커</div>',unsafe_allow_html=True)
st.markdown('<div class="hero-sub">가벼운 마음이 멀리 간다</div><div class="byline">BY 물꼬방 약국</div>',unsafe_allow_html=True)
st.image(str(ROOT/'assets'/'hero.png'),use_container_width=True)
st.markdown('<div class="hero-caption">2027. 1. 9. 토요일 · 부산 · 교사들의 느긋한 동네 탐방</div>',unsafe_allow_html=True)

st.header('01  어떤 바다를 걸을까요?')
labels={a['name']:a['id'] for a in AREAS}
initial=(shared or {}).get('a',AREAS[0]['id'])
index=[a['id'] for a in AREAS].index(initial)
area_name=st.selectbox('탐방 지역 · 7개 코스',options=list(labels),index=index)
area_id=labels[area_name];area=AREA[area_id]
st.markdown(f'<div class="area-note"><b>{safe(area["name"])}</b> — {safe(area["subtitle"])}<br><small>후보지의 실제 위치는 카카오맵 결과로 확인하고, 적합한 장소만 표시합니다.</small></div>',unsafe_allow_html=True)
interest_default=(shared or {}).get('interests',['독립서점','카페·디저트','문화·공간','자연·풍경'])
interest_default=[v for v in interest_default if v in CATEGORIES]
interests=st.multiselect('관심 있는 분야 · 여러 개 선택',CATEGORIES,default=interest_default,placeholder='분야 선택')
with st.expander('나의 출발지와 시간 정하기',expanded=True):
 left,right=st.columns(2)
 with left:
  preset=st.selectbox('출발 방법',['직접 장소 입력','보다스테이 2·3호','보다스테이 더펜트','광안리273','현재 위치(GPS)'])
  custom=st.text_input('출발 장소/숙소 명칭',value='광안리해수욕장' if preset=='직접 장소 입력' else '',placeholder='예: 광안리해수욕장, 부산역, 숙소 이름',disabled=preset!='직접 장소 입력')
  people=int(st.number_input('모둠 인원',min_value=1,max_value=30,value=4,step=1))
  budget=st.selectbox('1인 식사 예산',['정하지 않음','1만원 이하','1만~2만원','2만~3만원','3만원 이상'])
  st.caption('식사 예산은 기록용입니다. 확인되지 않은 메뉴 가격으로 장소를 임의로 제외하지 않습니다.')
 with right:
  start_obj=st.time_input('탐방 시작',value=time.fromisoformat((shared or {}).get('start','10:00')))
  end_obj=st.time_input('탐방 종료',value=time.fromisoformat((shared or {}).get('end','16:00')))
  mode=st.radio('주요 이동 수단',['도보','택시','자동차'],index=['도보','택시','자동차'].index((shared or {}).get('mode','도보')),horizontal=True)
  meal_buffer=int(st.select_slider('식사 장소 추가 여유 시간',options=[0,10,20,30],value=10,format_func=lambda n:f'{n}분'))
 st.caption('GPS는 선택 사항입니다. 허용하지 않아도 숙소나 출발지를 입력하여 사용할 수 있습니다. 개인 위치를 코스 공유 링크에 넣지 않습니다.')
 location=None
 if preset=='현재 위치(GPS)':
  try:
   from streamlit_geolocation import streamlit_geolocation
   raw=streamlit_geolocation()
   if isinstance(raw,dict) and raw.get('latitude') is not None and raw.get('longitude') is not None:
    la,lo=float(raw['latitude']),float(raw['longitude'])
    if 34.6<la<36.0 and 128.5<lo<130.0:
     location={'name':'나의 현재 위치(GPS)','address':'GPS 위치(개인 정보)','lat':la,'lon':lo}
     st.success('현재 위치를 확인했습니다. 공유 링크에는 이 좌표를 넣지 않습니다.')
    else:st.warning('GPS 좌표가 부산 일대가 아닙니다. 직접 장소 입력 방식으로 변경할 수 있습니다.')
   else:st.info('위치 사용 버튼을 눌러 위치를 허용하세요. 거부하면 출발 방법을 직접 입력으로 바꾸세요.')
  except Exception:
   st.warning('브라우저 GPS 사용이 어려워요. 직접 장소 입력을 선택하면 동일하게 이용할 수 있습니다.')

key=''
try:key=st.secrets.get('KAKAO_REST_API_KEY','')
except Exception:pass
if not key:
 st.error('Streamlit Secrets에서 KAKAO_REST_API_KEY를 읽지 못했습니다. 장소 검색은 API 키가 있을 때만 제공됩니다. 키를 채팅에 입력하지 마세요.')
 st.stop()
with st.spinner(f'{area_name}의 실제 장소를 카카오맵과 대조하는 중입니다…'):
 places=load_area(area_id,key)
place_map={p['name']:p for p in places}
if shared and area_id==shared['a']:
 previous=st.session_state.selected.setdefault(area_id,[])
 for name in shared['s']:
  if name in place_map and name not in previous:previous.append(name)
selected=st.session_state.selected.setdefault(area_id,[])
selected[:]=[x for x in selected if x in place_map]

st.header('02  마음에 드는 장소를 담아요')
if len(places)<20:
 st.warning(f'카카오에서 이번 탐방 지역의 후보 {len(places)}곳을 확인했습니다. 20곳 미만이므로 아직 장소 데이터 검증이 충분하지 않습니다. 적합하지 않은 장소로 숫자를 채우지 않았습니다.')
else:st.caption(f'카카오 장소 정보가 확인된 후보 **{len(places)}곳** · 장소 카드의 이미지는 실제 사진이 아닌 각각의 창작 삽화입니다.')
if not places:
 st.error('현재 카카오 API에서 장소를 불러오지 못했습니다. API 설정 또는 통신 상황을 확인하고 잠시 뒤 다시 시도하세요.')
 st.stop()

active=[c for c in CATEGORIES if c in interests]
if not active:st.info('관심 분야를 한 가지 이상 골라 주세요.')
show_all=st.toggle('이 지역의 전체 후보 보기 (기본: 분야별 우선 추천 3~5곳)',value=False)
display=[]
for cat in active:
 cat_places=[p for p in places if p['category']==cat]
 if not show_all:cat_places=cat_places[:5]
 display.extend(cat_places)
counts={c:sum(p['category']==c for p in places) for c in CATEGORIES}
st.caption(' · '.join(f'{c} {counts[c]}' for c in CATEGORIES))

def toggle_selection(name):
 current=st.session_state.selected.setdefault(area_id,[])
 if name in current:current.remove(name)
 else:current.append(name)
 st.session_state.route=None

if active and not display:st.info('해당 분야의 실제 확인된 후보가 없습니다. 다른 분야를 선택하거나 전체 후보를 살펴보세요.')
for cat in active:
 group=[p for p in display if p['category']==cat]
 if not group:continue
 st.subheader(f'{cat}  ·  {counts[cat]}곳')
 for j in range(0,len(group),3):
  cols=st.columns(3,gap='medium')
  for col,p in zip(cols,group[j:j+3]):
   with col:
    with st.container(border=True):
     st.image(image_for(p),use_container_width=True)
     st.markdown(f'**{safe(p["name"])}**')
     st.caption(('✦ 물꼬방 추천 후보' if p['editorial'] else '◦ 지도에서 찾은 추가 후보')+' · '+str(p['minutes'])+'분 머무름')
     st.write(p['description'])
     st.caption('**이곳을 권하는 이유**  '+p['why'])
     st.caption('📍 '+p['address'])
     st.caption('💳 '+p['budget_note']+'  ·  🕒 '+p['hours'])
     if p['phone']:st.caption('☎ '+p['phone'])
     st.caption('ⓘ '+p['notice'])
     if p['url']:st.markdown(f'[카카오맵 장소 정보 ↗]({p["url"]})')
     st.button('✓ 내 코스에서 빼기' if p['name'] in selected else '+ 내 코스에 담기',key='btn_'+area_id+'_'+hashlib.md5(p['name'].encode()).hexdigest()[:13],
      on_click=toggle_selection,args=(p['name'],),use_container_width=True,type='primary' if p['name'] in selected else 'secondary')

st.divider()
st.header('03  우리의 산책길을 만들어요')
st.caption('선택한 장소는 여러 개 담을 수 있습니다. 경로 계산은 실제 도로·보행망을 우선 이용하며, 실패 시 추정치로 별도 표시합니다.')
if selected:
 st.write('**담은 장소 ('+str(len(selected))+'곳)**  '+ '  ·  '.join(selected))
 stay_changes={}
 with st.expander('장소별 체류 시간 조정',expanded=False):
  for name in selected:
   stay_changes[name]=int(st.number_input(name+' · 머무를 시간(분)',min_value=10,max_value=180,step=5,
     value=int(place_map[name]['minutes']),key='stay_'+area_id+'_'+hashlib.md5(name.encode()).hexdigest()[:13]))
 cols=st.columns([1,1,2])
 with cols[0]:
  if st.button('전체 선택 해제',use_container_width=True):
   selected.clear();st.session_state.route=None;st.rerun()
 with cols[1]:
  if st.button('코스 다시 계산',use_container_width=True):
   st.session_state.route=None
else:st.info('위의 장소 카드에서 가고 싶은 곳을 담으면 이곳에 코스가 나타납니다.')

origin_text=custom if preset=='직접 장소 입력' else {'보다스테이 2·3호':'부산 광안리 보다스테이','보다스테이 더펜트':'보다스테이 더펜트','광안리273':'광안리273'}.get(preset,'')
@st.cache_data(ttl=2400,show_spinner=False)
def lookup_origin(s,_key):return find_origin(_key,s)
origin=location or (lookup_origin(origin_text,key) if origin_text else None)
if origin:st.caption(f'출발: {origin["name"]} · {origin["address"]}')
elif selected:st.warning('출발지 주소를 아직 확인하지 못했습니다. 장소 이름을 더 구체적으로 입력하거나 GPS를 허용해 주세요.')

if st.button('🌊 선택한 장소로 코스 만들기',type='primary',use_container_width=True,disabled=not bool(selected) or not bool(origin)):
 try:
  picks=[{**place_map[n],'minutes':stay_changes.get(n,place_map[n]['minutes'])} for n in selected if n in place_map]
  if len(picks)>9:st.info('선택 장소가 많아 경로 계산에 시간이 더 걸릴 수 있습니다.')
  with st.spinner('장소의 순서를 정하고 실제 도로·보행 경로를 조회하고 있어요…'):
   result=plan_schedule(origin,picks,start_obj.strftime('%H:%M'),end_obj.strftime('%H:%M'),mode,meal_buffer)
  st.session_state.route={'plan':result,'origin':origin,'area':area_id,'chosen':list(selected),'settings':(start_obj.strftime('%H:%M'),end_obj.strftime('%H:%M'),mode,meal_buffer)}
 except Exception as e:st.error('코스를 생성하지 못했습니다: '+str(e))

route=st.session_state.route
if route and route['area']==area_id and all(n in selected for n in route['chosen']):
 plan=route['plan'];st.subheader('한눈에 보는 우리의 코스')
 c1,c2,c3=st.columns(3)
 c1.metric('전체 예상 시간',f"{plan['minutes']//60}시간 {plan['minutes']%60}분")
 c2.metric('마지막 장소 종료',plan['end'])
 c3.metric('예정된 종료 시간',plan['deadline'])
 if plan['fits']:st.success('입력하신 탐방 시간 안에 방문할 수 있는 일정으로 계산했습니다. 단, 대기와 영업시간은 최종 확인해 주세요.')
 else:st.warning(f'현재 일정은 종료 시각보다 **{plan["over_minutes"]}분** 늦습니다. 방문 장소를 줄이거나 체류·시작 시간을 조정해 다시 계산해 주세요.')
 if not plan['all_verified']:
  st.warning('일부 구간에서 공개 경로 서비스가 응답하지 않았습니다. 주황색 점선과 해당 이동시간은 직선거리 기반 보정 추정이며, 실제 도보/차량 길찾기가 아닙니다.')
 else:st.caption('파란 실선은 공개 Valhalla/OSM 보행·차량 경로를 조회하여 표시했습니다. 택시는 승차 대기 시간 5분을 추가했습니다.')
 m=make_map(route['origin'],plan)
 components.html(m.get_root().render(),height=485,scrolling=False)
 data=[]
 for r in plan['schedule']:
  data.append({'순서':r['number'],'장소':r['name'],'도착':r['arrive'],'체류':f"{r['stay']}분",'출발':r['leave'],
   '직전 이동':f"{r['travel']}분",'이동 근거':'실제 공개 경로' if r['verified'] else '미검증 추정'})
 st.dataframe(pd.DataFrame(data),use_container_width=True,hide_index=True)
 with st.expander('장소별 유의 사항 및 이동 검증 내역',expanded=False):
  for r in plan['schedule']:
   st.markdown(f"**{r['number']}. {r['name']}** · {r['arrive']} 도착 / {r['stay']}분 체류")
   st.caption('주소: '+r['address']+' · '+r['notice']+' · '+r['provider'])
 st.caption('카카오 로컬 API는 영업시간·휴무·가격·예약 상태를 보장하지 않습니다. 2027년 1월 9일 이용 가능 여부는 장소 링크/전화로 방문 전에 확인하세요. 인원·식사 예산은 단체 좌석과 메뉴를 확인하기 위한 참고 설정이며 자동 확약이 아닙니다.')
 st.subheader('저장하고 모둠에 공유하기')
 params={'start':start_obj.strftime('%H:%M'),'end':end_obj.strftime('%H:%M'),'mode':mode,'interests':interests}
 token=pack_share(area_id,selected,params)
 share_url=PUBLIC_URL.rstrip('/')+'/?plan='+token
 st.code(share_url,language=None)
 st.caption('위 링크를 복사해 공유하세요. 출발지의 GPS 좌표는 링크에 저장되지 않습니다. 공유받은 사람은 자기 출발지를 다시 정할 수 있습니다.')
 exported={'event':'2027-01-09 물꼬방','area':area['name'],'participants':people,'meal_budget':budget,
  'mode':mode,'origin_name':route['origin']['name'] if route['origin']['name']!='나의 현재 위치(GPS)' else '현재 위치(비공개)',
  'schedule':plan['schedule'],'warning':'영업시간·가격·예약은 장소별로 재확인 필요'}
 x,y,z=st.columns(3)
 with x:st.download_button('일정표 CSV',pd.DataFrame(data).to_csv(index=False).encode('utf-8-sig'),file_name='물꼬방_산책일정.csv',mime='text/csv',use_container_width=True)
 with y:st.download_button('코스 저장 JSON',json.dumps(exported,ensure_ascii=False,indent=2).encode('utf-8'),file_name='물꼬방_나의산책.json',mime='application/json',use_container_width=True)
 with z:st.download_button('캘린더에 담기 ICS',ics_text(plan,plan['ordered']).encode('utf-8'),file_name='물꼬방_산책일정.ics',mime='text/calendar',use_container_width=True)
 st.info('수정하려면 위의 장소 카드를 추가하거나 빼고, 시작·종료 시각을 바꾼 뒤 「코스 만들기」를 다시 누르세요.')

st.divider()
st.markdown('**다정한 바다 산책 코스 메이커**  ·  By 물꼬방 약국')
st.caption('장소 정보: Kakao Local API · 보행/차량 경로: Valhalla / OpenStreetMap(응답 시) · 기본 지도: © OpenStreetMap 기여자 · 삽화: 장소별 독립 창작 스케치 · 2027.1.9 운영 정보는 사전 재확인')

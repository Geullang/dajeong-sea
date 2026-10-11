"""다정한 바다 산책 코스 메이커 — Streamlit custom component v2.
One visible screen at a time, server-side API secrets, real-place verification.
"""
from __future__ import annotations
import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import streamlit as st
from engine import verified_places, compact_recommendations, create_route, photo_for_place
from services import AREAS, AREA, find_origin

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='다정한 바다 산책 코스 메이커',page_icon='🌊',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
  [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"],
  [data-testid="stDecoration"], #MainMenu, footer{display:none!important}
  .stApp{background:linear-gradient(145deg,#eaf6fc,#f9faf9 70%,#e4f3fb)}
  .block-container{padding:.6rem .4rem 0!important;max-width:100%!important}
  [data-testid="stVerticalBlock"]{gap:0!important}
  iframe{border:0!important}
</style>''',unsafe_allow_html=True)

DEFAULT_ORIGINS={'namcheon':'남천역','gwangan':'광안리해수욕장','domoheon':'도모헌',
                 'yeongdo':'흰여울문화마을','yacht':'수영만요트경기장',
                 'train':'해운대 미포정거장','bosu':'보수동 책방골목'}
FORM={'area':'namcheon','origin':'남천역','gps':None,'interests':['식사','카페·디저트','문화·공간'],
      'destination_same':True,'destination':'','start':'11:00','end':'16:00','people':3,'mode':'도보','budget':'제한 없음'}

for key,val in {'stage':1,'form':FORM.copy(),'selected':[],'recommendations':[],
                'route':None,'error':'','photos':{}}.items():
    if key not in st.session_state:st.session_state[key]=val

def get_secret(name):
    try:return st.secrets.get(name,'')
    except Exception:return ''

KAKAO=get_secret('KAKAO_REST_API_KEY')
GOOGLE=get_secret('GOOGLE_PLACES_API_KEY')

@st.cache_data(ttl=1800,show_spinner=False)
def check_places(area,key):
    if not key:return []
    return verified_places(area,key)

def get_google_photo(place_id,place_name,lat,lon,key):
    if not key:return None
    return photo_for_place({'name':place_name,'lat':lat,'lon':lon},key)

def origin_for(form):
    loc=form.get('gps')
    if isinstance(loc,dict) and 'lat' in loc and 'lon' in loc:
        try:
            lat=float(loc['lat']);lon=float(loc['lon'])
            if 34.7<=lat<=35.6 and 128.7<=lon<=129.5:
                return {'id':'start','name':'현재 위치 (GPS)','lat':lat,'lon':lon,'address':'GPS 위치'}
        except (ValueError,TypeError):pass
    text=(form.get('origin') or DEFAULT_ORIGINS.get(form.get('area'),'')).strip()
    if not text:return None
    p=find_origin(KAKAO,text)
    if p:p.update(id='start')
    return p

def load_recommendations(form):
    area=form['area'];places=check_places(area,KAKAO)
    wanted=form.get('interests',[])
    # Small number of venue cards. 3 per category maximum; never display 154 cards.
    cards=compact_recommendations(places,wanted,limit=3)
    return cards,places

def act(event):
    kind=event.get('type');value=event.get('payload') or {}
    if kind=='home':
        st.session_state.stage=1
    elif kind=='back':
        st.session_state.stage=max(1,st.session_state.stage-1)
    elif kind=='edit':
        st.session_state.stage=2
    elif kind=='map':
        st.session_state.stage=4
    elif kind=='search':
        form=value.get('form') or {}
        if form.get('area') not in AREA:
            st.session_state.error='탐방 지역을 다시 선택해 주세요.';return
        if form.get('end','')<=form.get('start',''):
            st.session_state.error='종료 시각은 시작보다 늦어야 합니다.';return
        st.session_state.form=form
        st.session_state.route=None
        st.session_state.selected=[]
        st.session_state.photos={}
        if not KAKAO:
            st.session_state.error='카카오 REST API 키가 보이지 않습니다. Streamlit Secrets의 KAKAO_REST_API_KEY를 확인해 주세요.'
            st.session_state.stage=2;st.session_state.recommendations=[];return
        cards,_=load_recommendations(form)
        st.session_state.recommendations=cards
        st.session_state.stage=2
        st.session_state.error='' if cards else '카카오에서 해당 지역의 장소를 충분히 확인하지 못했습니다. 다른 지역 또는 시간을 선택해 주세요.'
    elif kind=='route':
        form=st.session_state.form
        st.session_state.selected=value.get('selected',[])
        if not KAKAO:return
        org=origin_for(form)
        if not org:
            st.session_state.error='출발지를 카카오에서 확인하지 못했습니다. 첫 화면에서 더 구체적인 장소명을 입력해 주세요.';return
        # Selections are a preference. App determines route order regardless of click order.
        places=check_places(form['area'],KAKAO)
        selected=st.session_state.selected
        endpoint=None
        if form.get('destination_same',True):
            endpoint={**org,'id':'end'}
        elif form.get('destination','').strip():
            endpoint=find_origin(KAKAO,form['destination'].strip())
            if not endpoint:
                st.session_state.error='도착지를 확인하지 못했습니다. 첫 화면에서 도착 장소를 다시 입력해 주세요.';return
            endpoint['id']='end'
        result=create_route(KAKAO,form['area'],org,places,form['interests'],form['start'],form['end'],form['mode'],selected_ids=selected or None,endpoint=endpoint)
        if result.get('error'):
            st.session_state.error=result['error'];return
        st.session_state.route=result
        st.session_state.error=''
        st.session_state.stage=3

# Display only the cards that matter, and never leak API keys to JS/browser.
if st.session_state.stage==2 and GOOGLE and st.session_state.recommendations and not st.session_state.photos:
    cards=st.session_state.recommendations[:10]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={p['id']:pool.submit(get_google_photo,p['id'],p['name'],p['lat'],p['lon'],GOOGLE) for p in cards}
        st.session_state.photos={ident:f.result() for ident,f in futures.items() if f.result() is not None}

hero64=base64.b64encode((ROOT/'hero.jpg').read_bytes()).decode('ascii')
hero_uri='data:image/jpeg;base64,'+hero64
area_id=st.session_state.form.get('area','namcheon')
ui=st.components.v2.component(
    name='dajeong_four_screen_app',
    html='<div class="app-root" aria-live="polite"></div>',
    css=(ROOT/'ui.css').read_text(encoding='utf-8'),
    js=(ROOT/'ui.js').read_text(encoding='utf-8'),
)
result=ui(
    key='dajeong-main',
    data={'stage':st.session_state.stage,'areas':AREAS,'area_name':AREA.get(area_id,AREA['namcheon'])['name'],
          'hero':hero_uri if st.session_state.stage==1 else '',
          'form':st.session_state.form,'recommendations':st.session_state.recommendations,
          'selected':st.session_state.selected,'route':st.session_state.route,
          'photos':st.session_state.photos,'error':st.session_state.error},
    on_action_change=lambda:None,
)
if result.action:
    act(result.action)
    st.rerun()

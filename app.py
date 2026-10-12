import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
st.set_page_config(page_title='2027 겨울 물꼬방 약국 | 산책 코스 메이커',layout='centered',initial_sidebar_state='collapsed')
st.markdown('''<style>#MainMenu,footer,header,[data-testid="stToolbar"]{display:none!important}.block-container{padding:0!important;max-width:520px!important}iframe{border:0!important}body{background:#eaf3fa}</style>''',unsafe_allow_html=True)
html=Path(__file__).with_name('mobile.html').read_text(encoding='utf-8')
components.html(html,height=920,scrolling=False)

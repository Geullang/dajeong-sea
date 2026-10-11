# 다정한 바다 · 산책 코스 메이커

2027년 1월 9일 전국국어교사모임 부산 자유탐방 Streamlit 시제품.

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 배포

1. GitHub에 새 저장소를 만든 후 `app.py`, `requirements.txt`를 저장소 최상위에 업로드합니다.
2. https://share.streamlit.io/ 에 GitHub로 로그인합니다.
3. Create app → 저장소, 브랜치 `main`, 진입 파일 `app.py`를 지정합니다.
4. Deploy를 누르면 `*.streamlit.app` 링크가 생성됩니다.

## 제한사항

현재 지역별 일부 장소 데이터는 시연용 목록입니다. 실제 검색·사진·정확한 동선·영업정보·AI 추천을 제공하지 않습니다. 위치 확인과 Streamlit Secrets를 사용하는 API 연동은 다음 개발 단계입니다.

카카오 또는 AI API 키는 GitHub에 저장하지 마세요. Streamlit Community Cloud 앱 설정의 Secrets에 별도로 등록하세요.

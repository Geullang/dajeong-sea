# 다정한 바다 산책 코스 메이커 — 업로드 오류 수정본

## GitHub에 올리는 방법 (하위 폴더 없이 12개 파일)

1. 이 ZIP을 한 번 압축 해제합니다.
2. 압축을 푼 폴더 안의 **파일 전부(12개)** 를 선택합니다. 폴더 자체나 ZIP 파일을 GitHub에 넣는 것이 아니라, **폴더 안에 보이는 12개 파일을 모두** 선택하세요.
3. 기존 GitHub 저장소 https://github.com/Geullang/dajeong-sea 에서 **Add file → Upload files** 를 눌러 파일 12개를 끌어 놓습니다.
4. 기존 파일을 덮어쓸지 묻는다면 새 파일로 교체하고 **Commit changes**를 누릅니다.
5. GitHub 저장소 첫 화면에서 `app.py`, `services.py`, `requirements.txt`, `areas.json`, `places.csv`, `illustrations.zip`, `hero.png`가 전부 보이는지 확인합니다.
6. 기존 Streamlit 앱을 새로 고침합니다. 이전 오류가 남아 있으면 Streamlit의 **Manage app → Reboot app**을 누릅니다.

### 이번 수정 내용

- 기존 오류: `data/areas.json` 파일이 GitHub에 업로드되지 않아 앱이 시작조차 되지 않음.
- 이제 `areas.json`과 `places.csv`를 저장소 첫 화면(최상위)에 놓도록 하여 폴더째 올리는 문제를 피함.
- 두 데이터 파일을 미처 올리지 않더라도 `services.py`의 내장 백업 데이터로 실행할 수 있도록 처리.
- `illustrations.zip`과 `hero.png`도 최상위에서 바로 인식함. `illustrations.zip` 안에는 장소별 고유 JPG 130개가 있으며 풀지 않습니다.
- 앱 UI·7코스·기존 후보 154항목·추천 분류 6개·지도/일정/공유 기능은 유지함.
- **추가 API 키는 필요 없습니다**. Streamlit Secrets에 이미 저장된 `KAKAO_REST_API_KEY`를 그대로 이용합니다.

### 확인 사항

소스 데이터가 정상 연결돼도 **카카오 API에서 확인되는 후보 수는 지역별로 다를 수 있습니다.** 154건은 편집 후보 데이터이고 모든 업체의 현재 영업 사실을 보증하는 수치는 아닙니다. GPS 권한·외부 도로 길찾기·실제 Streamlit Cloud 화면은 배포 후 확인이 필요합니다.

### 배포 전 테스트

`python test_project.py` — 데이터 및 이미지 유효성, 백업 로딩, 경로 계산 등을 네트워크 없이 점검합니다.

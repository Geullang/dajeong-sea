# 🌊 다정한 바다 산책 코스 메이커

2027년 1월 9일(토), 전국국어교사모임 물꼬방 부산 모둠별 자유 탐방.

> 중요: 이 파일은 **실행 가능한 개발·현장검증 후보본**입니다. 작성된 장소 후보 154건의 2027년 1월 실제 영업 여부, 실사용 Streamlit 앱 화면, 외부 지도 API 응답, GPS 브라우저 권한은 아직 현장에서 검증되지 않았습니다. 충분히 시험한 뒤 행사에 사용해 주세요. 확인하지 않은 사항을 완료로 표시하지 않았습니다.

## ZIP을 내려받은 뒤 배포하는 방법

1. ZIP 압축을 풉니다. 폴더 안에 `app.py`, `requirements.txt`, `assets`, `data`가 보이는지 확인하세요.
2. https://github.com/Geullang/dajeong-sea 로 가서 **Add file → Upload files**를 누르세요.
3. 압축을 푼 폴더 **내부의 모든 파일과 폴더**를 선택하거나 끌어다 놓으세요. `assets`와 `data` 디렉터리는 안에 든 파일까지 업로드되어야 합니다. 기존 `app.py`, `requirements.txt`는 새 파일로 교체합니다. 본문에 파일이 `dajeong-sea-project/app.py`처럼 별도 하위 폴더로 들어가지 않도록 주의하세요.
4. **Commit changes**를 누르세요.
5. 기존 Streamlit 앱(https://dajeong-sea-jnbtnkxhn5vhxwskczvu7p.streamlit.app/)을 열고 변경 사항이 반영되는지 보세요. 앱이 자동으로 재배포되지 않았다면 Streamlit Cloud 관리 화면에서 **Reboot app**을 선택합니다.
6. 오류가 보이면 Streamlit Cloud의 Manage app → Logs를 확인합니다.

**카카오 REST 키:** 기존 Streamlit Secrets의 `KAKAO_REST_API_KEY`를 그대로 읽습니다. ZIP이나 GitHub 파일에 API 키를 넣지 않았습니다. 대화창에 공개할 필요도 없습니다.

### 행사 전 필수 시험

- 모바일 브라우저에서 화면이 세로로 정상 정렬되고 카드 삽화가 보이는지 확인
- 7개 코스 각각에서 카카오가 일치시킨 장소 후보 **20곳 이상**을 실제로 표시하는지 확인. 미달 시 '20곳 미만' 경고가 나오고, 가짜 데이터를 채워 넣지 않음
- GPS 허용 / 차단 두 경우와 숙소·출발지 직접 입력 두 경우 확인
- 각 코스에서 장소 3~5곳을 담고 실제 보행 경로가 **파란 실선**으로 표시되는지 확인. 주황 점선은 검증되지 않은 보정 추정으로 **실제 길찾기라고 주장하지 않음**
- 생성된 일정의 시간·이동수단·체류시간, 장소별 카카오 상세 링크 확인
- 모둠 간 공유 URL, CSV·JSON·ICS 다운로드 확인
- 휴무·단체석·예약·가격·2027년 1월 9일 영업 여부를 운영자가 각 업체에 최종 확인

## 기능 및 주요 설계

- 코스 7개: 남천동, 광안리 책과 산책, 도모헌 일대, 영도, 해운대 요트, 해운대 해변열차, 보수동 책방골목
- 코스당 **편집자 후보 22건**; 총 154개의 코스별 후보 연결, 중복을 제외한 **고유 장소명 130개**
- 이미지 130개는 `assets/illustrations.zip` 안에 **서로 다른 JPG 파일 130개**로 보관한 고유 일러스트레이션입니다. GitHub 웹 업로드가 한 번에 100개 파일로 제한되므로, 앱이 이 내부 ZIP에서 개별 파일을 바로 읽도록 구성했습니다(두 번째 ZIP을 따로 풀 필요 없음). 장소마다 이름·성격·색·구도를 달리한 창작 펜·수채화풍 스케치. 카카오 결과로 새로 발견된 장소도 즉시 별도 그림을 생성해 표시할 수 있도록 `artwork.py` 포함. 실제 현장 사진은 아님
- 첫 화면 6개 복수 선택 관심 분야: 식사 / 카페·디저트(빵집 포함) / 독립서점 / 소품샵 / 문화·공간 / 자연·풍경
- 분야별 5곳 우선 표시, 전체 보기 전환, 방문 장소 추가/제거, 체류 시간 조정, 출발지·시각·인원·이동수단 설정
- 현재 위치 선택에는 브라우저 GPS 권한 필요(선택적). GPS 없이도 출발지 검색으로 동작
- 카카오 Local API는 **실제 장소명/주소/전화번호/좌표/카카오 링크 확인** 용도. 운영시간·휴무·가격·실시간 예약 여부 제공 API가 아님
- 보행/차량 길찾기는 공개 **Valhalla/OSM**, 실패 시 공개 **OSRM/OSM 보행·차량망**으로 한 번 더 확인. 둘 다 실패하면 추정치를 **명시적으로 구분**
- 길찾기 서버의 점선/실선 범례와 날짜별 일정표, 공유 링크, CSV/JSON/ICS 저장 제공. GPS 좌표는 공유 링크에 넣지 않음
- 영업시간 검증 데이터가 없으므로 자동 휴무 충돌 판정 불가. 식사 예산·인원은 참고/기록용이며 확인되지 않은 가격으로 임의 제외하지 않음

## 주요 파일

```text
app.py                 Streamlit UI
services.py            카카오 장소 검증, 외부 보행·차량망, 방문순서·일정
exports.py             코스 공유 및 ICS 파일 생성
artwork.py             고유 창작 삽화 생성 및 누락 시 현장 그리기
build_dataset.py       장소 후보 CSV 재생성 도구(일반 사용자 실행 불필요)
requirements.txt       Streamlit Cloud 의존성
assets/hero.png        첫 화면 부산 바다 창작 그림
assets/illustrations.zip 130개 장소별 고유 JPG가 개별 파일로 들어 있는 삽화 꾸러미
 data/areas.json       7개 코스
 data/places.csv       코스별 154개 후보(중복 포함)
 tests/test_project.py 데이터·경로·공유 테스트
검증보고서.md            확인 완료와 미확인 사항
```

## 개발자가 시험하는 방법

```bash
pip install -r requirements.txt
streamlit run app.py
python -m unittest discover -s tests -v
```

## 자료 확인 메모

- 기존 저장소: https://github.com/Geullang/dajeong-sea (이전 시제품의 대상·주요 후보 검토)
- 부산시 도모헌 공식 안내: https://www.busan.go.kr/domoheon/notice
- 부산문화재단 F1963 소개: https://www.bscf.or.kr/view.do?no=1007
- 보수동 책방골목 관광정보: https://access.visitkorea.or.kr/ms/detail.do?cotId=b5220abc-5e47-432d-89c3-97227372069f
- 수영구 망미 역사문화자원: https://www.suyeong.go.kr/down/alley_0001_down.pdf
- 보행·차량 라우팅 엔진: https://valhalla.github.io/valhalla/api/turn-by-turn/overview/
- 공개 OSRM 데모 서버 및 공정사용 조건: https://routing.openstreetmap.de/about.html

일부 후보는 이전 대화에서 언급된 이름, 지도 검색과 공개 장소 소개를 바탕으로 정리한 **편집 후보**입니다. 일괄적인 2026년 10월 영업 확인·2027년 1월 예약 확인을 완료한 명단이 아닙니다. 앱은 실행 시 카카오의 실제 장소 기록과 일치하는 후보만 제시하고, 부족하면 주변의 다른 실제 장소를 조회합니다. 공개 보행 라우팅 데모 서버는 행사 당일 70명의 동시 사용에 대한 서비스 보장이 없으므로 사전 부하·접속 시험과 안정적인 경로 서비스 대안 검토가 남아 있습니다.

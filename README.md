# ClassFit Streamlit Custom Component 최종본

가천대학교 강의실 예약 및 시간표 충돌 검사 시스템입니다.

이번 버전은 기존 Streamlit 기본 위젯 UI를 버리고, React 기반 Custom Component를 Streamlit 내부에 삽입한 구조입니다. 따라서 화면은 React 디자인으로 유지하고, DB 처리와 트랜잭션은 Python/SQLite에서 수행합니다.

## 1. 핵심 구조

```text
ClassFit/
├── app.py                         # Streamlit 실행 파일
├── database.py                    # SQLite DB 처리 로직
├── classfit.db                    # 실제 DB 파일
├── schema.sql                     # DB 스키마
├── requirements.txt               # Python 의존성
├── data/
│   ├── rooms.csv
│   ├── blocked_schedules.csv
│   └── users_sample.csv
└── component/
    ├── src/                       # React Custom Component 원본
    ├── dist/                      # 빌드된 React UI, Streamlit이 여기서 화면을 불러옴
    └── package.json
```

## 2. 왜 Custom Component 구조인가?

이전 Streamlit 버전은 `st.selectbox`, `st.button`, `st.date_input` 같은 기본 위젯 위에 CSS를 덮어씌우는 방식이어서 드롭다운 색상, 카드 배치, 로그인 화면이 자주 깨졌습니다.

이번 버전은 React UI 전체를 Streamlit Custom Component로 분리했습니다.

```text
React Custom Component
→ 화면, 로그인 폼, 카드, 탭, 버튼, 현황판 담당

Streamlit app.py
→ Python 세션 상태, DB 함수 호출, action 처리 담당

SQLite classfit.db
→ users, rooms, blocked_schedules, reservations, reservation_history 저장
```

즉, 화면은 React가 담당하고 예약 데이터는 Python DB 로직이 담당합니다.

## 3. 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 Streamlit 주소가 열리면 React 기반 ClassFit 화면이 표시됩니다.

## 4. 로그인 방식

비밀번호 입력은 없습니다. 오직 학번 또는 교수 학수번호만 입력합니다.

### 학생 로그인 범위

```text
202130001 ~ 202139999
202230001 ~ 202239999
202330001 ~ 202339999
202430001 ~ 202439999
202530001 ~ 202539999
202630001 ~ 202639999
```

예시:

```text
202430001
202630001
```

### 교수 로그인 ID

```text
08095006
13970001
14268001
14271001
14283001
14798002
```

## 5. 주요 기능

### 학생

- 학번 기반 로그인
- 날짜/교시/인원/건물 조건 입력
- 사용 가능한 강의실 추천
- 강의실 예약 신청
- 내 예약 조회
- 예약 취소
- 실시간 현황판 조회
- 예약 이력 확인

### 교수

- 교수 학수번호 기반 로그인
- 빈 강의실 조회
- 전체 예약 조회
- 실시간 현황판 조회
- 예약 이력 조회
- 시연용 예약 초기화

## 6. DB 실시간 연동 방식

예약 신청 버튼을 누르면 React Component가 Streamlit에 action을 전달합니다.

```text
React 버튼 클릭
→ Streamlit.setComponentValue(action)
→ app.py에서 action 처리
→ database.py의 add_reservation() 호출
→ SQLite DB 저장
→ st.rerun()
→ React Component에 최신 DB 데이터 재전달
```

따라서 화면에서 보이는 데이터는 매번 DB 기준으로 갱신됩니다.

## 7. 중복 예약 방지

중복 예약 방지는 React에서 하지 않고 `database.py`에서 처리합니다.

`add_reservation()` 함수 내부에서 다음 순서로 처리됩니다.

```text
1. BEGIN IMMEDIATE 트랜잭션 시작
2. 기존 수업 blocked_schedules 충돌 검사
3. 기존 실시간 예약 reservations 충돌 검사
4. 충돌 없을 때만 reservations INSERT
5. reservation_history에 CREATE 기록
6. COMMIT
```

따라서 시연 중 두 사용자가 같은 강의실, 같은 시간대를 동시에 예약하려고 해도 DB 트랜잭션 단계에서 중복 예약이 차단됩니다.

## 8. 사용한 자료구조와 알고리즘

| 구분 | 적용 위치 | 설명 |
|---|---|---|
| 관계형 테이블 | `rooms`, `users`, `reservations`, `reservation_history` | 데이터를 역할별로 분리 저장 |
| B-Tree 인덱스 | SQLite 인덱스 | 강의실/날짜/교시 조건 조회 성능 개선 |
| 구간 겹침 검사 | `add_reservation()`, `get_conflict_details()` | 기존 예약과 새 예약의 시간 겹침 판단 |
| Hash 기반 사용자 탐색 | `login_with_identifier()` | 학번/학수번호 기반 사용자 조회 |
| Undo/Redo 스택 | `app.py` 세션 상태 | 예약 생성/취소 작업 되돌리기 |
| 우선순위 기반 추천 | React Component | 정원, 우선순위, 접근성 점수 기반 정렬 |

## 9. React Component를 수정해야 할 때

화면을 수정하려면 `component/src/main.jsx` 또는 `component/src/style.css`를 수정한 뒤 빌드합니다.

```bash
cd component
npm install
npm run build
```

빌드 결과는 `component/dist/`에 생성되고, `app.py`는 이 폴더를 읽어 화면에 표시합니다.

## 10. 제출 시 포함해야 할 파일

```text
app.py
database.py
classfit.db
schema.sql
requirements.txt
data/
component/dist/
component/src/
README.md
```

`component/dist/`가 포함되어 있으므로 제출 환경에서 npm build를 다시 하지 않아도 됩니다.

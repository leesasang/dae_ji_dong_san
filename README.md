# ClassFit Streamlit Custom Component v1.4

가천대학교 강의실 예약 및 시간표 충돌 검사 시스템입니다. Streamlit은 Python 세션/SQLite 로직을 담당하고, 화면은 React Custom Component가 담당합니다.

## v1.4 수정 사항

- 교수 계정 화면을 학생 계정과 동일하게 변경
  - `예약하기`
  - `내 예약`
  - `실시간 현황판`
- 관리자 계정 추가
  - 로그인 코드: `admin`
  - 관리자만 `전체 예약`, `예약 이력`, `예약 관리` 접근 가능
- 학생/교수에게 전체 예약자 정보와 예약 이력 데이터 미전달
- 학생/교수는 본인 예약만 취소 가능
- 관리자만 전체 예약 초기화 가능
- 새로고침 시 로그인 유지
  - React Custom Component 내부 localStorage에 로그인 식별자 저장
  - Streamlit 세션이 초기화되면 저장된 식별자로 자동 재로그인 시도
- 컴포넌트 캐시 충돌 방지를 위해 Streamlit component name을 `classfit_react_ui_v14`로 변경

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 화면 수정 후 빌드

```bash
cd component
npm install
npm run build
```

## 구조

```text
classfit_streamlit_custom_component/
├── app.py
├── database.py
├── classfit.db
├── schema.sql
├── requirements.txt
├── component/
│   ├── src/
│   │   ├── main.jsx
│   │   └── style.css
│   └── dist/
└── data/
```

## 로그인 계정

- 학생: `202130001` ~ `202139999`, `202230001` ~ `202239999`, ..., `202630001` ~ `202639999`
- 교수: `08095006`, `13970001`, `14268001`, `14271001`, `14283001`, `14798002`
- 관리자: `admin`

비밀번호 없이 학번, 교수 학수번호 또는 관리자 코드만 입력합니다.

## 권한 구조

| 역할 | 접근 화면 |
|---|---|
| 학생 | 예약하기, 내 예약, 실시간 현황판 |
| 교수 | 예약하기, 내 예약, 실시간 현황판 |
| 관리자 | 예약하기, 내 예약, 실시간 현황판, 전체 예약, 예약 이력, 예약 관리 |

## DB 상태

초기 제출용 DB는 다음 상태입니다.

| 테이블 | 개수 |
|---|---:|
| rooms | 40 |
| blocked_schedules | 896 |
| users | 60001 |
| reservations | 0 |
| reservation_history | 0 |

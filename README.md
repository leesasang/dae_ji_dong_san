# classfit

가천대학교 강의실 예약 및 시간표 충돌 검사 시스템입니다.  
`classfit`은 강의실의 기존 수업 시간표와 사용자가 생성한 실시간 예약을 함께 검사하여, 특정 날짜와 교시에 실제로 사용 가능한 강의실을 조회하고 예약할 수 있도록 만든 알고리즘 기반 웹 애플리케이션입니다.

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 프로젝트명 | classfit |
| 목적 | 강의실 예약 과정에서 발생하는 시간표 충돌과 중복 예약 문제 해결 |
| 주요 사용자 | 학생, 교수, 관리자 |
| 핵심 기능 | 강의실 추천, 예약 신청, 내 예약 조회, 실시간 현황판, 관리자 예약 관리 |
| 구현 방식 | Streamlit + React Custom Component + SQLite |
| 데이터 기준 | 강의실 목록, 기존 수업 차단 시간표, 사용자 계정, 실시간 예약, 예약 이력 |

---

## 2. 핵심 아이디어

기존 강의실 예약은 사용자가 직접 강의실 시간표를 확인하고 빈 시간을 찾아야 한다는 문제가 있습니다. `classfit`은 다음 두 종류의 데이터를 동시에 검사합니다.

1. `blocked_schedules`  
   정규 수업으로 이미 사용 중인 강의실 시간표

2. `reservations`  
   사용자가 실시간으로 생성한 강의실 예약 데이터

예약 신청 시에는 화면에서 한 번 후보 강의실을 계산하고, 실제 저장 직전에 SQLite 트랜잭션 안에서 다시 한 번 충돌 여부를 검사합니다. 따라서 여러 사용자가 동시에 같은 강의실을 예약하려고 해도 중복 예약을 방지할 수 있습니다.

---

## 3. 기술 스택

| 영역 | 기술 |
|---|---|
| 메인 앱 | Streamlit |
| UI | React Custom Component |
| 프론트엔드 빌드 | Vite |
| 데이터베이스 | SQLite |
| 데이터 처리 | Python, pandas |
| 아이콘 | lucide-react |
| 배포 대상 | Streamlit Cloud |

---

## 4. 시스템 구조

```text
classfit_streamlit_custom_component/
├── app.py
├── database.py
├── classfit.db
├── schema.sql
├── requirements.txt
├── README.md
├── data/
│   ├── rooms.csv
│   ├── blocked_schedules.csv
│   ├── users_sample.csv
│   ├── reservations_empty.csv
│   └── reservation_history_empty.csv
├── component/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.jsx
│   │   └── style.css
│   └── dist/
│       ├── index.html
│       └── assets/
└── .streamlit/
    └── config.toml
```

### 역할 분리

| 파일/폴더 | 역할 |
|---|---|
| `app.py` | Streamlit 실행 진입점, 세션 관리, React 컴포넌트 호출, 사용자 액션 처리 |
| `database.py` | SQLite 연결, 로그인, 예약 생성/취소, 충돌 검사, 이력 저장 |
| `classfit.db` | 실제 서비스 데이터 저장소 |
| `schema.sql` | 데이터베이스 테이블 구조 정의 |
| `component/src/main.jsx` | React 기반 사용자 화면 구현 |
| `component/src/style.css` | React UI 스타일 정의 |
| `component/dist/` | Streamlit에서 불러오는 React 빌드 결과물 |
| `data/` | 초기 데이터 CSV 파일 |

---

## 5. 주요 기능

### 5.1 로그인

학번, 교수 학수번호, 관리자 코드를 입력하여 로그인합니다. 비밀번호 입력은 사용하지 않습니다.

| 역할 | 로그인 식별자 예시 | 권한 |
|---|---|---|
| 학생 | `202430001` | 예약하기, 내 예약, 실시간 현황판 |
| 교수 | `08095006` | 예약하기, 내 예약, 실시간 현황판 |
| 관리자 | `admin` | 예약하기, 내 예약, 실시간 현황판, 전체 예약, 예약 이력, 예약 관리 |

지원되는 학생 로그인 범위는 다음과 같습니다.

```text
202130001 ~ 202139999
202230001 ~ 202239999
202330001 ~ 202339999
202430001 ~ 202439999
202530001 ~ 202539999
202630001 ~ 202639999
```

지원되는 교수 학수번호는 다음과 같습니다.

```text
08095006
13970001
14268001
14271001
14283001
14798002
```

새로고침 후에도 로그인 상태가 유지되도록 React 컴포넌트 내부의 `localStorage`에 마지막 로그인 식별자를 저장하고, Streamlit 세션이 초기화되면 자동으로 재로그인을 시도합니다.

---

### 5.2 강의실 조회 및 예약

사용자는 다음 조건을 입력하여 예약 가능한 강의실을 조회할 수 있습니다.

- 날짜
- 시작 교시
- 종료 교시
- 최소 수용 인원
- 건물
- 검색어
- 정렬 기준
- 이용 목적

조회 결과는 기존 수업 시간표와 실시간 예약 데이터를 모두 제외한 강의실만 보여줍니다. 실제 예약 저장 시에는 DB 트랜잭션 안에서 다시 충돌 검사를 수행합니다.

---

### 5.3 내 예약

학생과 교수는 본인이 생성한 예약만 조회하고 취소할 수 있습니다.  
타인의 예약 정보, 전체 예약 이력, 예약 관리 기능은 일반 사용자 화면에 노출되지 않습니다.

---

### 5.4 실시간 현황판

전체 강의실의 교시별 상태를 색상으로 확인할 수 있습니다.

| 상태 | 의미 |
|---|---|
| 가능 | 해당 교시에 사용 가능 |
| 기존 수업 | 정규 수업으로 사용 중 |
| 실시간 예약 | 사용자가 예약한 시간 |

현황판은 날짜와 건물 기준으로 필터링할 수 있습니다.

---

### 5.5 관리자 기능

관리자는 전체 예약 데이터와 예약 이력을 확인하고 관리할 수 있습니다.

| 기능 | 설명 |
|---|---|
| 전체 예약 | 모든 사용자의 실시간 예약 조회 |
| 예약 이력 | 예약 생성, 취소, 복구 기록 조회 |
| 전체 예약 초기화 | 실시간 예약만 초기화하고 이력은 유지 |
| 예약 및 이력 초기화 | 실시간 예약과 예약 이력을 모두 초기화 |

---

## 6. 적용된 자료구조 및 알고리즘

### 6.1 구간 겹침 검사

예약 충돌 검사의 핵심 조건은 다음과 같습니다.

```text
기존 시작 교시 < 새 예약 종료 교시
그리고
새 예약 시작 교시 < 기존 종료 교시
```

SQL 조건은 다음과 같은 방식으로 적용됩니다.

```sql
SELECT reservation_id
FROM reservations
WHERE room_id = ?
  AND date = ?
  AND start_period < ?
  AND ? < end_period;
```

이 방식은 예약 시간이 완전히 같은 경우뿐 아니라 일부만 겹치는 경우도 차단할 수 있습니다.

---

### 6.2 트랜잭션 기반 중복 예약 방지

예약 생성은 `BEGIN IMMEDIATE` 트랜잭션 안에서 처리됩니다.

처리 순서는 다음과 같습니다.

```text
1. 예약 요청 수신
2. SQLite BEGIN IMMEDIATE 실행
3. 기존 수업 시간표 충돌 검사
4. 실시간 예약 충돌 검사
5. 충돌이 없으면 reservations INSERT
6. reservation_history에 CREATE 기록 INSERT
7. COMMIT
```

이 구조를 사용하면 두 사용자가 동시에 같은 강의실을 예약하더라도 DB 저장 단계에서 한 명만 성공하게 됩니다.

---

### 6.3 추천 점수 기반 정렬

예약 가능한 강의실은 다음 요소를 반영하여 추천 점수를 계산합니다.

- 강의실 우선순위
- 접근성 점수
- 위치 점수
- 요청 인원 대비 남는 좌석 수

좌석 낭비가 지나치게 큰 강의실은 점수가 낮아지도록 처리하여, 조건에 맞으면서도 적절한 크기의 강의실이 먼저 보이도록 했습니다.

---

### 6.4 실행 취소 및 다시 실행

예약 생성과 취소 작업은 Streamlit 세션의 stack 구조로 관리됩니다.

| 구조 | 역할 |
|---|---|
| `undo_stack` | 직전에 수행한 예약 생성/취소 작업 저장 |
| `redo_stack` | 실행 취소한 작업을 다시 실행하기 위해 저장 |

이를 통해 사용자는 예약 생성 또는 취소 작업을 되돌릴 수 있습니다.

---

### 6.5 DB 인덱스 기반 탐색 최적화

자주 조회되는 컬럼에는 인덱스를 적용했습니다.

| 인덱스 | 목적 |
|---|---|
| `idx_blocked_room_day_period` | 특정 강의실, 요일, 교시의 기존 수업 빠른 조회 |
| `idx_reservations_room_date_period` | 특정 강의실, 날짜, 교시의 실시간 예약 충돌 검사 |
| `idx_reservations_user_id` | 사용자별 예약 조회 |
| `idx_history_user_id` | 사용자별 이력 조회 |
| `idx_rooms_capacity` | 수용 인원 기준 강의실 필터링 |

---

## 7. 데이터베이스 구조

### 7.1 `rooms`

강의실 기본 정보를 저장합니다.

| 컬럼 | 설명 |
|---|---|
| `room_id` | 강의실 고유 ID |
| `building` | 건물명 |
| `floor` | 층 |
| `room_number` | 호실 번호 |
| `room_name` | 화면 표시용 강의실명 |
| `capacity` | 수용 인원 |
| `room_type` | 강의실 유형 |
| `priority` | 추천 우선순위 |
| `equipment` | 기자재 정보 |

### 7.2 `blocked_schedules`

정규 수업으로 이미 사용 중인 강의실 시간을 저장합니다.

| 컬럼 | 설명 |
|---|---|
| `blocked_id` | 차단 시간 고유 ID |
| `course_id` | 수업 ID |
| `room_id` | 강의실 ID |
| `day` | 요일 |
| `period` | 교시 |
| `source_row` | 원본 데이터 행 추적 번호 |

### 7.3 `users`

사용자 계정을 저장합니다.

| 컬럼 | 설명 |
|---|---|
| `user_id` | 사용자 고유 ID |
| `user_name` | 사용자명 또는 로그인명 |
| `role` | `student`, `professor`, `admin` |
| `student_id` | 학번 또는 교수 학수번호 |
| `department` | 소속 |
| `email` | 이메일 |

### 7.4 `reservations`

현재 유효한 실시간 예약을 저장합니다.

| 컬럼 | 설명 |
|---|---|
| `reservation_id` | 예약 고유 ID |
| `room_id` | 강의실 ID |
| `date` | 예약 날짜 |
| `day` | 예약 요일 |
| `start_period` | 시작 교시 |
| `end_period` | 종료 교시 |
| `user_id` | 예약자 ID |
| `purpose` | 이용 목적 |
| `created_at` | 예약 생성 시각 |

### 7.5 `reservation_history`

예약 생성, 취소, 복구 기록을 저장합니다.

| 컬럼 | 설명 |
|---|---|
| `history_id` | 이력 고유 ID |
| `reservation_id` | 관련 예약 ID |
| `action` | `CREATE`, `CANCEL`, `RESTORE` |
| `room_id` | 강의실 ID |
| `date` | 예약 날짜 |
| `start_period` | 시작 교시 |
| `end_period` | 종료 교시 |
| `user_id` | 작업 사용자 ID |
| `memo` | 작업 설명 |
| `action_at` | 작업 시각 |

---

## 8. 초기 데이터 상태

초기 DB는 다음 상태로 구성되어 있습니다.

| 테이블 | 개수 |
|---|---:|
| `rooms` | 40 |
| `blocked_schedules` | 896 |
| `users` | 60,001 |
| `reservations` | 0 |
| `reservation_history` | 0 |

---

## 9. 실행 방법

### 9.1 Python 패키지 설치

```bash
pip install -r requirements.txt
```

### 9.2 앱 실행

```bash
streamlit run app.py
```

실행 후 브라우저에서 Streamlit 앱이 열립니다.

---

## 10. React 컴포넌트 수정 방법

화면 UI는 `component/src/main.jsx`와 `component/src/style.css`에서 수정합니다.  
수정 후에는 반드시 React 컴포넌트를 다시 빌드해야 합니다.

```bash
cd component
npm install
npm run build
cd ..
streamlit run app.py
```

Streamlit Cloud에 배포할 때는 `component/dist/` 폴더가 반드시 포함되어 있어야 합니다.

---

## 11. Streamlit Cloud 배포 체크리스트

배포 시 다음 파일과 폴더가 모두 업로드되어야 합니다.

```text
app.py
database.py
classfit.db
schema.sql
requirements.txt
README.md
data/
component/dist/
component/package.json
component/vite.config.js
.streamlit/config.toml
```

특히 `component/dist/assets/` 안의 JavaScript와 CSS 파일이 빠지면 React Custom Component가 로드되지 않습니다.

---

## 12. 문제 해결

### 12.1 React 화면이 뜨지 않는 경우

다음 파일이 존재하는지 확인합니다.

```text
component/dist/index.html
component/dist/assets/*.js
component/dist/assets/*.css
```

없다면 아래 명령어를 실행합니다.

```bash
cd component
npm install
npm run build
```

### 12.2 Streamlit Cloud에서 컴포넌트 로딩 오류가 나는 경우

다음 순서로 해결합니다.

```text
1. ZIP 전체를 다시 업로드한다.
2. component/dist 폴더가 포함되어 있는지 확인한다.
3. Manage app → Reboot app을 실행한다.
```

### 12.3 새로고침 후 로그인이 풀리는 경우

브라우저의 localStorage 사용이 막혀 있거나, 이전 캐시가 남아 있을 수 있습니다.

```text
1. 브라우저 캐시를 새로고침한다.
2. Streamlit 앱을 Reboot한다.
3. 로그아웃 후 다시 로그인한다.
```

---

## 13. 보안 및 운영상 주의점

현재 로그인은 과제 시연과 프로토타입 검증을 위해 식별자 기반으로 단순화되어 있습니다. 실제 운영 환경에서는 다음 보완이 필요합니다.

- 학교 통합 로그인 또는 OAuth 연동
- 관리자 계정 인증 강화
- 외부 DB 사용
- 서버 단위 권한 검증 강화
- 예약 변경/삭제 로그 장기 보관
- 사용자 입력값 검증 및 감사 로그 강화

또한 Streamlit Cloud에서 SQLite를 사용할 경우 앱 재배포 또는 파일 초기화 방식에 따라 DB 상태가 바뀔 수 있습니다. 장기 운영 목적이라면 PostgreSQL, MySQL, Supabase 같은 외부 DB를 사용하는 것이 적절합니다.

---

## 14. 발표 핵심 요약

`classfit`은 단순한 CRUD 예약 시스템이 아니라, 기존 수업 시간표와 실시간 예약 데이터를 함께 검사하는 알고리즘 기반 강의실 예약 시스템입니다.  
구간 겹침 검사, 트랜잭션 기반 중복 예약 방지, 추천 점수 정렬, stack 기반 실행 취소/다시 실행, DB 인덱스 최적화를 적용하여 실제 서비스에 가까운 예약 흐름을 구현했습니다.


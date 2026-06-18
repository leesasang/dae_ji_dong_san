# ClassFit 최종본

**ClassFit**은 가천대학교 강의실 예약 상황을 확인하고, 조건에 맞는 빈 강의실을 추천하며, 예약 생성/취소 이력을 DB에 남기는 강의실 예약·추천 서비스 프로토타입이다.

이번 최종본은 기존 React + TypeScript 프론트엔드의 화면 흐름과 기능을 **Streamlit + SQLite** 구조로 재구현한 버전이다.
React 버전의 화면 컨셉인 파란색 상단바, 카드형 강의실 목록, 역할별 포털, 관리자 대시보드, 예약 이력 관리 흐름을 Streamlit UI로 옮겼다.

---

## 1. 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

실행 후 브라우저에서 Streamlit 주소로 접속한다.

---

## 2. 기본 로그인 계정

| 역할 | 아이디 | 비밀번호 | 설명 |
|---|---|---|---|
| 관리자 | admin | admin123 | 관리자 대시보드, 강의실 CRUD, 통계, DB 초기화 |
| 학생 | user1 | 1234 | 강의실 조회/예약, 내 예약 확인 |
| 학생 | user2 | 1234 | 강의실 조회/예약, 내 예약 확인 |
| 학생 자동 생성 | 9자리 숫자 | 생략 가능 | 예: 202400001 입력 시 학생 계정 자동 생성 |
| 교수 자동 생성 | 7자리 숫자 | 생략 가능 | 예: 1234567 입력 시 교수 계정 자동 생성 |

React 원본의 로그인 규칙을 반영하여 `admin`, 9자리 학번, 7자리 사번 로그인을 지원한다.
DB에는 사용자가 `users` 테이블에 저장되며, 예약은 `user_id`를 기준으로 연결된다.

---

## 3. 프로젝트 구조

```text
classfit_streamlit_final/
├── app.py
├── database.py
├── classfit.db
├── schema.sql
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
└── data/
    ├── rooms.csv
    ├── blocked_schedules.csv
    ├── users_sample.csv
    ├── reservations_empty.csv
    └── reservation_history_empty.csv
```

---

## 4. DB 구조

### 4.1 rooms

강의실 고정 정보를 저장한다.

주요 컬럼:

- `room_id`: 강의실 고유 ID
- `building`: 건물명
- `floor`: 층
- `room_number`: 강의실 번호
- `room_name`: 사용자 화면 출력용 강의실명
- `capacity`: 수용 인원
- `room_type`: 강의실 유형
- `priority`: 기본 추천 우선순위
- `equipment`: 기자재 정보

### 4.2 blocked_schedules

기존 정규 수업 때문에 예약할 수 없는 시간표를 저장한다.

주요 컬럼:

- `course_id`: 학수번호
- `room_id`: 강의실 ID
- `day`: 요일
- `period`: 교시
- `source_row`: 원본 엑셀 행 번호 추적용 컬럼

### 4.3 users

사용자 계정을 저장한다.

주요 컬럼:

- `user_id`: 사용자 고유 번호
- `user_name`: 로그인 ID 또는 이름
- `password_hash`: 비밀번호 해시값
- `role`: student / professor / admin
- `student_id`: 학번 또는 사번
- `department`: 소속
- `email`: 이메일

### 4.4 reservations

현재 살아 있는 실시간 예약을 저장한다.

주요 컬럼:

- `reservation_id`: 예약 ID
- `room_id`: 강의실 ID
- `date`: 예약 날짜
- `day`: 요일
- `start_period`: 시작 교시
- `end_period`: 종료 교시
- `user_id`: 예약자 ID
- `purpose`: 이용 목적

기존의 `user_name` 저장 방식은 제거하고, `users.user_id`를 참조하는 방식으로 수정했다.

### 4.5 reservation_history

예약 생성, 취소, 복구 내역을 저장한다.

주요 컬럼:

- `history_id`: 이력 ID
- `reservation_id`: 관련 예약 ID
- `action`: CREATE / CANCEL / RESTORE
- `room_id`: 강의실 ID
- `date`: 예약 날짜
- `start_period`, `end_period`: 예약 교시
- `user_id`: 작업 사용자
- `memo`: 이력 설명

예약을 취소하더라도 `reservation_history`에는 기록이 남는다.

---

## 5. 주요 기능

### 5.1 학생 기능

- 로그인
- 강의실 조건 검색
- 강의실 상세 정보 확인
- 예약 신청
- 기존 수업 시간표와 충돌 검사
- 실시간 예약과 충돌 검사
- BFS 기반 대체 강의실 추천
- 우선순위 큐 기반 Top-K 강의실 추천
- 내 예약 조회
- 예약 취소
- 예약 이력 확인
- Undo / Redo 작업 이력 관리

### 5.2 교수 기능

- 유휴 강의실 연속 공강 조회
- 강의실 조회 및 예약
- 정규 주간 시간표 조회
- 내 예약 내역 확인

### 5.3 관리자 기능

- 실시간 가용 현황판
- 강의실 × 교시 상태 확인
- 강의실 데이터 추가/수정/삭제
- 강의실 이용 통계
- 건물별 예약 통계
- DB 마스터 데이터 초기화
- 실시간 예약 데이터 초기화
- 전체 예약 이력 조회

---

## 6. 사용한 자료구조 및 알고리즘

### 6.1 관계형 테이블 구조

`rooms`, `blocked_schedules`, `users`, `reservations`, `reservation_history`를 분리하여 데이터 중복을 줄이고 무결성을 높였다.
예약 테이블은 `user_id`를 통해 사용자 테이블과 연결된다.

### 6.2 B-Tree 기반 인덱스

SQLite 인덱스를 사용하여 강의실, 날짜, 교시 기준 조회 성능을 개선했다.
주로 충돌 검사와 예약 조회에서 사용된다.

### 6.3 구간 겹침 검사 알고리즘

예약 충돌 조건은 다음과 같다.

```text
기존 시작 교시 < 새 종료 교시
그리고
새 시작 교시 < 기존 종료 교시
```

이 조건을 만족하면 두 예약 시간은 겹치는 것으로 판단한다.

### 6.4 우선순위 큐

강의실 추천에서 `heapq`를 사용하여 추천 점수가 높은 강의실 Top-K를 추출한다.
추천 점수에는 수용 인원, 위치 점수, 접근성 점수, 기본 우선순위, 정원 낭비 정도가 반영된다.

### 6.5 BFS 대체 강의실 추천

예약 충돌이 발생하면 같은 건물과 같은 층의 인접 강의실을 그래프로 구성하고 BFS로 가까운 대체 강의실을 탐색한다.

### 6.6 퀵 정렬

강의실 검색 결과를 `room_id`, `capacity`, `priority` 기준으로 정렬할 때 퀵 정렬 방식을 적용했다.
React 원본의 `quick_sort.ts` 기능을 Streamlit 앱 내부 함수로 재구현했다.

### 6.7 Sliding Window

특정 날짜에 연속으로 비어 있는 교시를 찾기 위해 Sliding Window 방식으로 강의실별 최대 연속 공강을 계산한다.
교수 포털의 유휴 강의실 조회와 관리자 현황판에서 사용된다.

### 6.8 Stack 기반 Undo/Redo

Streamlit `session_state`를 이용해 Undo Stack과 Redo Stack을 관리한다.
예약 생성, 예약 취소 작업을 실행 취소하거나 다시 실행할 수 있다.

---

## 7. 데이터 흐름

```text
원본 엑셀 시간표
→ CSV 전처리
→ rooms.csv / blocked_schedules.csv
→ SQLite classfit.db 적재
→ Streamlit 앱에서 실시간 예약 생성
→ reservations 테이블 저장
→ reservation_history 테이블에 작업 이력 저장
```

---

## 8. Streamlit Cloud 배포 방법

1. 이 폴더 전체를 GitHub 저장소에 업로드한다.
2. Streamlit Community Cloud에 접속한다.
3. `New app`을 선택한다.
4. Repository, Branch를 선택한다.
5. Main file path를 `app.py`로 지정한다.
6. Deploy를 실행한다.

주의: SQLite는 Streamlit Cloud에서 시연용으로는 사용 가능하지만, 앱 재시작이나 재배포 시 저장 데이터가 초기화될 수 있다.
실제 운영 서비스로 확장하려면 PostgreSQL, Supabase 같은 외부 DB로 이전하는 것이 적절하다.

---

## 9. 최종 설명 문장

ClassFit은 정규 수업 시간표와 실시간 예약 데이터를 함께 고려하여 강의실의 사용 가능 여부를 판단하고, 조건에 맞는 강의실을 추천하는 강의실 예약 서비스 프로토타입이다. 본 프로젝트는 SQLite 기반 DB, Streamlit 웹 UI, 구간 충돌 검사, BFS, 우선순위 큐, 퀵 정렬, Sliding Window, Stack 기반 Undo/Redo 기능을 결합하여 실생활 문제를 알고리즘과 자료구조로 해결하는 것을 목표로 한다.


## v4.1 수정 사항

- 로그인 후 상단 헤더에서 `login_id` 키가 없어 발생하던 `KeyError`를 수정했습니다.
- 세션에 기존 사용자 정보가 남아 있거나 DB 조회 결과에 `login_id`가 없어도 `user_name`/`student_id`로 안전하게 대체합니다.
- `login_with_identifier()` 함수가 로그인 성공 시 `login_id`를 명시적으로 세션 사용자 정보에 포함하도록 수정했습니다.
- 학번/교수 학수번호 단일 로그인, SQLite 실시간 예약 저장, `BEGIN IMMEDIATE` 트랜잭션 기반 중복 예약 방지는 그대로 유지됩니다.

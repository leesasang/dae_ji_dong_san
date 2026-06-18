# ClassFit 최종본 v3 - 학번/학수번호 단일 로그인

**ClassFit**은 가천대학교 강의실의 정규 수업 시간표와 실시간 예약 데이터를 함께 확인하여, 강의실 사용 가능 여부를 판단하고 조건에 맞는 강의실을 추천하는 강의실 예약·추천 서비스 프로토타입이다.

이번 버전은 기존 React + TypeScript 프론트엔드의 화면 구성과 기능 흐름을 **Streamlit + SQLite** 구조로 재구현한 최종 버전이며, 로그인 방식은 비밀번호 없이 **학생 학번 또는 교수 학수번호만 입력**하는 방식으로 단순화했다.

---

## 1. 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 2. 로그인 방식

비밀번호는 입력하지 않는다. 로그인 화면에는 오직 **학번 또는 교수 학수번호**만 입력한다.

### 학생 로그인 ID

아래 범위에 해당하는 학번만 학생 계정으로 로그인할 수 있다.

| 입학년도 | 로그인 가능 학번 범위 |
|---|---|
| 2021 | 202130001 ~ 202139999 |
| 2022 | 202230001 ~ 202239999 |
| 2023 | 202330001 ~ 202339999 |
| 2024 | 202430001 ~ 202439999 |
| 2025 | 202530001 ~ 202539999 |
| 2026 | 202630001 ~ 202639999 |

### 교수 로그인 ID

아래 학수번호만 교수 계정으로 로그인할 수 있다.

```text
08095006
13970001
14268001
14271001
14283001
14798002
```

### users 테이블 상태

| 역할 | 개수 |
|---|---:|
| admin | 1 |
| student | 59,994 |
| professor | 6 |

현재 로그인 화면에서는 학생 학번과 교수 학수번호만 허용한다. `admin` 계정은 DB 내부 관리용으로 남겨두었지만, 일반 로그인 화면에서는 사용하지 않는다.

---

## 3. 프로젝트 구조

```text
classfit_streamlit_final_v3_id_only/
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

로그인 가능한 사용자 식별자를 저장한다.

주요 컬럼:

- `user_id`: 사용자 고유 번호
- `user_name`: 로그인 ID. 학생은 학번, 교수는 학수번호
- `role`: student / professor / admin
- `student_id`: 학생 학번
- `department`: 소속
- `email`: 이메일

비밀번호 입력은 사용하지 않는다. 학생과 교수는 `users_sample.csv`에 등록된 `user_name` 값만으로 로그인한다.

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

기존의 `user_name` 직접 저장 방식은 사용하지 않고, `users.user_id`를 참조하는 외래키 구조를 사용한다.

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

## 5. 실시간 DB 연동 및 중복 예약 방지

이 프로젝트는 단순 화면 상태가 아니라 SQLite DB의 `reservations` 테이블을 기준으로 예약 데이터를 저장한다.

예약 신청 과정은 다음 순서로 동작한다.

```text
1. 사용자가 학번 또는 교수 학수번호로 로그인
2. 예약할 강의실, 날짜, 교시 입력
3. DB 트랜잭션 BEGIN IMMEDIATE 시작
4. 기존 정규 수업 blocked_schedules 충돌 검사
5. 실시간 예약 reservations 충돌 검사
6. 충돌이 없을 때만 reservations에 INSERT
7. reservation_history에 CREATE 기록
8. 화면 즉시 갱신
```

중복 예약 방지를 위해 예약 생성 함수 `add_reservation()` 내부에서 최종 충돌 검사를 다시 수행한다. 따라서 화면에서 예약 가능으로 보였더라도, 다른 사용자가 같은 시간에 먼저 예약했다면 DB 저장 직전에 다시 막힌다.

사용한 충돌 조건은 다음과 같다.

```text
기존 시작 교시 < 새 종료 교시
그리고
새 시작 교시 < 기존 종료 교시
```

또한 SQLite의 `BEGIN IMMEDIATE` 트랜잭션과 WAL 모드를 사용하여 여러 사용자가 동시에 예약 버튼을 눌러도 같은 강의실·같은 시간대의 중복 예약이 발생하지 않도록 구성했다.

---

## 6. 주요 기능

### 6.1 학생 기능

- 학번 기반 로그인
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

### 6.2 교수 기능

- 교수 학수번호 기반 로그인
- 유휴 강의실 연속 공강 조회
- 강의실 조회 및 예약
- 정규 주간 시간표 조회
- 내 예약 내역 확인

### 6.3 관리자 기능

관리자 기능은 코드와 DB 구조에는 포함되어 있으나, 현재 로그인 화면은 학생 학번과 교수 학수번호 입력만 허용하도록 제한했다.

---

## 7. 사용한 자료구조 및 알고리즘

### 7.1 관계형 테이블 구조

`rooms`, `blocked_schedules`, `users`, `reservations`, `reservation_history`를 분리하여 데이터 중복을 줄이고 무결성을 높였다. 예약 테이블은 `user_id`를 통해 사용자 테이블과 연결된다.

### 7.2 B-Tree 기반 인덱스

SQLite 인덱스를 사용하여 강의실, 날짜, 교시 기준 조회 성능을 개선했다. 특히 충돌 검사와 예약 조회에서 사용된다.

### 7.3 구간 겹침 검사 알고리즘

예약 충돌 조건은 다음과 같다.

```text
기존 시작 교시 < 새 종료 교시
그리고
새 시작 교시 < 기존 종료 교시
```

이 조건을 만족하면 두 예약 시간은 겹치는 것으로 판단한다.

### 7.4 우선순위 큐

강의실 추천에서 `heapq`를 사용하여 추천 점수가 높은 강의실 Top-K를 추출한다. 추천 점수에는 수용 인원, 위치 점수, 접근성 점수, 기본 우선순위, 정원 낭비 정도가 반영된다.

### 7.5 BFS 대체 강의실 추천

예약 충돌이 발생하면 같은 건물과 같은 층의 인접 강의실을 그래프로 구성하고 BFS로 가까운 대체 강의실을 탐색한다.

### 7.6 퀵 정렬

강의실 검색 결과를 `room_id`, `capacity`, `priority` 기준으로 정렬할 때 퀵 정렬 방식을 적용했다.

### 7.7 Sliding Window

특정 날짜에 연속으로 비어 있는 교시를 찾기 위해 Sliding Window 방식으로 강의실별 최대 연속 공강을 계산한다.

### 7.8 Stack 기반 Undo/Redo

Streamlit `session_state`를 이용해 Undo Stack과 Redo Stack을 관리한다. 예약 생성, 예약 취소 작업을 실행 취소하거나 다시 실행할 수 있다.

---

## 8. 데이터 흐름

```text
원본 엑셀 시간표
→ CSV 전처리
→ rooms.csv / blocked_schedules.csv / users_sample.csv
→ SQLite classfit.db 적재
→ Streamlit 앱에서 실시간 예약 생성
→ reservations 테이블 저장
→ reservation_history 테이블에 작업 이력 저장
```

---

## 9. 배포 방법

1. 이 폴더 전체를 GitHub 저장소에 업로드한다.
2. Streamlit Community Cloud에서 새 앱을 생성한다.
3. Repository와 Branch를 선택한다.
4. Main file path를 `app.py`로 지정한다.
5. Deploy를 실행한다.

주의: SQLite는 시연용 프로토타입에는 적합하지만, Streamlit Cloud 환경에서는 앱 재시작이나 재배포 시 저장 데이터가 초기화될 수 있다. 실제 운영 서비스로 확장하려면 PostgreSQL, Supabase 같은 외부 DB로 이전하는 것이 적절하다.

---

## 10. 최종 설명 문장

ClassFit은 정규 수업 시간표와 실시간 예약 데이터를 함께 고려하여 강의실의 사용 가능 여부를 판단하고, 조건에 맞는 강의실을 추천하는 강의실 예약 서비스 프로토타입이다. 본 프로젝트는 SQLite 기반 DB, Streamlit 웹 UI, 학번/학수번호 기반 로그인, 구간 충돌 검사, BFS, 우선순위 큐, 퀵 정렬, Sliding Window, Stack 기반 Undo/Redo 기능을 결합하여 실생활 문제를 알고리즘과 자료구조로 해결하는 것을 목표로 한다.

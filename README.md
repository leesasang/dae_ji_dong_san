# ClassFit Streamlit 최종본 v4

ClassFit은 가천대학교 강의실의 정규 수업 시간표와 실시간 예약 정보를 함께 반영하여 빈 강의실을 조회하고 예약하는 서비스 프로토타입이다.

이번 v4는 사용자가 제공한 React + TypeScript 프론트엔드의 디자인을 Streamlit에 다시 맞춰 옮긴 버전이다. 기존 Streamlit 사이드바 중심 UI를 제거하고, React 원본과 같이 파란색 상단 헤더, 흰색 카드형 레이아웃, 상단 탭 메뉴, 로그인 카드 구조를 사용하도록 수정했다.

---

## 1. 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 2. 로그인 방식

비밀번호 입력은 사용하지 않는다. 로그인 화면에는 학번 또는 교수 학수번호만 입력한다.

### 학생 로그인

다음 범위의 학번만 로그인 가능하다.

```text
202130001 ~ 202139999
202230001 ~ 202239999
202330001 ~ 202339999
202430001 ~ 202439999
202530001 ~ 202539999
202630001 ~ 202639999
```

### 교수 로그인

다음 학수번호만 로그인 가능하다.

```text
08095006
13970001
14268001
14271001
14283001
14798002
```

### 관리자 로그인

최종 시연 흐름에서는 관리자 직접 로그인은 제외했다. 관리자 기능은 DB 구조와 앱 내부 기능으로는 유지되어 있으나, 로그인 입력은 학생 학번과 교수 학수번호만 받도록 설계했다.

---

## 3. 프로젝트 구조

```text
classfit_streamlit_final_v4_react_design/
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

### rooms

강의실 고정 정보를 저장한다.

주요 컬럼은 `room_id`, `building`, `floor`, `room_number`, `capacity`, `room_type`, `location_score`, `accessibility_score`, `priority`이다.

### blocked_schedules

정규 수업 때문에 예약할 수 없는 강의실 시간표를 저장한다. 엑셀 시간표를 전처리해 `room_id`, `day`, `period`, `course_id` 단위로 분리했다.

### users

학생 학번과 교수 학수번호 로그인 정보를 저장한다. 예약자는 `user_id`로 관리된다.

### reservations

현재 살아 있는 실시간 예약 정보를 저장한다. 예약자명 문자열 대신 `user_id`를 사용한다.

### reservation_history

예약 생성, 취소, 복구 내역을 저장한다. 예약을 취소해도 이력은 남는다.

---

## 5. 실시간 DB 연동과 중복 예약 방지

예약 신청은 `database.py`의 `add_reservation()`에서 처리된다.

처리 흐름은 다음과 같다.

```text
1. BEGIN IMMEDIATE 트랜잭션 시작
2. rooms 테이블에서 강의실 존재 여부 확인
3. blocked_schedules 테이블에서 정규 수업 충돌 검사
4. reservations 테이블에서 실시간 예약 충돌 검사
5. 충돌이 없으면 reservations INSERT
6. reservation_history에 CREATE 기록
7. commit
```

따라서 두 사용자가 같은 시간에 같은 강의실을 동시에 예약하려고 해도, DB 트랜잭션 안에서 한 번 더 충돌 검사를 수행하므로 중복 예약이 방지된다.

---

## 6. 주요 기능

### 학생 기능

- 학번 로그인
- 조건별 강의실 검색
- 강의실 예약
- 기존 수업 충돌 검사
- 실시간 예약 충돌 검사
- BFS 기반 대체 강의실 추천
- 내 예약 조회
- 예약 취소
- 예약 이력 확인

### 교수 기능

- 교수 학수번호 로그인
- 유휴 강의실 연속 공강 조회
- 강의실 조회 및 예약
- 정규 주간 시간표 조회
- 내 예약 내역 확인

### 관리자/DB 기능

- 강의실 현황판
- 강의실 데이터 관리
- 예약 통계
- 예약 이력 조회
- CSV 기반 DB 초기화

---

## 7. 사용한 자료구조 및 알고리즘

### 관계형 테이블 구조

`rooms`, `blocked_schedules`, `users`, `reservations`, `reservation_history`를 분리하여 데이터 중복을 줄이고 예약 데이터의 무결성을 높였다.

### B-Tree 기반 인덱스

SQLite 인덱스를 사용하여 강의실, 날짜, 교시 기준 조회 속도를 높였다.

### 구간 겹침 검사 알고리즘

예약 충돌 조건은 다음과 같다.

```text
기존 시작 교시 < 새 종료 교시
그리고
새 시작 교시 < 기존 종료 교시
```

이 조건을 만족하면 두 예약은 겹치는 것으로 판단한다.

### 우선순위 큐

강의실 추천에서 `heapq`를 사용하여 추천 점수가 높은 강의실을 Top-K로 추출한다.

### BFS 대체 강의실 추천

예약 충돌이 발생하면 같은 건물과 같은 층의 인접 강의실을 그래프로 보고 BFS로 대체 강의실을 탐색한다.

### 퀵 정렬

강의실 검색 결과를 `room_id`, `capacity`, `priority` 기준으로 정렬할 때 퀵 정렬 방식을 적용했다.

### Sliding Window

특정 날짜에 연속으로 비어 있는 교시를 찾기 위해 Sliding Window 방식으로 강의실별 최대 연속 공강을 계산한다.

### Stack 기반 Undo/Redo

예약 생성/취소 작업을 Stack 구조로 관리하여 실행 취소와 다시 실행 흐름을 구현했다.

---

## 8. v4 디자인 수정 사항

- 기존 Streamlit 사이드바 중심 UI 제거
- React 원본처럼 파란색 상단 헤더 적용
- 역할별 메뉴를 상단 탭형 메뉴로 변경
- 로그인 화면을 React LoginGate 구조에 맞춰 카드형으로 재구성
- 전체 배경을 `#F8FAFC`, 카드 배경을 흰색, 메인 컬러를 `#005BAC`으로 통일
- 다크모드 강제 적용 제거
- Streamlit 기본 위젯 색상도 React 디자인 톤에 맞게 CSS 재정리

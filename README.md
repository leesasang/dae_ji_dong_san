# ClassFit Streamlit Final v4.3

React/Vite 프론트 디자인을 Streamlit + SQLite 구조로 재구현한 ClassFit 최종 수정본입니다.

## v4.3 수정 사항

- 로그인 화면 UI 깨짐 수정
- HTML 카드와 Streamlit 입력창이 겹치던 구조 제거
- `margin-top:-42vh` 방식 제거
- 로그인 카드 헤더와 입력 폼을 순차 렌더링 방식으로 수정
- 비밀번호 입력 제거 유지
- 학번 또는 교수 학수번호 단일 로그인 유지
- SQLite DB 실시간 연동 유지
- `BEGIN IMMEDIATE` 트랜잭션 기반 중복 예약 방지 유지
- `reservation_history` 예약 이력 기록 유지

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 로그인 방식

비밀번호는 입력하지 않습니다. 로그인 화면에는 학번 또는 교수 학수번호만 입력합니다.

### 학생 학번

- 202130001 ~ 202139999
- 202230001 ~ 202239999
- 202330001 ~ 202339999
- 202430001 ~ 202439999
- 202530001 ~ 202539999
- 202630001 ~ 202639999

### 교수 학수번호

- 08095006
- 13970001
- 14268001
- 14271001
- 14283001
- 14798002

## DB 구조

- rooms
- blocked_schedules
- users
- reservations
- reservation_history

예약 정보는 `reservations.user_id`를 기준으로 사용자와 연결됩니다.
예약 생성/취소 내역은 `reservation_history`에 기록됩니다.

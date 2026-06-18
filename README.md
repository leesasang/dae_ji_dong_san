# ClassFit Streamlit Custom Component v1.2

React 화면을 Streamlit Custom Component로 삽입하고, 예약/취소/이력 저장은 Python + SQLite에서 처리하는 버전입니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## v1.2 수정 사항

- Streamlit Cloud에서 이전 실패한 컴포넌트 경로가 캐시될 수 있어 컴포넌트 이름을 `classfit_react_ui_v12`로 변경했습니다.
- `component/dist/index.html`, `component/dist/assets/*.js`, `component/dist/assets/*.css` 존재 여부를 실행 전에 검사합니다.
- React 컴포넌트는 `withStreamlitConnection` 래퍼를 제거하고 `Streamlit.setComponentReady()`를 직접 호출하는 방식으로 변경했습니다.
- Vite build 경로는 `base: "./"`로 고정되어 Streamlit iframe 내부에서도 JS/CSS를 상대 경로로 불러옵니다.

## 배포 시 주의

Streamlit Cloud에 올릴 때는 반드시 아래 폴더를 포함해야 합니다.

```text
component/dist/index.html
component/dist/assets/*.js
component/dist/assets/*.css
```

GitHub에 올릴 때 `.gitignore`에 `dist`가 제외되어 있으면 화면이 로드되지 않습니다. 이 프로젝트는 이미 build 결과물을 포함하고 있으므로 ZIP 전체를 업로드하는 방식이 가장 안전합니다.

## 구조

```text
app.py                    Streamlit 실행 파일
component/dist/            React build 결과물
component/src/             React 원본 코드
database.py                SQLite DB 함수
classfit.db                실제 DB
schema.sql                 DB 스키마
requirements.txt           Python 패키지
```

## 로그인 예시

- 학생: `202430001`
- 학생: `202630001`
- 교수: `08095006`

## 기능

- 학번/학수번호 단일 로그인
- 강의실 추천 및 예약
- 기존 시간표와 실시간 예약 충돌 검사
- SQLite 트랜잭션 기반 중복 예약 방지
- 내 예약 조회
- 전체 예약 조회
- 예약 이력 조회
- Undo / Redo

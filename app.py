"""
ClassFit Final Streamlit App
React/Vite 프론트엔드 디자인과 기능 흐름을 Streamlit + SQLite 구조로 재구현한 최종 버전.
"""
from __future__ import annotations

import heapq
from datetime import date as DateType, datetime
from typing import Any, Iterable

import pandas as pd
import streamlit as st

import database as db

PERIODS = list(range(1, 13))
END_PERIODS = list(range(2, 14))
KOREAN_DAYS = ["월", "화", "수", "목", "금", "토", "일"]
ROLE_LABELS = {"student": "학생", "professor": "교수", "admin": "관리자", "user": "학생"}
EQUIPMENT_OPTIONS = ["projector", "computer", "whiteboard"]

st.set_page_config(
    page_title="ClassFit | Gachon University Reservation System",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------
# Design system: React UI theme port
# -------------------------

def apply_theme(theme: str) -> None:
    dark = theme == "다크 모드"
    palette = {
        "bg": "#020617" if dark else "#F8FAFC",
        "panel": "#0F172A" if dark else "#FFFFFF",
        "panel2": "#111827" if dark else "#F1F5F9",
        "panel3": "#1E293B" if dark else "#E2E8F0",
        "border": "#334155" if dark else "#E2E8F0",
        "text": "#E5E7EB" if dark else "#1E293B",
        "muted": "#94A3B8" if dark else "#64748B",
        "primary": "#005BAC",
        "primary2": "#60A5FA" if dark else "#2563EB",
        "success_bg": "#052E16" if dark else "#F0FDF4",
        "success_text": "#BBF7D0" if dark else "#166534",
        "danger_bg": "#450A0A" if dark else "#FEF2F2",
        "danger_text": "#FECACA" if dark else "#991B1B",
        "info_bg": "#0C4A6E" if dark else "#EFF6FF",
        "info_text": "#BAE6FD" if dark else "#1D4ED8",
    }
    css = f"""
    <style>
    :root {{
        --cf-bg:{palette['bg']}; --cf-panel:{palette['panel']}; --cf-panel2:{palette['panel2']};
        --cf-panel3:{palette['panel3']}; --cf-border:{palette['border']}; --cf-text:{palette['text']};
        --cf-muted:{palette['muted']}; --cf-primary:{palette['primary']}; --cf-primary2:{palette['primary2']};
        --cf-success-bg:{palette['success_bg']}; --cf-success-text:{palette['success_text']};
        --cf-danger-bg:{palette['danger_bg']}; --cf-danger-text:{palette['danger_text']};
        --cf-info-bg:{palette['info_bg']}; --cf-info-text:{palette['info_text']};
    }}
    html, body, .stApp, [data-testid="stAppViewContainer"] {{ background: var(--cf-bg) !important; color: var(--cf-text) !important; }}
    .main .block-container {{ max-width: 1480px; padding-top: 1rem; padding-bottom: 3rem; }}
    [data-testid="stSidebar"] {{ background: var(--cf-panel) !important; border-right:1px solid var(--cf-border); }}
    [data-testid="stSidebar"] * {{ color: var(--cf-text) !important; }}
    h1,h2,h3,h4,h5,h6,p,span,div,label,[data-testid="stMarkdownContainer"] {{ color: var(--cf-text) !important; }}
    small, .caption, [data-testid="stCaptionContainer"], .muted {{ color: var(--cf-muted) !important; }}
    .topbar {{ background:#005BAC; color:white !important; border-radius:18px; padding:18px 22px; margin-bottom:18px;
        box-shadow:0 14px 30px rgba(0,91,172,.22); display:flex; align-items:center; justify-content:space-between; gap:16px; }}
    .topbar h1 {{ color:white !important; margin:0; font-size:30px; letter-spacing:-.02em; }}
    .topbar p {{ color:#DBEAFE !important; margin:4px 0 0 0; font-size:14px; }}
    .brand-chip {{ background:rgba(255,255,255,.14); color:white !important; border:1px solid rgba(255,255,255,.22); padding:7px 11px; border-radius:999px; font-size:12px; font-weight:800; }}
    .card {{ background:var(--cf-panel); border:1px solid var(--cf-border); border-radius:18px; padding:18px; box-shadow:0 8px 22px rgba(0,0,0,.12); margin-bottom:14px; }}
    .soft-card {{ background:var(--cf-panel2); border:1px solid var(--cf-border); border-radius:16px; padding:15px; margin-bottom:12px; }}
    .metric-card {{ background:var(--cf-panel); border:1px solid var(--cf-border); border-radius:18px; padding:17px; box-shadow:0 8px 22px rgba(0,0,0,.10); }}
    .metric-label {{ color:var(--cf-muted) !important; font-size:13px; font-weight:700; }}
    .metric-value {{ color:var(--cf-text) !important; font-size:28px; font-weight:900; margin-top:4px; }}
    .section-title {{ display:flex; align-items:center; gap:9px; font-size:23px; font-weight:900; margin:8px 0 3px; }}
    .section-desc {{ color:var(--cf-muted) !important; margin-bottom:16px; font-size:14px; }}
    .badge {{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:900; margin:2px; border:1px solid var(--cf-border); }}
    .badge-ok {{ background:var(--cf-success-bg); color:var(--cf-success-text) !important; }}
    .badge-bad {{ background:var(--cf-danger-bg); color:var(--cf-danger-text) !important; }}
    .badge-info {{ background:var(--cf-info-bg); color:var(--cf-info-text) !important; }}
    .room-card {{ border:1px solid var(--cf-border); background:var(--cf-panel); border-radius:16px; padding:14px; min-height:160px; margin-bottom:10px; }}
    .room-title {{ font-weight:900; font-size:18px; color:var(--cf-text) !important; }}
    .room-sub {{ color:var(--cf-muted) !important; font-size:13px; margin-top:2px; }}
    .mini {{ color:var(--cf-muted) !important; font-size:12px; }}
    .status-grid {{ font-size:12px; line-height:1.15; }}
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div,
    [data-testid="stDateInput"] input, [data-testid="stNumberInput"] input, input, textarea {{
        background:var(--cf-panel2) !important; color:var(--cf-text) !important; border-color:var(--cf-border) !important;
    }}
    .stButton > button {{ border-radius:12px !important; border:1px solid var(--cf-border) !important; font-weight:800 !important; }}
    .stButton > button[kind="primary"] {{ background:#005BAC !important; color:white !important; border-color:#005BAC !important; }}
    [data-testid="stDataFrame"] {{ border:1px solid var(--cf-border); border-radius:14px; overflow:hidden; }}
    hr {{ border-color: var(--cf-border); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def topbar(title: str, subtitle: str, chip: str = "ClassFit System") -> None:
    st.markdown(
        f"""
        <div class="topbar">
            <div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
            <div class="brand-chip">{chip}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric(label: str, value: Any, help_text: str = "") -> None:
    st.markdown(
        f"""<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="mini">{help_text}</div></div>""",
        unsafe_allow_html=True,
    )


def section(title: str, desc: str = "") -> None:
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    if desc:
        st.markdown(f"<div class='section-desc'>{desc}</div>", unsafe_allow_html=True)


def badge(text: str, kind: str = "info") -> str:
    cls = {"ok": "badge-ok", "bad": "badge-bad", "info": "badge-info"}.get(kind, "badge-info")
    return f"<span class='badge {cls}'>{text}</span>"


# -------------------------
# Algorithm helpers ported from React version
# -------------------------

def quick_sort_rooms(items: list[dict], key: str, reverse: bool = False) -> list[dict]:
    """연결 리스트 기반 퀵 정렬 아이디어를 Streamlit용 리스트 정렬 함수로 구현."""
    if len(items) <= 1:
        return items[:]
    pivot = items[len(items) // 2]

    def val(x: dict):
        if key == "capacity":
            return int(x.get("capacity") or 0)
        if key == "priority":
            return int(x.get("priority") or 0)
        return str(x.get("room_id") or "")

    less = [x for x in items if val(x) < val(pivot)]
    equal = [x for x in items if val(x) == val(pivot)]
    greater = [x for x in items if val(x) > val(pivot)]
    out = quick_sort_rooms(less, key, False) + equal + quick_sort_rooms(greater, key, False)
    return list(reversed(out)) if reverse else out


def room_score(room: dict, requested_capacity: int, preferred_building: str | None = None) -> int:
    waste = max(int(room.get("capacity") or 0) - int(requested_capacity or 0), 0)
    score = 0
    score += int(room.get("priority") or 3) * 10
    score += int(room.get("location_score") or 3) * 4
    score += int(room.get("accessibility_score") or 3) * 4
    score += max(0, 30 - waste)
    if preferred_building and preferred_building != "전체" and room.get("building") == preferred_building:
        score += 25
    return score


def recommend_rooms_priority_queue(date_text: str, start_period: int, end_period: int, min_capacity: int, preferred_building: str = "전체", limit: int = 5) -> list[dict]:
    rows = db.get_available_rooms(date_text, start_period, end_period, min_capacity)
    heap: list[tuple[int, str, dict]] = []
    for room in rows:
        if preferred_building != "전체" and room.get("building") != preferred_building:
            # 선호 건물은 필터가 아니라 가중치로 쓰되, 추천 탭에서는 일치 후보를 우선적으로 보여주기 위해 낮은 패널티만 줌
            pass
        score = room_score(room, min_capacity, preferred_building)
        item = dict(room)
        item["recommend_score"] = score
        heapq.heappush(heap, (-score, item["room_id"], item))
    result = []
    while heap and len(result) < limit:
        result.append(heapq.heappop(heap)[2])
    return result


def build_room_graph(rooms: list[dict]) -> dict[str, list[str]]:
    """같은 건물/같은 층의 인접 강의실을 그래프로 연결해 BFS 대체 추천에 사용."""
    graph: dict[str, set[str]] = {r["room_id"]: set() for r in rooms}
    grouped: dict[tuple[str, int], list[dict]] = {}
    for r in rooms:
        grouped.setdefault((r.get("building"), int(r.get("floor") or 0)), []).append(r)
    for group in grouped.values():
        group = sorted(group, key=lambda x: str(x.get("room_number") or x.get("room_id")))
        for i, r in enumerate(group):
            if i > 0:
                graph[r["room_id"]].add(group[i - 1]["room_id"])
            if i < len(group) - 1:
                graph[r["room_id"]].add(group[i + 1]["room_id"])
    return {k: sorted(v) for k, v in graph.items()}


def bfs_alternatives(start_room_id: str, date_text: str, start_period: int, end_period: int, min_capacity: int, limit: int = 5) -> list[dict]:
    rooms = db.get_rooms()
    by_id = {r["room_id"]: r for r in rooms}
    graph = build_room_graph(rooms)
    visited = {start_room_id}
    queue = [(start_room_id, 0)]
    out = []
    while queue and len(out) < limit:
        cur, dist = queue.pop(0)
        for nxt in graph.get(cur, []):
            if nxt in visited:
                continue
            visited.add(nxt)
            room = by_id.get(nxt)
            if room:
                detail = db.get_conflict_details(nxt, date_text, start_period, end_period)
                if detail["ok"] and int(room.get("capacity") or 0) >= min_capacity:
                    item = dict(room)
                    item["distance"] = dist + 1
                    item["recommend_score"] = room_score(room, min_capacity) - (dist * 3)
                    out.append(item)
            queue.append((nxt, dist + 1))
    if len(out) < limit:
        # 인접 후보가 부족하면 전체 가능 강의실에서 보완
        existing = {r["room_id"] for r in out}
        for r in db.get_available_rooms(date_text, start_period, end_period, min_capacity):
            if r["room_id"] != start_room_id and r["room_id"] not in existing:
                item = dict(r)
                item["distance"] = 99
                item["recommend_score"] = room_score(item, min_capacity)
                out.append(item)
            if len(out) >= limit:
                break
    return sorted(out, key=lambda x: (x.get("distance", 99), -x.get("recommend_score", 0)))[:limit]


def availability_status(room_id: str, date_text: str, period: int) -> str:
    detail = db.get_conflict_details(room_id, date_text, period, period + 1)
    if detail["ok"]:
        return "가능"
    if detail["type"] == "blocked":
        return "수업"
    return "예약"


def analyze_sliding_window(date_text: str, window_size: int, min_capacity: int = 1) -> list[dict]:
    rows = []
    for room in db.get_rooms():
        if int(room.get("capacity") or 0) < min_capacity:
            continue
        free = []
        for p in PERIODS:
            if db.get_conflict_details(room["room_id"], date_text, p, p + 1)["ok"]:
                free.append(p)
        longest = 0
        current = 0
        ranges = []
        start = None
        prev = None
        for p in free:
            if start is None or prev is None or p != prev + 1:
                if start is not None and current >= window_size:
                    ranges.append(f"{start}~{prev + 1}교시")
                start = p
                current = 1
            else:
                current += 1
            prev = p
            longest = max(longest, current)
        if start is not None and current >= window_size:
            ranges.append(f"{start}~{prev + 1}교시")
        if longest >= window_size:
            score = longest * 10 + int(room.get("priority") or 0) * 3 + int(room.get("capacity") or 0) // 10
            rows.append({
                "room_id": room["room_id"], "building": room["building"], "floor": room.get("floor"),
                "capacity": room["capacity"], "longest_streak": longest,
                "available_ranges": ", ".join(ranges) or "-", "priority_score": score,
            })
    return sorted(rows, key=lambda x: (-x["priority_score"], x["room_id"]))


def df_from(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def push_undo(action: dict) -> None:
    st.session_state.setdefault("undo_stack", []).append(action)
    st.session_state["redo_stack"] = []


def history_controls() -> None:
    st.markdown("<div class='soft-card'><b>작업 이력 관리</b><br><span class='mini'>예약 추가/취소 작업을 현재 세션 기준으로 실행 취소하거나 다시 실행합니다.</span></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 4])
    undo_count = len(st.session_state.get("undo_stack", []))
    redo_count = len(st.session_state.get("redo_stack", []))
    with c1:
        if st.button(f"↩ 실행 취소 ({undo_count})", disabled=undo_count == 0, use_container_width=True):
            undo_action()
    with c2:
        if st.button(f"↪ 다시 실행 ({redo_count})", disabled=redo_count == 0, use_container_width=True):
            redo_action()
    with c3:
        st.caption("Undo/Redo는 React 원본의 이중 스택 구조를 Streamlit 세션 상태로 구현했습니다.")


def undo_action() -> None:
    stack = st.session_state.get("undo_stack", [])
    if not stack:
        st.warning("실행 취소할 기록이 없습니다.")
        return
    action = stack.pop()
    if action["type"] == "ADD":
        ok, msg, snapshot = db.cancel_reservation(action["snapshot"]["reservation_id"], actor_user_id=st.session_state.user["user_id"], memo="Undo: 예약 생성 취소")
        if ok:
            st.session_state.setdefault("redo_stack", []).append(action)
            st.success(msg)
        else:
            st.error(msg)
    elif action["type"] == "DELETE":
        ok, msg, restored = db.restore_reservation(action["snapshot"], memo="Undo: 예약 취소 복구")
        if ok:
            st.session_state.setdefault("redo_stack", []).append(action)
            st.success(msg)
        else:
            st.error(msg)
    st.rerun()


def redo_action() -> None:
    stack = st.session_state.get("redo_stack", [])
    if not stack:
        st.warning("다시 실행할 기록이 없습니다.")
        return
    action = stack.pop()
    snap = action["snapshot"]
    if action["type"] == "ADD":
        ok, msg, restored = db.restore_reservation(snap, memo="Redo: 예약 생성 복구")
        if ok:
            action["snapshot"] = restored
            st.session_state.setdefault("undo_stack", []).append(action)
            st.success(msg)
        else:
            st.error(msg)
    elif action["type"] == "DELETE":
        ok, msg, deleted = db.cancel_reservation(snap["reservation_id"], actor_user_id=st.session_state.user["user_id"], memo="Redo: 예약 취소 재실행")
        if ok:
            st.session_state.setdefault("undo_stack", []).append(action)
            st.success(msg)
        else:
            st.error(msg)
    st.rerun()


# -------------------------
# Login / layout
# -------------------------

def login_page() -> None:
    st.markdown("<div style='height:42px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.1, 1.25, 1.1])
    with c2:
        st.markdown(
            """
            <div class="card" style="text-align:center; padding:30px 26px;">
                <div style="width:62px;height:62px;background:#005BAC;border-radius:18px;margin:0 auto 14px auto;display:flex;align-items:center;justify-content:center;font-size:30px;">🏫</div>
                <h2 style="margin-bottom:4px;">가천대학교 통합 로그인</h2>
                <p class="muted">학번 또는 교수 학수번호만 입력하여 ClassFit에 접속하세요.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form", border=False):
            identifier = st.text_input("학번 또는 교수 학수번호", placeholder="예: 202430001 또는 08095006")
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)
            if submitted:
                ok, msg, user = db.login_with_identifier(identifier)
                if ok and user:
                    st.session_state.user = user
                    st.session_state.undo_stack = []
                    st.session_state.redo_stack = []
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        st.caption("로그인 방식: 비밀번호 없이 CSV/DB에 등록된 학생 학번 또는 교수 학수번호만 입력")


def sidebar() -> str:
    user = st.session_state.user
    with st.sidebar:
        st.markdown("### 🏫 ClassFit")
        st.caption("Gachon University Classroom Reservation System")
        st.divider()
        st.markdown(f"**{user['user_name']}**")
        st.caption(f"{ROLE_LABELS.get(user['role'], user['role'])} 계정 · user_id {user['user_id']}")
        theme = st.selectbox("화면 테마", ["다크 모드", "라이트 모드"], index=0, key="theme_select")
        st.session_state.theme = theme
        st.divider()
        role = user["role"]
        if role == "admin":
            menu = st.radio(
                "관리자 메뉴",
                ["실시간 가용 현황판", "강의실 데이터 관리", "강의실 이용 통계", "인프라 관리 센터", "예약 이력 조회"],
            )
        elif role == "professor":
            menu = st.radio(
                "교수 메뉴",
                ["유휴 강의실 연속 공강 조회", "강의실 조회 및 예약", "학과별 정규 주간 시간표", "내 예약 내역 확인"],
            )
        else:
            menu = st.radio("학생 메뉴", ["강의실 조회 및 예약", "내 예약 내역 확인"])
        st.divider()
        if st.button("로그아웃", use_container_width=True):
            for key in ["user", "undo_stack", "redo_stack"]:
                st.session_state.pop(key, None)
            st.rerun()
        return menu


# -------------------------
# Common pages
# -------------------------

def room_search_and_booking() -> None:
    topbar("ClassFit 강의실 조회 및 예약", "다중 필터링, 퀵 정렬, 구간 충돌 검사, BFS 대체 추천을 하나의 예약 플로우로 통합했습니다.", "Student / Professor")
    section("조건별 맞춤 강의실 검색", "React 원본의 검색·예약 화면을 Streamlit 카드형 UI로 재구성했습니다.")
    rooms = db.get_rooms()
    buildings = ["전체"] + sorted({r["building"] for r in rooms})

    f1, f2, f3, f4 = st.columns([1.2, 1, 1.2, 1])
    with f1:
        building = st.selectbox("건물 선택", buildings)
    with f2:
        min_capacity = st.number_input("최소 수용 인원", min_value=1, max_value=300, value=30, step=1)
    with f3:
        query = st.text_input("검색어", placeholder="강의실 번호, room_id, 건물명")
    with f4:
        sort_key = st.selectbox("정렬 기준", ["room_id", "capacity", "priority"])
    order_desc = st.toggle("내림차순 정렬", value=False)
    required_equipment = st.multiselect("필수 기자재", EQUIPMENT_OPTIONS, default=[])

    filtered = []
    for r in rooms:
        if building != "전체" and r["building"] != building:
            continue
        if int(r["capacity"]) < int(min_capacity):
            continue
        hay = " ".join([str(r.get("room_id", "")), str(r.get("room_name", "")), str(r.get("building", "")), str(r.get("room_number", ""))]).lower()
        if query and query.lower() not in hay:
            continue
        eq = set(str(r.get("equipment") or "").split(","))
        eq = {e.strip() for e in eq}
        if required_equipment and not set(required_equipment).issubset(eq):
            continue
        filtered.append(r)
    filtered = quick_sort_rooms(filtered, sort_key, order_desc)

    st.markdown(f"{badge(f'검색 결과 {len(filtered)}개', 'info')}", unsafe_allow_html=True)
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("<div class='card'><b>검색 결과 강의실 목록</b></div>", unsafe_allow_html=True)
        if not filtered:
            st.warning("조건에 맞는 강의실이 없습니다.")
        else:
            for r in filtered[:24]:
                st.markdown(
                    f"""
                    <div class="room-card">
                        <div class="room-title">{r['room_id']}</div>
                        <div class="room-sub">{r['building']} · {r.get('floor','-')}층 · {r.get('room_type','일반강의실')}</div>
                        <div style="margin-top:8px;">{badge(str(r['capacity']) + '명', 'info')} {badge('우선순위 ' + str(r.get('priority', '-')), 'ok')}</div>
                        <div class="mini" style="margin-top:8px;">기자재: {r.get('equipment', '')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    with right:
        st.markdown("<div class='card'><b>예약 신청</b><br><span class='mini'>선택한 날짜/교시 기준으로 DB 충돌 검사를 수행합니다.</span></div>", unsafe_allow_html=True)
        room_options = [r["room_id"] for r in filtered] or [r["room_id"] for r in rooms]
        selected_room = st.selectbox("예약할 강의실", room_options)
        res_date = st.date_input("예약 일자", value=DateType.today(), key="reserve_date_search").strftime("%Y-%m-%d")
        c1, c2 = st.columns(2)
        with c1:
            start_p = st.selectbox("시작 교시", PERIODS, index=0, key="reserve_start_search")
        with c2:
            valid_ends = [p for p in END_PERIODS if p > start_p]
            end_p = st.selectbox("종료 교시", valid_ends, index=0, key="reserve_end_search")
        purpose = st.text_area("이용 목적", placeholder="예: 전공 보충 스터디, 프로젝트 회의 등", key="reserve_purpose_search")
        detail = db.get_conflict_details(selected_room, res_date, start_p, end_p)
        if detail["ok"]:
            st.markdown(f"{badge('예약 가능', 'ok')} <span class='mini'>{detail['message']}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"{badge('충돌 감지', 'bad')} <span class='mini'>{detail['message']}</span>", unsafe_allow_html=True)
            section("BFS 대체 강의실 추천", "같은 건물/층 인접 그래프를 BFS로 탐색한 뒤 가능한 강의실을 제안합니다.")
            alts = bfs_alternatives(selected_room, res_date, start_p, end_p, int(min_capacity), 5)
            for a in alts:
                st.markdown(f"- **{a['room_id']}** · {a['building']} {a.get('floor','-')}층 · 정원 {a['capacity']}명 · 거리 {a.get('distance','-')}")
        if st.button("예약 신청", type="primary", use_container_width=True):
            ok, msg, snapshot = db.add_reservation(selected_room, res_date, int(start_p), int(end_p), st.session_state.user["user_id"], purpose)
            if ok:
                push_undo({"type": "ADD", "snapshot": snapshot})
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    section("우선순위 큐 기반 Top-K 추천", "현재 입력한 날짜/교시/인원 조건을 기준으로 추천 점수가 높은 강의실을 추출합니다.")
    recs = recommend_rooms_priority_queue(res_date, int(start_p), int(end_p), int(min_capacity), building, limit=5)
    if recs:
        cols = st.columns(min(5, len(recs)))
        for col, r in zip(cols, recs):
            with col:
                st.markdown(
                    f"""
                    <div class="room-card">
                        <div class="room-title">{r['room_id']}</div>
                        <div class="room-sub">{r['building']} · {r.get('floor','-')}층</div>
                        <div style="margin-top:8px;">{badge('추천점수 ' + str(r['recommend_score']), 'ok')}</div>
                        <div class="mini">정원 {r['capacity']}명 · {r.get('room_type','')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("현재 조건에서 추천 가능한 강의실이 없습니다.")


def my_reservations_page() -> None:
    topbar("내 예약 내역 확인", "현재 로그인 계정 기준 예약과 생성/취소 이력을 확인합니다.", "History Stack")
    history_controls()
    rows = db.get_user_reservations(st.session_state.user["user_id"])
    st.markdown(f"{badge(f'활성 예약 {len(rows)}건', 'info')}", unsafe_allow_html=True)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown("#### 예약 취소")
        cancel_id = st.selectbox("취소할 예약 ID", [r["reservation_id"] for r in rows])
        if st.button("선택 예약 취소", type="primary"):
            ok, msg, snapshot = db.cancel_reservation(cancel_id, actor_user_id=st.session_state.user["user_id"], memo="사용자 직접 취소")
            if ok:
                push_undo({"type": "DELETE", "snapshot": snapshot})
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    else:
        st.info("현재 계정으로 등록된 예약 내역이 없습니다.")

    section("예약 생성/취소 이력", "reservation_history 테이블에 기록된 사용자의 작업 로그입니다.")
    hist = db.get_reservation_history(user_id=st.session_state.user["user_id"], limit=100)
    if hist:
        st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
    else:
        st.caption("아직 이력이 없습니다.")


# -------------------------
# Professor pages
# -------------------------

def vacant_finder_page() -> None:
    topbar("유휴 강의실 연속 공강 조회", "Sliding Window 방식으로 연속 공강이 긴 강의실을 탐색하고 우선순위 점수로 정렬합니다.", "Professor Portal")
    c1, c2, c3 = st.columns(3)
    with c1:
        target_date = st.date_input("조회 날짜", value=DateType.today()).strftime("%Y-%m-%d")
    with c2:
        window = st.slider("최소 연속 공강", 1, 6, 3)
    with c3:
        min_cap = st.number_input("최소 정원", min_value=1, max_value=300, value=30)
    rows = analyze_sliding_window(target_date, int(window), int(min_cap))
    st.markdown(f"{badge(f'조건 충족 {len(rows)}개', 'ok' if rows else 'bad')}", unsafe_allow_html=True)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("조건을 충족하는 빈 강의실이 없습니다.")


def academic_schedule_page() -> None:
    topbar("학과별 정규 주간 시간표", "원본 엑셀에서 전처리한 blocked_schedules 테이블입니다. 해당 시간대는 일반 예약이 차단됩니다.", "Blocked Schedule")
    rooms = db.get_rooms()
    buildings = ["전체"] + sorted({r["building"] for r in rooms})
    c1, c2 = st.columns(2)
    with c1:
        day = st.selectbox("요일", ["전체"] + KOREAN_DAYS)
    with c2:
        building = st.selectbox("건물", buildings)
    rows = db.get_blocked_schedules(day=day, building=building)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("조건에 맞는 정규 시간표가 없습니다.")


# -------------------------
# Admin pages
# -------------------------

def admin_dashboard_page() -> None:
    topbar("종합 공간 가용 현황실", "정규 수업과 실시간 예약을 함께 반영한 강의실 × 교시 상태판입니다.", "Admin Dashboard")
    counts = db.get_counts()
    c1, c2, c3, c4 = st.columns(4)
    with c1: metric("강의실", counts["rooms"], "rooms 테이블")
    with c2: metric("기존 수업 차단", counts["blocked_schedules"], "blocked_schedules")
    with c3: metric("실시간 예약", counts["reservations"], "reservations")
    with c4: metric("예약 이력", counts["reservation_history"], "reservation_history")

    target_date = st.date_input("현황 날짜", value=DateType.today(), key="admin_dash_date").strftime("%Y-%m-%d")
    rooms = db.get_rooms()
    show_count = st.slider("표시할 강의실 수", 5, min(40, len(rooms)), min(20, len(rooms)))
    table_rows = []
    for r in rooms[:show_count]:
        row = {"room_id": r["room_id"], "capacity": r["capacity"]}
        for p in PERIODS:
            status = availability_status(r["room_id"], target_date, p)
            row[f"{p}교시"] = {"가능": "🟢 가능", "수업": "🔵 수업", "예약": "🔴 예약"}[status]
        table_rows.append(row)
    st.markdown("<div class='status-grid'>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    section("연속 공강 강의실 보고서", "Sliding Window 결과를 우선순위 지수 기준으로 정렬합니다.")
    window = st.slider("최소 연속 공강 교시", 1, 6, 3, key="admin_window")
    rows = analyze_sliding_window(target_date, int(window), 1)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("조건을 충족하는 빈 강의실이 없습니다.")


def room_management_page() -> None:
    topbar("강의 시설 관리 대장", "강의실 정보를 등록, 수정, 삭제합니다. 변경 즉시 SQLite DB에 반영됩니다.", "CRUD")
    rooms = db.get_rooms()
    tab1, tab2 = st.tabs(["강의실 목록", "추가/수정/삭제"])
    with tab1:
        st.dataframe(pd.DataFrame(rooms), use_container_width=True, hide_index=True)
    with tab2:
        mode = st.radio("작업", ["추가", "수정", "삭제"], horizontal=True)
        existing_ids = [r["room_id"] for r in rooms]
        selected = None
        if mode in {"수정", "삭제"}:
            selected_id = st.selectbox("대상 강의실", existing_ids)
            selected = db.get_room(selected_id)
        if mode == "삭제":
            if selected:
                st.warning(f"{selected['room_id']} 강의실과 관련된 정규 시간표/예약 데이터가 함께 삭제됩니다.")
                if st.button("강의실 삭제", type="primary"):
                    ok, msg = db.delete_room(selected["room_id"])
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()
        else:
            base = selected or {}
            with st.form("room_form"):
                room_id = st.text_input("room_id", value=base.get("room_id", ""), disabled=(mode == "수정"))
                building = st.text_input("building", value=base.get("building", "AI관"))
                floor = st.number_input("floor", min_value=0, max_value=50, value=int(base.get("floor") or 1))
                room_number = st.text_input("room_number", value=str(base.get("room_number", "")))
                room_name = st.text_input("room_name", value=base.get("room_name", room_id if room_id else ""))
                capacity = st.number_input("capacity", min_value=1, max_value=500, value=int(base.get("capacity") or 40))
                room_type = st.selectbox("room_type", ["소형강의실", "일반강의실", "대형강의실", "세미나실", "컴퓨터실"], index=1)
                c1, c2, c3 = st.columns(3)
                with c1: location_score = st.slider("location_score", 1, 5, int(base.get("location_score") or 3))
                with c2: accessibility_score = st.slider("accessibility_score", 1, 5, int(base.get("accessibility_score") or 3))
                with c3: priority = st.slider("priority", 1, 5, int(base.get("priority") or 3))
                equipment = st.text_input("equipment", value=base.get("equipment", "projector,computer,whiteboard"))
                submitted = st.form_submit_button("저장", type="primary")
                if submitted:
                    payload = {
                        "room_id": room_id if mode == "추가" else selected["room_id"],
                        "building": building,
                        "floor": floor,
                        "room_number": room_number,
                        "room_name": room_name or room_id,
                        "capacity": capacity,
                        "capacity_avg": base.get("capacity_avg"),
                        "room_type": room_type,
                        "location_score": location_score,
                        "accessibility_score": accessibility_score,
                        "priority": priority,
                        "equipment": equipment,
                        "source_course_count": base.get("source_course_count", 0),
                    }
                    ok, msg = db.upsert_room(payload)
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()


def statistics_page() -> None:
    topbar("강의실 이용 누적 통계 분석", "예약 로그를 건물/강의실 단위로 집계한 통계 리포트입니다.", "Analytics")
    counts = db.get_counts()
    c1, c2, c3 = st.columns(3)
    with c1: metric("누적 활성 예약", counts["reservations"], "현재 살아 있는 예약")
    with c2: metric("누적 이력", counts["reservation_history"], "생성/취소/복구 로그")
    with c3: metric("등록 사용자", counts["users"], "users 테이블")
    room_stats = pd.DataFrame(db.get_room_usage_stats())
    building_stats = pd.DataFrame(db.get_building_usage_stats())
    if not room_stats.empty:
        section("강의실별 예약 점유수")
        st.bar_chart(room_stats.set_index("room_id")["reservation_count"])
        st.dataframe(room_stats, use_container_width=True, hide_index=True)
    if not building_stats.empty:
        section("건물별 예약 점유수")
        st.bar_chart(building_stats.set_index("building")["reservation_count"])


def infrastructure_page() -> None:
    topbar("시스템 인프라 관리 센터", "CSV 마스터 데이터 동기화, 예약 로그 초기화, DB 상태 확인을 수행합니다.", "Infrastructure")
    counts = db.get_counts()
    st.dataframe(pd.DataFrame([counts]), use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='card'><b>마스터 데이터 재동기화</b><br><span class='mini'>rooms.csv, blocked_schedules.csv, users_sample.csv 기준으로 DB를 초기화합니다.</span></div>", unsafe_allow_html=True)
        if st.button("마스터 데이터 동기화 및 DB 초기화", type="primary", use_container_width=True):
            db.reset_db_from_csv()
            st.success("DB가 마스터 CSV 기준으로 초기화되었습니다.")
            st.rerun()
    with c2:
        st.markdown("<div class='card'><b>예약 내역 초기화</b><br><span class='mini'>현재 실시간 예약만 삭제합니다. 이력 삭제 여부를 선택할 수 있습니다.</span></div>", unsafe_allow_html=True)
        clear_hist = st.checkbox("reservation_history도 함께 삭제")
        if st.button("실시간 예약 내역 전체 초기화", use_container_width=True):
            ok, msg = db.purge_reservations(clear_history=clear_hist)
            st.success(msg) if ok else st.error(msg)
            st.rerun()


def reservation_history_page() -> None:
    topbar("예약 이력 조회", "reservation_history 테이블에 저장된 전체 예약 생성/취소/복구 로그입니다.", "History Table")
    users = db.get_all_users()
    rooms = db.get_rooms()
    c1, c2, c3 = st.columns(3)
    with c1:
        user_opt = st.selectbox("사용자", ["전체"] + [f"{u['user_id']} · {u['user_name']}" for u in users])
    with c2:
        room_opt = st.selectbox("강의실", ["전체"] + [r["room_id"] for r in rooms])
    with c3:
        use_date = st.checkbox("날짜 필터")
        target_date = st.date_input("날짜", value=DateType.today()).strftime("%Y-%m-%d") if use_date else None
    user_id = None if user_opt == "전체" else int(user_opt.split("·")[0].strip())
    room_id = None if room_opt == "전체" else room_opt
    rows = db.get_reservation_history(user_id=user_id, room_id=room_id, date=target_date, limit=500)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("조건에 맞는 이력이 없습니다.")


# -------------------------
# Main
# -------------------------

def main() -> None:
    db.ensure_seed_data()
    if "theme" not in st.session_state:
        st.session_state.theme = "다크 모드"
    apply_theme(st.session_state.theme)
    if "user" not in st.session_state:
        login_page()
        return
    menu = sidebar()
    apply_theme(st.session_state.get("theme_select", st.session_state.theme))

    if menu == "강의실 조회 및 예약":
        room_search_and_booking()
    elif menu == "내 예약 내역 확인":
        my_reservations_page()
    elif menu == "유휴 강의실 연속 공강 조회":
        vacant_finder_page()
    elif menu == "학과별 정규 주간 시간표":
        academic_schedule_page()
    elif menu == "실시간 가용 현황판":
        admin_dashboard_page()
    elif menu == "강의실 데이터 관리":
        room_management_page()
    elif menu == "강의실 이용 통계":
        statistics_page()
    elif menu == "인프라 관리 센터":
        infrastructure_page()
    elif menu == "예약 이력 조회":
        reservation_history_page()


if __name__ == "__main__":
    main()

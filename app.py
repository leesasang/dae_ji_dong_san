from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import streamlit as st
import streamlit.components.v1 as components

import database as db

BASE_DIR = Path(__file__).resolve().parent
COMPONENT_BUILD_DIR = BASE_DIR / "component" / "dist"

st.set_page_config(
    page_title="ClassFit | 가천대학교 강의실 예약 시스템",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Streamlit shell 자체는 최소화하고, 화면은 React Custom Component가 담당한다.
st.markdown(
    """
    <style>
    #MainMenu, header, footer { visibility: hidden; }
    .stApp { background: #F8FAFC; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    [data-testid="stToolbar"] { display: none !important; }
    iframe { border: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _declare_component():
    index_file = COMPONENT_BUILD_DIR / "index.html"
    assets_dir = COMPONENT_BUILD_DIR / "assets"
    js_files = list(assets_dir.glob("*.js")) if assets_dir.exists() else []
    css_files = list(assets_dir.glob("*.css")) if assets_dir.exists() else []

    if not COMPONENT_BUILD_DIR.exists() or not index_file.exists() or not js_files or not css_files:
        st.error(
            "React 컴포넌트 빌드 파일이 완전하지 않습니다. "
            "component 폴더에서 `npm install && npm run build`를 실행하거나, "
            "dist/assets 폴더까지 포함된 ZIP 전체를 다시 업로드하세요."
        )
        st.stop()

    # Streamlit Cloud와 브라우저가 이전 실패한 컴포넌트 경로를 캐시하는 경우가 있어
    # 컴포넌트 이름에 버전을 붙여 새 프론트엔드 엔드포인트를 강제로 사용하게 한다.
    return components.declare_component("classfit_react_ui_v14", path=str(COMPONENT_BUILD_DIR))


classfit_react_ui = _declare_component()


def init_state() -> None:
    if "user" not in st.session_state:
        st.session_state.user = None
    if "notice" not in st.session_state:
        st.session_state.notice = {"type": "info", "message": ""}
    if "last_event_id" not in st.session_state:
        st.session_state.last_event_id = None
    if "undo_stack" not in st.session_state:
        st.session_state.undo_stack = []
    if "redo_stack" not in st.session_state:
        st.session_state.redo_stack = []


def set_notice(kind: str, message: str) -> None:
    st.session_state.notice = {"type": kind, "message": message}


def current_user_id() -> Optional[int]:
    user = st.session_state.get("user")
    if not user:
        return None
    return int(user["user_id"])


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def handle_login(action: dict) -> None:
    identifier = str(action.get("identifier") or "").strip()
    ok, message, user = db.login_with_identifier(identifier)
    if not ok or user is None:
        set_notice("error", message)
        return
    user["login_id"] = identifier
    st.session_state.user = user
    set_notice("success", message)


def handle_logout() -> None:
    st.session_state.user = None
    st.session_state.undo_stack = []
    st.session_state.redo_stack = []
    set_notice("info", "로그아웃되었습니다.")


def handle_reserve(action: dict) -> None:
    user_id = current_user_id()
    if user_id is None:
        set_notice("error", "로그인이 필요합니다.")
        return
    room_id = str(action.get("room_id") or "").strip()
    date = str(action.get("date") or "").strip()
    start_period = safe_int(action.get("start_period"), 0)
    end_period = safe_int(action.get("end_period"), 0)
    purpose = str(action.get("purpose") or "").strip()
    ok, message, snapshot = db.add_reservation(
        room_id=room_id,
        date=date,
        start_period=start_period,
        end_period=end_period,
        user_id=user_id,
        purpose=purpose,
    )
    if ok and snapshot:
        st.session_state.undo_stack.append({"type": "CREATE", "snapshot": snapshot})
        st.session_state.redo_stack = []
        set_notice("success", message)
    else:
        set_notice("error", message)


def handle_cancel(action: dict) -> None:
    user_id = current_user_id()
    if user_id is None:
        set_notice("error", "로그인이 필요합니다.")
        return
    reservation_id = safe_int(action.get("reservation_id"), 0)
    target = db.get_reservation_by_id(reservation_id)
    user = st.session_state.get("user") or {}
    if not target:
        set_notice("error", "예약 취소 실패: 해당 예약 ID를 찾을 수 없습니다.")
        return
    if user.get("role") != "admin" and int(target.get("user_id")) != int(user_id):
        set_notice("error", "본인 예약만 취소할 수 있습니다.")
        return

    ok, message, snapshot = db.cancel_reservation(
        reservation_id=reservation_id,
        actor_user_id=user_id,
        memo="사용자 요청에 의한 예약 취소",
    )
    if ok and snapshot:
        st.session_state.undo_stack.append({"type": "CANCEL", "snapshot": snapshot})
        st.session_state.redo_stack = []
        set_notice("success", message)
    else:
        set_notice("error", message)


def handle_undo() -> None:
    if not st.session_state.undo_stack:
        set_notice("info", "실행 취소할 작업이 없습니다.")
        return
    action = st.session_state.undo_stack.pop()
    typ = action.get("type")
    snapshot = action.get("snapshot") or {}
    if typ == "CREATE":
        ok, message, canceled = db.cancel_reservation(
            reservation_id=int(snapshot.get("reservation_id")),
            actor_user_id=current_user_id(),
            memo="Undo: 예약 생성 취소",
        )
        if ok:
            st.session_state.redo_stack.append(action)
            set_notice("success", "예약 생성 작업을 실행 취소했습니다.")
        else:
            st.session_state.undo_stack.append(action)
            set_notice("error", message)
    elif typ == "CANCEL":
        ok, message, restored = db.restore_reservation(snapshot, memo="Undo: 예약 취소 복구")
        if ok:
            # restore_reservation이 reservation_id를 갱신할 수 있으므로 snapshot 보정
            action["snapshot"] = restored or snapshot
            st.session_state.redo_stack.append(action)
            set_notice("success", "예약 취소 작업을 실행 취소했습니다.")
        else:
            st.session_state.undo_stack.append(action)
            set_notice("error", message)


def handle_redo() -> None:
    if not st.session_state.redo_stack:
        set_notice("info", "다시 실행할 작업이 없습니다.")
        return
    action = st.session_state.redo_stack.pop()
    typ = action.get("type")
    snapshot = action.get("snapshot") or {}
    if typ == "CREATE":
        ok, message, restored = db.restore_reservation(snapshot, memo="Redo: 예약 생성 재실행")
        if ok:
            action["snapshot"] = restored or snapshot
            st.session_state.undo_stack.append(action)
            set_notice("success", "예약 생성 작업을 다시 실행했습니다.")
        else:
            st.session_state.redo_stack.append(action)
            set_notice("error", message)
    elif typ == "CANCEL":
        ok, message, canceled = db.cancel_reservation(
            reservation_id=int(snapshot.get("reservation_id")),
            actor_user_id=current_user_id(),
            memo="Redo: 예약 취소 재실행",
        )
        if ok:
            st.session_state.undo_stack.append(action)
            set_notice("success", "예약 취소 작업을 다시 실행했습니다.")
        else:
            st.session_state.redo_stack.append(action)
            set_notice("error", message)


def handle_reset(action: dict) -> None:
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        set_notice("error", "관리자만 초기화할 수 있습니다.")
        return
    clear_history = bool(action.get("clear_history"))
    ok, message = db.purge_reservations(clear_history=clear_history)
    if ok:
        st.session_state.undo_stack = []
        st.session_state.redo_stack = []
        set_notice("success", message)
    else:
        set_notice("error", message)


def process_action(action: Any) -> bool:
    if not isinstance(action, dict) or not action.get("type"):
        return False
    event_id = action.get("event_id")
    if event_id and event_id == st.session_state.last_event_id:
        return False
    st.session_state.last_event_id = event_id

    kind = action.get("type")
    if kind == "login":
        handle_login(action)
    elif kind == "logout":
        handle_logout()
    elif kind == "reserve":
        handle_reserve(action)
    elif kind == "cancel":
        handle_cancel(action)
    elif kind == "undo":
        handle_undo()
    elif kind == "redo":
        handle_redo()
    elif kind == "reset_reservations":
        handle_reset(action)
    else:
        set_notice("error", f"알 수 없는 작업입니다: {kind}")
    return True


def build_payload() -> dict:
    user = st.session_state.get("user")
    rooms = db.get_rooms()
    all_reservations = db.get_all_reservations()
    counts = db.get_counts()
    current_availability = db.get_current_availability_summary()
    counts.update({
        "current_available": current_availability.get("available_now", 0),
        "current_unavailable": current_availability.get("unavailable_now", 0),
        "current_total_rooms": current_availability.get("total_rooms", counts.get("rooms", 0)),
    })

    blocked = db.get_blocked_schedules()
    user_reservations = []
    can_view_history = False
    if user:
        user_reservations = db.get_user_reservations(int(user["user_id"]))
        can_view_history = user.get("role") == "admin"

    # 학생/교수에게는 전체 예약자의 이름/목적/예약ID를 넘기지 않는다.
    # 화면의 빈 강의실 계산과 현황판 표시에 필요한 최소 슬롯 정보만 제공한다.
    if can_view_history:
        reservations = all_reservations
        history = db.get_reservation_history(limit=250)
    else:
        reservations = [
            {
                "room_id": r.get("room_id"),
                "date": r.get("date"),
                "day": r.get("day"),
                "start_period": r.get("start_period"),
                "end_period": r.get("end_period"),
            }
            for r in all_reservations
        ]
        history = []

    return {
        "user": user,
        "rooms": rooms,
        "reservations": reservations,
        "blocked": blocked,
        "history": history,
        "userReservations": user_reservations,
        "counts": counts,
        "currentAvailability": current_availability,
        "canViewHistory": can_view_history,
        "notice": st.session_state.notice,
        "undoCount": len(st.session_state.undo_stack),
        "redoCount": len(st.session_state.redo_stack),
    }


def main() -> None:
    db.ensure_seed_data()
    init_state()

    payload = build_payload()
    action = classfit_react_ui(payload=payload, default=None, key="classfit_react_custom_component")

    if process_action(action):
        st.rerun()


if __name__ == "__main__":
    main()

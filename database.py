"""
ClassFit database module - final Streamlit version

핵심 역할
- SQLite DB 스키마 생성 및 CSV 기반 초기 데이터 적재
- users 테이블 기반 로그인/사용자 관리
- reservations 테이블에서 user_id 외래키 사용
- reservation_history 테이블로 예약 생성/취소/복구 이력 기록
- 기존 수업 시간표(blocked_schedules)와 실시간 예약(reservations) 충돌 검사
- 강의실 CRUD, 빈 강의실 탐색, 통계/현황 조회 지원
"""
from __future__ import annotations

import csv
import hashlib
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Iterable, Optional, Sequence

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "classfit.db"
DATA_DIR = BASE_DIR / "data"
ROOMS_CSV_PATH = DATA_DIR / "rooms.csv"
BLOCKED_CSV_PATH = DATA_DIR / "blocked_schedules.csv"
USERS_CSV_PATH = DATA_DIR / "users_sample.csv"

KOREAN_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
VALID_ROLES = {"student", "professor", "admin", "user"}

DEFAULT_USERS = [
    # user_name, password, role, student_id, department, email
    ("admin", "admin123", "admin", "", "", ""),
    ("user1", "1234", "student", "", "", ""),
    ("user2", "1234", "student", "", "", ""),
]


def dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_day_from_date(date_text: str) -> str:
    dt = datetime.strptime(str(date_text), "%Y-%m-%d")
    return KOREAN_WEEKDAYS[dt.weekday()]


def hash_password(password: str) -> str:
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()


def connect_db(row_factory: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    if row_factory:
        conn.row_factory = dict_factory
    return conn


def init_db() -> None:
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            room_id TEXT PRIMARY KEY,
            building TEXT NOT NULL,
            floor INTEGER,
            room_number TEXT,
            room_name TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            capacity_avg REAL,
            room_type TEXT,
            location_score INTEGER DEFAULT 3,
            accessibility_score INTEGER DEFAULT 3,
            priority INTEGER DEFAULT 3,
            equipment TEXT DEFAULT 'projector,computer,whiteboard',
            source_course_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS blocked_schedules (
            blocked_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id TEXT NOT NULL,
            room_id TEXT NOT NULL,
            day TEXT NOT NULL,
            period INTEGER NOT NULL,
            capacity INTEGER,
            source_row INTEGER,
            FOREIGN KEY (room_id) REFERENCES rooms(room_id)
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            student_id TEXT UNIQUE,
            department TEXT,
            email TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reservations (
            reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            date TEXT NOT NULL,
            day TEXT NOT NULL,
            start_period INTEGER NOT NULL,
            end_period INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            purpose TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(room_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS reservation_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER,
            action TEXT NOT NULL CHECK(action IN ('CREATE', 'CANCEL', 'RESTORE')),
            room_id TEXT NOT NULL,
            date TEXT NOT NULL,
            day TEXT NOT NULL,
            start_period INTEGER NOT NULL,
            end_period INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            purpose TEXT,
            action_at TEXT DEFAULT CURRENT_TIMESTAMP,
            memo TEXT,
            FOREIGN KEY (room_id) REFERENCES rooms(room_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_blocked_room_day_period
        ON blocked_schedules(room_id, day, period);

        CREATE INDEX IF NOT EXISTS idx_blocked_day_period
        ON blocked_schedules(day, period);

        CREATE INDEX IF NOT EXISTS idx_users_user_name
        ON users(user_name);

        CREATE INDEX IF NOT EXISTS idx_reservations_user_id
        ON reservations(user_id);

        CREATE INDEX IF NOT EXISTS idx_reservations_room_date_period
        ON reservations(room_id, date, start_period, end_period);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_reservations_exact_slot_unique
        ON reservations(room_id, date, start_period, end_period);

        CREATE INDEX IF NOT EXISTS idx_reservations_date
        ON reservations(date);

        CREATE INDEX IF NOT EXISTS idx_history_user_id
        ON reservation_history(user_id);

        CREATE INDEX IF NOT EXISTS idx_history_room_date
        ON reservation_history(room_id, date);

        CREATE INDEX IF NOT EXISTS idx_rooms_capacity
        ON rooms(capacity);
        """
    )
    conn.commit()
    conn.close()


def _insert_user_row(cur: sqlite3.Cursor, user_name: str, password: str, role: str, student_id: str = "", department: str = "", email: str = "") -> None:
    cur.execute(
        """
        INSERT OR IGNORE INTO users
        (user_name, password_hash, role, student_id, department, email)
        VALUES (?, ?, ?, NULLIF(?, ''), NULLIF(?, ''), NULLIF(?, ''));
        """,
        (str(user_name).strip(), hash_password(password), role, student_id or "", department or "", email or ""),
    )


def _insert_default_users(cur: sqlite3.Cursor) -> None:
    # CSV가 있으면 CSV 우선 반영, 없으면 DEFAULT_USERS 사용
    inserted = False
    if USERS_CSV_PATH.exists():
        with open(USERS_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                _insert_user_row(
                    cur,
                    row.get("user_name") or row.get("name") or f"user{row.get('user_id', '')}",
                    row.get("password") or "1234",
                    normalize_role(row.get("role") or "student"),
                    row.get("student_id") or "",
                    row.get("department") or "",
                    row.get("email") or "",
                )
                inserted = True
    if not inserted:
        for user_name, password, role, sid, dept, email in DEFAULT_USERS:
            _insert_user_row(cur, user_name, password, role, sid, dept, email)


def normalize_role(role: str) -> str:
    role = (role or "student").strip().lower()
    if role == "user":
        return "student"
    if role in {"student", "professor", "admin"}:
        return role
    return "student"


def reset_db_from_csv() -> None:
    """CSV 기반 마스터 데이터로 DB 전체 초기화. 예약/history도 빈 상태로 재생성한다."""
    init_db()
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        cur.execute("DELETE FROM reservation_history;")
        cur.execute("DELETE FROM reservations;")
        cur.execute("DELETE FROM blocked_schedules;")
        cur.execute("DELETE FROM rooms;")
        cur.execute("DELETE FROM users;")
        cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('reservation_history','reservations','blocked_schedules','users');")

        with open(ROOMS_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rooms = []
            for row in reader:
                rooms.append(
                    (
                        row["room_id"],
                        row["building"],
                        int(row["floor"]) if row.get("floor") else None,
                        row.get("room_number", ""),
                        row.get("room_name") or row["room_id"],
                        int(float(row["capacity"])),
                        float(row["capacity_avg"]) if row.get("capacity_avg") else None,
                        row.get("room_type", "일반강의실"),
                        int(row.get("location_score") or 3),
                        int(row.get("accessibility_score") or 3),
                        int(row.get("priority") or 3),
                        row.get("equipment") or "projector,computer,whiteboard",
                        int(row.get("source_course_count") or 0),
                    )
                )
        cur.executemany(
            """
            INSERT INTO rooms
            (room_id, building, floor, room_number, room_name, capacity, capacity_avg,
             room_type, location_score, accessibility_score, priority, equipment, source_course_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            rooms,
        )

        with open(BLOCKED_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            blocked = []
            for row in reader:
                blocked.append(
                    (
                        row["course_id"],
                        row["room_id"],
                        row["day"],
                        int(row["period"]),
                        int(row["capacity"]) if row.get("capacity") not in (None, "") else None,
                        int(row["source_row"]) if row.get("source_row") not in (None, "") else None,
                    )
                )
        cur.executemany(
            """
            INSERT INTO blocked_schedules
            (course_id, room_id, day, period, capacity, source_row)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            blocked,
        )
        _insert_default_users(cur)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_seed_data() -> None:
    init_db()
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rooms;")
    room_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users;")
    user_count = cur.fetchone()[0]
    if room_count == 0:
        conn.close()
        reset_db_from_csv()
        return
    if user_count == 0:
        cur.execute("BEGIN IMMEDIATE;")
        _insert_default_users(cur)
        conn.commit()
    conn.close()


# -------------------------
# Users / authentication
# -------------------------

def create_user(user_name: str, password: str = "1234", role: str = "student", student_id: str | None = None, department: str | None = None, email: str | None = None):
    if not user_name or not str(user_name).strip():
        return False, "사용자명은 비울 수 없습니다.", None
    if not password:
        password = "1234"
    role = normalize_role(role)
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        cur.execute(
            """
            INSERT INTO users (user_name, password_hash, role, student_id, department, email)
            VALUES (?, ?, ?, NULLIF(?, ''), NULLIF(?, ''), NULLIF(?, ''));
            """,
            (str(user_name).strip(), hash_password(password), role, student_id or "", department or "", email or ""),
        )
        user_id = cur.lastrowid
        conn.commit()
        return True, f"사용자 생성 완료: user_id {user_id}", user_id
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        return False, f"사용자 생성 실패: 중복된 user_name/student_id/email이 있습니다. ({exc})", None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, user_name, role, student_id, department, email, created_at
        FROM users WHERE user_id = ?;
        """,
        (int(user_id),),
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_name(user_name: str) -> Optional[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, user_name, role, student_id, department, email, created_at
        FROM users WHERE user_name = ?;
        """,
        (str(user_name).strip(),),
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_all_users() -> list[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, user_name, role, student_id, department, email, created_at
        FROM users ORDER BY user_id ASC;
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def authenticate_user(user_name: str, password: str) -> Optional[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, user_name, role, student_id, department, email, created_at
        FROM users
        WHERE user_name = ? AND password_hash = ?;
        """,
        (str(user_name).strip(), hash_password(password)),
    )
    row = cur.fetchone()
    conn.close()
    return row


PROFESSOR_LOGIN_IDS = {"08095006", "13970001", "14268001", "14271001", "14283001", "14798002"}
ADMIN_LOGIN_IDS = {"admin"}


def is_valid_student_login_id(identifier: str) -> bool:
    """2021~2026학번 중 30001~39999 범위만 학생 로그인 ID로 인정한다."""
    if not identifier.isdigit() or len(identifier) != 9:
        return False
    year = identifier[:4]
    number = int(identifier[4:])
    return year in {"2021", "2022", "2023", "2024", "2025", "2026"} and 30001 <= number <= 39999


def is_valid_professor_login_id(identifier: str) -> bool:
    """지정된 교수 학수번호만 교수 로그인 ID로 인정한다."""
    return identifier in PROFESSOR_LOGIN_IDS


def is_valid_admin_login_id(identifier: str) -> bool:
    """관리자 로그인 ID를 인정한다."""
    return identifier in ADMIN_LOGIN_IDS


def login_with_identifier(identifier: str) -> tuple[bool, str, Optional[dict]]:
    """비밀번호 없이 CSV/DB에 등록된 학번 또는 교수 학수번호만으로 로그인한다.

    - 학생: 202130001~202139999, 202230001~202239999, ..., 202630001~202639999
    - 교수: 지정된 6개 학수번호만 허용
    - 관리자: admin 계정 허용
    - 보안 목적의 실제 인증이 아니라, 알고리즘 프로젝트용 식별자 기반 로그인이다.
    """
    identifier = str(identifier or "").strip()
    if not identifier:
        return False, "학번 또는 교수 학수번호를 입력해야 합니다.", None

    # 학생 학번, 지정 교수 학수번호, 관리자 코드만 로그인 허용
    if not (is_valid_student_login_id(identifier) or is_valid_professor_login_id(identifier) or is_valid_admin_login_id(identifier)):
        return False, "등록 가능한 형식의 학번, 교수 학수번호 또는 관리자 코드가 아닙니다.", None

    user = get_user_by_name(identifier)
    if not user:
        return False, "CSV 기반 users 테이블에 등록되지 않은 계정입니다.", None

    user["role"] = normalize_role(user["role"])
    if user["role"] == "student" and is_valid_student_login_id(identifier):
        return True, "학생 계정으로 로그인되었습니다.", user
    if user["role"] == "professor" and is_valid_professor_login_id(identifier):
        return True, "교수 계정으로 로그인되었습니다.", user
    if user["role"] == "admin" and is_valid_admin_login_id(identifier):
        return True, "관리자 계정으로 로그인되었습니다.", user

    return False, "계정 역할과 입력 ID 형식이 일치하지 않습니다.", None

# -------------------------
# Room operations
# -------------------------

def get_rooms() -> list[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms ORDER BY building, floor, room_number, room_id;")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_room(room_id: str) -> Optional[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute("SELECT * FROM rooms WHERE room_id = ?;", (room_id,))
    row = cur.fetchone()
    conn.close()
    return row


def upsert_room(room: dict) -> tuple[bool, str]:
    required = ["room_id", "building", "room_name", "capacity"]
    for k in required:
        if room.get(k) in (None, ""):
            return False, f"필수 값 누락: {k}"
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        cur.execute(
            """
            INSERT INTO rooms
            (room_id, building, floor, room_number, room_name, capacity, capacity_avg,
             room_type, location_score, accessibility_score, priority, equipment, source_course_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(room_id) DO UPDATE SET
              building=excluded.building,
              floor=excluded.floor,
              room_number=excluded.room_number,
              room_name=excluded.room_name,
              capacity=excluded.capacity,
              capacity_avg=excluded.capacity_avg,
              room_type=excluded.room_type,
              location_score=excluded.location_score,
              accessibility_score=excluded.accessibility_score,
              priority=excluded.priority,
              equipment=excluded.equipment,
              source_course_count=excluded.source_course_count;
            """,
            (
                room.get("room_id"),
                room.get("building"),
                int(room.get("floor") or 0) or None,
                str(room.get("room_number") or ""),
                room.get("room_name"),
                int(room.get("capacity") or 0),
                float(room.get("capacity_avg")) if room.get("capacity_avg") not in (None, "") else None,
                room.get("room_type") or "일반강의실",
                int(room.get("location_score") or 3),
                int(room.get("accessibility_score") or 3),
                int(room.get("priority") or 3),
                room.get("equipment") or "projector,computer,whiteboard",
                int(room.get("source_course_count") or 0),
            ),
        )
        conn.commit()
        return True, "강의실 정보가 저장되었습니다."
    except sqlite3.Error as exc:
        conn.rollback()
        return False, f"DB 오류: {exc}"
    finally:
        conn.close()


def delete_room(room_id: str) -> tuple[bool, str]:
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        cur.execute("DELETE FROM reservation_history WHERE room_id = ?;", (room_id,))
        cur.execute("DELETE FROM reservations WHERE room_id = ?;", (room_id,))
        cur.execute("DELETE FROM blocked_schedules WHERE room_id = ?;", (room_id,))
        cur.execute("DELETE FROM rooms WHERE room_id = ?;", (room_id,))
        if cur.rowcount == 0:
            conn.rollback()
            return False, "삭제 실패: 존재하지 않는 강의실입니다."
        conn.commit()
        return True, "강의실과 관련 예약/시간표 데이터가 삭제되었습니다."
    except sqlite3.Error as exc:
        conn.rollback()
        return False, f"DB 오류: {exc}"
    finally:
        conn.close()


# -------------------------
# Conflict/reservation operations
# -------------------------

def get_conflict_details(room_id: str, date: str, start_period: int, end_period: int) -> dict:
    if start_period >= end_period:
        return {"ok": False, "type": "period_error", "message": "종료 교시는 시작 교시보다 커야 합니다."}
    if start_period < 1 or end_period > 13:
        return {"ok": False, "type": "period_error", "message": "예약 가능 교시는 1~12교시입니다."}
    try:
        day = get_day_from_date(date)
    except ValueError:
        return {"ok": False, "type": "date_error", "message": "날짜 형식은 YYYY-MM-DD이어야 합니다."}

    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute("SELECT room_id FROM rooms WHERE room_id = ?;", (room_id,))
    if cur.fetchone() is None:
        conn.close()
        return {"ok": False, "type": "room_error", "message": "존재하지 않는 강의실입니다."}

    cur.execute(
        """
        SELECT course_id, period
        FROM blocked_schedules
        WHERE room_id = ? AND day = ? AND period >= ? AND period < ?
        ORDER BY period ASC;
        """,
        (room_id, day, start_period, end_period),
    )
    blocked_rows = cur.fetchall()

    cur.execute(
        """
        SELECT rv.reservation_id, rv.start_period, rv.end_period, u.user_name, rv.purpose
        FROM reservations rv
        JOIN users u ON rv.user_id = u.user_id
        WHERE rv.room_id = ? AND rv.date = ? AND rv.start_period < ? AND ? < rv.end_period
        ORDER BY rv.start_period ASC;
        """,
        (room_id, date, end_period, start_period),
    )
    reservation_rows = cur.fetchall()
    conn.close()

    if blocked_rows:
        periods = ", ".join(f"{r['period']}교시" for r in blocked_rows)
        courses = ", ".join(sorted(set(str(r["course_id"]) for r in blocked_rows)))
        return {"ok": False, "type": "blocked", "day": day, "periods": periods, "courses": courses, "message": f"기존 수업과 충돌합니다: {day} {periods} / 학수번호 {courses}"}

    if reservation_rows:
        items = [f"예약 #{r['reservation_id']}({r['start_period']}~{r['end_period']}교시, {r['user_name']})" for r in reservation_rows]
        return {"ok": False, "type": "reservation", "day": day, "items": items, "message": "실시간 예약과 충돌합니다: " + "; ".join(items)}

    return {"ok": True, "type": "none", "day": day, "message": "예약 가능한 시간입니다."}


def add_reservation(room_id: str, date: str, start_period: int, end_period: int, user_id: int, purpose: str = "") -> tuple[bool, str, Optional[dict]]:
    if start_period >= end_period:
        return False, "예약 실패: 종료 교시는 시작 교시보다 커야 합니다.", None
    if start_period < 1 or end_period > 13:
        return False, "예약 실패: 예약 가능 교시는 1~12교시입니다.", None
    try:
        user_id = int(user_id)
        day = get_day_from_date(date)
    except Exception:
        return False, "예약 실패: 날짜 또는 user_id 형식이 올바르지 않습니다.", None

    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        cur.execute("SELECT room_id FROM rooms WHERE room_id = ?;", (room_id,))
        if cur.fetchone() is None:
            conn.rollback()
            return False, "예약 실패: 존재하지 않는 강의실입니다.", None
        cur.execute("SELECT user_id FROM users WHERE user_id = ?;", (user_id,))
        if cur.fetchone() is None:
            conn.rollback()
            return False, "예약 실패: 존재하지 않는 user_id입니다.", None

        cur.execute(
            """
            SELECT course_id, period
            FROM blocked_schedules
            WHERE room_id = ? AND day = ? AND period >= ? AND period < ?
            ORDER BY period ASC;
            """,
            (room_id, day, start_period, end_period),
        )
        blocked = cur.fetchone()
        if blocked:
            conn.rollback()
            return False, f"예약 실패: {day}{blocked['period']}교시에 기존 수업({blocked['course_id']})이 있습니다.", None

        cur.execute(
            """
            SELECT reservation_id, start_period, end_period
            FROM reservations
            WHERE room_id = ? AND date = ? AND start_period < ? AND ? < end_period;
            """,
            (room_id, date, end_period, start_period),
        )
        conflict = cur.fetchone()
        if conflict:
            conn.rollback()
            return False, f"예약 실패: 기존 예약 ID {conflict['reservation_id']}번({conflict['start_period']}~{conflict['end_period']}교시)과 시간이 겹칩니다.", None

        cur.execute(
            """
            INSERT INTO reservations (room_id, date, day, start_period, end_period, user_id, purpose)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (room_id, date, day, start_period, end_period, user_id, str(purpose or "").strip()),
        )
        reservation_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO reservation_history
            (reservation_id, action, room_id, date, day, start_period, end_period, user_id, purpose, memo)
            VALUES (?, 'CREATE', ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (reservation_id, room_id, date, day, start_period, end_period, user_id, str(purpose or "").strip(), "예약 생성"),
        )
        conn.commit()
        snapshot = {
            "reservation_id": reservation_id,
            "room_id": room_id,
            "date": date,
            "day": day,
            "start_period": start_period,
            "end_period": end_period,
            "user_id": user_id,
            "purpose": str(purpose or "").strip(),
        }
        return True, f"예약 완료: 예약 ID {reservation_id}", snapshot
    except sqlite3.Error as exc:
        conn.rollback()
        return False, f"DB 오류: {exc}", None
    finally:
        conn.close()


def get_reservation_by_id(reservation_id: int) -> Optional[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT rv.reservation_id, rv.room_id, rv.date, rv.day, rv.start_period, rv.end_period,
               rv.user_id, u.user_name, rv.purpose, rv.created_at
        FROM reservations rv JOIN users u ON rv.user_id = u.user_id
        WHERE rv.reservation_id = ?;
        """,
        (int(reservation_id),),
    )
    row = cur.fetchone()
    conn.close()
    return row


def cancel_reservation(reservation_id: int, actor_user_id: int | None = None, memo: str = "") -> tuple[bool, str, Optional[dict]]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        cur.execute(
            """
            SELECT reservation_id, room_id, date, day, start_period, end_period, user_id, purpose
            FROM reservations WHERE reservation_id = ?;
            """,
            (int(reservation_id),),
        )
        target = cur.fetchone()
        if not target:
            conn.rollback()
            return False, "예약 취소 실패: 해당 예약 ID를 찾을 수 없습니다.", None
        history_user_id = int(actor_user_id) if actor_user_id is not None else int(target["user_id"])
        cur.execute("SELECT user_id FROM users WHERE user_id = ?;", (history_user_id,))
        if cur.fetchone() is None:
            conn.rollback()
            return False, "예약 취소 실패: 존재하지 않는 actor_user_id입니다.", None
        cur.execute(
            """
            INSERT INTO reservation_history
            (reservation_id, action, room_id, date, day, start_period, end_period, user_id, purpose, memo)
            VALUES (?, 'CANCEL', ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                target["reservation_id"], target["room_id"], target["date"], target["day"],
                target["start_period"], target["end_period"], history_user_id,
                target.get("purpose") or "", memo.strip() or "예약 취소",
            ),
        )
        cur.execute("DELETE FROM reservations WHERE reservation_id = ?;", (int(reservation_id),))
        conn.commit()
        return True, f"예약 ID {reservation_id}번이 취소되었습니다.", dict(target)
    except sqlite3.Error as exc:
        conn.rollback()
        return False, f"DB 오류: {exc}", None
    finally:
        conn.close()


def restore_reservation(snapshot: dict, memo: str = "예약 복구") -> tuple[bool, str, Optional[dict]]:
    """Undo/Redo용 복구. 기존 reservation_id가 비어 있으면 같은 ID로 복구를 시도한다."""
    if not snapshot:
        return False, "복구할 예약 정보가 없습니다.", None
    detail = get_conflict_details(snapshot["room_id"], snapshot["date"], int(snapshot["start_period"]), int(snapshot["end_period"]))
    if not detail["ok"]:
        return False, "예약 복구 실패: " + detail["message"], None
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        # 같은 reservation_id가 아직 없으면 가능한 한 원래 ID로 복구한다.
        rid = int(snapshot.get("reservation_id") or 0)
        if rid:
            cur.execute("SELECT reservation_id FROM reservations WHERE reservation_id = ?;", (rid,))
            if cur.fetchone() is None:
                cur.execute(
                    """
                    INSERT INTO reservations
                    (reservation_id, room_id, date, day, start_period, end_period, user_id, purpose)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (rid, snapshot["room_id"], snapshot["date"], snapshot["day"], int(snapshot["start_period"]), int(snapshot["end_period"]), int(snapshot["user_id"]), snapshot.get("purpose") or ""),
                )
            else:
                conn.rollback()
                return False, "예약 복구 실패: 같은 예약 ID가 이미 존재합니다.", None
        else:
            cur.execute(
                """
                INSERT INTO reservations (room_id, date, day, start_period, end_period, user_id, purpose)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (snapshot["room_id"], snapshot["date"], snapshot["day"], int(snapshot["start_period"]), int(snapshot["end_period"]), int(snapshot["user_id"]), snapshot.get("purpose") or ""),
            )
            rid = cur.lastrowid
        cur.execute(
            """
            INSERT INTO reservation_history
            (reservation_id, action, room_id, date, day, start_period, end_period, user_id, purpose, memo)
            VALUES (?, 'RESTORE', ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (rid, snapshot["room_id"], snapshot["date"], snapshot["day"], int(snapshot["start_period"]), int(snapshot["end_period"]), int(snapshot["user_id"]), snapshot.get("purpose") or "", memo),
        )
        conn.commit()
        new_snapshot = dict(snapshot)
        new_snapshot["reservation_id"] = rid
        return True, f"예약 ID {rid}번이 복구되었습니다.", new_snapshot
    except sqlite3.Error as exc:
        conn.rollback()
        return False, f"DB 오류: {exc}", None
    finally:
        conn.close()


def purge_reservations(clear_history: bool = False) -> tuple[bool, str]:
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        cur.execute("DELETE FROM reservations;")
        if clear_history:
            cur.execute("DELETE FROM reservation_history;")
        conn.commit()
        return True, "실시간 예약 내역이 초기화되었습니다."
    except sqlite3.Error as exc:
        conn.rollback()
        return False, f"DB 오류: {exc}"
    finally:
        conn.close()


def get_all_reservations() -> list[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT rv.reservation_id, rv.room_id, rv.date, rv.day, rv.start_period, rv.end_period,
               rv.user_id, u.user_name, u.role, rv.purpose, rv.created_at
        FROM reservations rv JOIN users u ON rv.user_id = u.user_id
        ORDER BY rv.date ASC, rv.start_period ASC, rv.room_id ASC;
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_user_reservations(user_id: int) -> list[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT rv.reservation_id, rv.room_id, rv.date, rv.day, rv.start_period, rv.end_period,
               rv.user_id, u.user_name, rv.purpose, rv.created_at
        FROM reservations rv JOIN users u ON rv.user_id = u.user_id
        WHERE rv.user_id = ?
        ORDER BY rv.date ASC, rv.start_period ASC;
        """,
        (int(user_id),),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_reservations_by_room_date(room_id: str, date: str) -> list[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT rv.reservation_id, rv.room_id, rv.date, rv.day, rv.start_period, rv.end_period,
               rv.user_id, u.user_name, rv.purpose, rv.created_at
        FROM reservations rv JOIN users u ON rv.user_id = u.user_id
        WHERE rv.room_id = ? AND rv.date = ?
        ORDER BY rv.start_period ASC;
        """,
        (room_id, date),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_reservation_history(user_id: int | None = None, room_id: str | None = None, date: str | None = None, limit: int = 200) -> list[dict]:
    conditions = []
    params: list[object] = []
    if user_id is not None:
        conditions.append("h.user_id = ?")
        params.append(int(user_id))
    if room_id:
        conditions.append("h.room_id = ?")
        params.append(room_id)
    if date:
        conditions.append("h.date = ?")
        params.append(date)
    where_sql = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(int(limit))
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT h.history_id, h.reservation_id, h.action, h.room_id, h.date, h.day,
               h.start_period, h.end_period, h.user_id, u.user_name, h.purpose,
               h.action_at, h.memo
        FROM reservation_history h JOIN users u ON h.user_id = u.user_id
        {where_sql}
        ORDER BY h.action_at DESC, h.history_id DESC
        LIMIT ?;
        """,
        params,
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# -------------------------
# Search/recommendation/statistics
# -------------------------

def get_available_rooms(date: str, start_period: int, end_period: int, min_capacity: int = 0) -> list[dict]:
    try:
        day = get_day_from_date(date)
    except ValueError:
        return []
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.*
        FROM rooms r
        WHERE r.capacity >= ?
          AND NOT EXISTS (
              SELECT 1 FROM blocked_schedules b
              WHERE b.room_id = r.room_id AND b.day = ? AND b.period >= ? AND b.period < ?
          )
          AND NOT EXISTS (
              SELECT 1 FROM reservations rv
              WHERE rv.room_id = r.room_id AND rv.date = ?
                AND rv.start_period < ? AND ? < rv.end_period
          )
        ORDER BY r.priority DESC, r.capacity ASC, r.room_id ASC;
        """,
        (int(min_capacity), day, int(start_period), int(end_period), date, int(end_period), int(start_period)),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_blocked_schedules(day: str | None = None, room_id: str | None = None, building: str | None = None) -> list[dict]:
    conditions = []
    params: list[object] = []
    if day and day != "전체":
        conditions.append("b.day = ?")
        params.append(day)
    if room_id:
        conditions.append("b.room_id = ?")
        params.append(room_id)
    if building and building != "전체":
        conditions.append("r.building = ?")
        params.append(building)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT b.blocked_id, b.course_id, b.room_id, r.building, r.floor,
               b.day, b.period, b.capacity, b.source_row
        FROM blocked_schedules b JOIN rooms r ON b.room_id = r.room_id
        {where}
        ORDER BY CASE b.day WHEN '월' THEN 1 WHEN '화' THEN 2 WHEN '수' THEN 3 WHEN '목' THEN 4 WHEN '금' THEN 5 WHEN '토' THEN 6 ELSE 7 END,
                 b.period ASC, b.room_id ASC;
        """,
        params,
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def search_available_room_slots(date: str, duration: int, min_capacity: int = 1, start_min: int = 1, end_max: int = 13) -> list[dict]:
    if duration < 1 or start_min < 1 or end_max > 13 or start_min >= end_max:
        return []
    candidates = []
    for start in range(start_min, end_max - duration + 1):
        end = start + duration
        for row in get_available_rooms(date, start, end, min_capacity):
            item = dict(row)
            item["start_period"] = start
            item["end_period"] = end
            candidates.append(item)
    return candidates


def recommend_alternative_slots(room_id: str, date: str, duration: int, min_start: int = 1, max_end: int = 13, limit: int = 8) -> list[dict]:
    alternatives = []
    if duration < 1:
        return alternatives
    for start in range(min_start, max_end - duration + 1):
        end = start + duration
        detail = get_conflict_details(room_id, date, start, end)
        if detail["ok"]:
            alternatives.append({"room_id": room_id, "date": date, "start_period": start, "end_period": end})
        if len(alternatives) >= limit:
            break
    return alternatives


def add_recurring_reservations(room_id: str, start_date: str, end_date: str, selected_days: Iterable[str], start_period: int, end_period: int, user_id: int, purpose: str = ""):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return [], [{"date": "-", "ok": False, "message": "날짜 형식 오류"}]
    if end_dt < start_dt:
        return [], [{"date": "-", "ok": False, "message": "종료일은 시작일보다 늦어야 합니다."}]
    days = set(selected_days)
    successes: list[dict] = []
    failures: list[dict] = []
    cur_dt = start_dt
    while cur_dt <= end_dt:
        date_text = cur_dt.strftime("%Y-%m-%d")
        day = get_day_from_date(date_text)
        if day in days:
            ok, message, snapshot = add_reservation(room_id, date_text, start_period, end_period, user_id, purpose)
            record = {"date": date_text, "day": day, "ok": ok, "message": message, "snapshot": snapshot}
            if ok:
                successes.append(record)
            else:
                failures.append(record)
        cur_dt += timedelta(days=1)
    return successes, failures



def get_current_period(now: datetime | None = None) -> int | None:
    """한국 시간 기준 현재 교시를 계산한다.

    1교시를 09:00~10:00, 12교시를 20:00~21:00으로 본다.
    수업 시간대 밖이면 None을 반환한다.
    """
    if now is None:
        now = datetime.now(ZoneInfo("Asia/Seoul"))
    hour = int(now.hour)
    if 9 <= hour <= 20:
        return hour - 8
    return None


def get_current_availability_summary() -> dict:
    """현재 한국 시간 기준 전체 강의실 중 즉시 사용 가능한 강의실 수를 반환한다."""
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    date_text = now.strftime("%Y-%m-%d")
    day = get_day_from_date(date_text)
    period = get_current_period(now)

    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rooms;")
    total_rooms = int(cur.fetchone()[0])
    conn.close()

    if period is None:
        available = total_rooms
        unavailable = 0
    else:
        available = len(get_available_rooms(date_text, period, period + 1, min_capacity=0))
        unavailable = max(total_rooms - available, 0)

    return {
        "total_rooms": total_rooms,
        "available_now": available,
        "unavailable_now": unavailable,
        "current_date": date_text,
        "current_day": day,
        "current_time": now.strftime("%H:%M"),
        "current_period": period,
        "is_class_time": period is not None,
    }

def get_counts() -> dict:
    conn = connect_db()
    cur = conn.cursor()
    counts = {}
    for table in ["rooms", "blocked_schedules", "users", "reservations", "reservation_history"]:
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        counts[table] = cur.fetchone()[0]
    conn.close()
    return counts


def get_room_usage_stats() -> list[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.room_id, r.building, r.capacity, COUNT(rv.reservation_id) AS reservation_count
        FROM rooms r LEFT JOIN reservations rv ON r.room_id = rv.room_id
        GROUP BY r.room_id
        ORDER BY reservation_count DESC, r.room_id ASC;
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_building_usage_stats() -> list[dict]:
    conn = connect_db(row_factory=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.building, COUNT(rv.reservation_id) AS reservation_count
        FROM rooms r LEFT JOIN reservations rv ON r.room_id = rv.room_id
        GROUP BY r.building
        ORDER BY reservation_count DESC, r.building ASC;
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    ensure_seed_data()
    print("DB 준비 완료")
    print(get_counts())

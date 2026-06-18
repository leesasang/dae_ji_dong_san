import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Streamlit, withStreamlitConnection } from 'streamlit-component-lib';
import {
  BookOpen, Calendar, CheckCircle2, Clock, Database, History, LogOut,
  MapPin, RefreshCcw, RotateCcw, RotateCw, Search, ShieldCheck,
  Sparkles, Users, XCircle, Building2, Layers, Trash2, Gauge, Filter
} from 'lucide-react';
import './style.css';

const KOREAN_WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];
const PERIODS = Array.from({ length: 12 }, (_, i) => i + 1);

function emit(type, payload = {}) {
  Streamlit.setComponentValue({ type, event_id: `${type}-${Date.now()}-${Math.random()}`, ...payload });
}

function normalizeEquipment(text) {
  if (!text) return ['projector', 'computer', 'whiteboard'];
  return String(text).split(',').map((v) => v.trim()).filter(Boolean);
}

function dateToKoreanDay(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  return KOREAN_WEEKDAYS[d.getDay()];
}

function hasPeriodConflict(res, start, end) {
  return Number(res.start_period) < Number(end) && Number(start) < Number(res.end_period);
}

function isRoomAvailable(room, date, start, end, blocked, reservations) {
  const day = dateToKoreanDay(date);
  const blockedHit = blocked.some((b) => b.room_id === room.room_id && b.day === day && Number(b.period) >= Number(start) && Number(b.period) < Number(end));
  if (blockedHit) return { ok: false, reason: '기존 수업' };
  const rvHit = reservations.some((r) => r.room_id === room.room_id && r.date === date && hasPeriodConflict(r, start, end));
  if (rvHit) return { ok: false, reason: '예약됨' };
  return { ok: true, reason: '가능' };
}

function scoreRoom(room, minCapacity) {
  const waste = Math.max(0, Number(room.capacity) - Number(minCapacity || 0));
  return Number(room.priority || 3) * 10 + Number(room.accessibility_score || 3) + Number(room.location_score || 3) - Math.min(waste / 10, 15);
}

function computeAvailableRooms({ rooms, blocked, reservations, date, start, end, minCapacity, building, query, sortBy }) {
  let result = rooms
    .filter((r) => Number(r.capacity || 0) >= Number(minCapacity || 0))
    .filter((r) => building === '전체' || r.building === building)
    .filter((r) => {
      const q = String(query || '').trim().toLowerCase();
      if (!q) return true;
      return `${r.room_id} ${r.room_name} ${r.room_number} ${r.building}`.toLowerCase().includes(q);
    })
    .map((room) => ({ ...room, availability: isRoomAvailable(room, date, start, end, blocked, reservations), score: scoreRoom(room, minCapacity) }))
    .filter((r) => r.availability.ok);

  result = [...result].sort((a, b) => {
    if (sortBy === 'capacity') return Number(a.capacity) - Number(b.capacity) || a.room_id.localeCompare(b.room_id);
    if (sortBy === 'priority') return Number(b.priority || 0) - Number(a.priority || 0) || Number(a.capacity) - Number(b.capacity);
    if (sortBy === 'score') return Number(b.score) - Number(a.score) || Number(a.capacity) - Number(b.capacity);
    return a.room_id.localeCompare(b.room_id);
  });
  return result;
}

function Notice({ notice }) {
  if (!notice || !notice.message) return null;
  return <div className={`notice ${notice.type || 'info'}`}>{notice.message}</div>;
}

function TopHeader({ user, onLogout, undoCount, redoCount }) {
  const roleLabel = user?.role === 'professor' ? '교수' : user?.role === 'student' ? '학생' : '사용자';
  return (
    <header className="top-header">
      <div className="brand-wrap">
        <div className="brand-icon"><BookOpen size={24} /></div>
        <div>
          <h1>ClassFit</h1>
          <p>Gachon University Classroom Reservation System</p>
        </div>
      </div>
      <div className="header-actions">
        <button className="history-btn" onClick={() => emit('undo')} disabled={!undoCount}><RotateCcw size={15} /> 실행 취소 <b>{undoCount}</b></button>
        <button className="history-btn" onClick={() => emit('redo')} disabled={!redoCount}><RotateCw size={15} /> 다시 실행 <b>{redoCount}</b></button>
        <div className="user-pill">
          <span className="role-dot" />
          <div>
            <strong>{user?.user_name}</strong>
            <small>{roleLabel} · {user?.login_id || user?.student_id || user?.user_name}</small>
          </div>
        </div>
        <button className="logout" onClick={onLogout}><LogOut size={16} /> 로그아웃</button>
      </div>
    </header>
  );
}

function LoginGate({ payload }) {
  const [identifier, setIdentifier] = useState('');
  const counts = payload.counts || {};
  return (
    <main className="login-page">
      <div className="login-hero">
        <div className="hero-badge"><Sparkles size={16} /> Algorithm Project</div>
        <h1>ClassFit</h1>
        <p>가천대학교 강의실 예약 및 시간표 충돌 검사 시스템</p>
      </div>
      <section className="login-card">
        <div className="login-card-head">
          <div className="login-icon"><ShieldCheck size={28} /></div>
          <div>
            <h2>가천대학교 통합 로그인</h2>
            <p>학번 또는 교수 학수번호만 입력하세요.</p>
          </div>
        </div>
        <form className="login-form" onSubmit={(e) => { e.preventDefault(); emit('login', { identifier }); }}>
          <label>학번 / 교수 학수번호</label>
          <input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="예: 202430001 또는 08095006"
            autoFocus
          />
          <button type="submit" className="primary full">로그인</button>
        </form>
        <Notice notice={payload.notice} />
        <div className="sample-box">
          <b>시연용 계정</b>
          <div className="sample-row">
            <button onClick={() => setIdentifier('202430001')}>학생 202430001</button>
            <button onClick={() => setIdentifier('202630001')}>학생 202630001</button>
            <button onClick={() => setIdentifier('08095006')}>교수 08095006</button>
          </div>
        </div>
        <div className="db-mini-grid">
          <span>강의실 <b>{counts.rooms ?? 0}</b></span>
          <span>수업차단 <b>{counts.blocked_schedules ?? 0}</b></span>
          <span>사용자 <b>{counts.users ?? 0}</b></span>
        </div>
      </section>
      <p className="footer-note">SQLite DB 기반 실시간 예약 저장 · 트랜잭션 기반 중복 예약 방지</p>
    </main>
  );
}

function StatCards({ counts }) {
  const items = [
    { label: '강의실', value: counts.rooms || 0, icon: Building2 },
    { label: '기존 수업', value: counts.blocked_schedules || 0, icon: Calendar },
    { label: '실시간 예약', value: counts.reservations || 0, icon: CheckCircle2 },
    { label: '예약 이력', value: counts.reservation_history || 0, icon: History },
  ];
  return <div className="stats-grid">{items.map((it) => <div className="stat-card" key={it.label}><it.icon size={21} /><div><b>{it.value.toLocaleString()}</b><span>{it.label}</span></div></div>)}</div>;
}

function RoomCard({ room, date, start, end, purpose }) {
  const equipment = normalizeEquipment(room.equipment);
  return (
    <article className="room-card">
      <div className="room-top">
        <div>
          <h3>{room.room_name || room.room_id}</h3>
          <p><MapPin size={14} /> {room.building} · {room.floor || '-'}층 · {room.room_id}</p>
        </div>
        <span className="score-badge">Score {Math.round(room.score)}</span>
      </div>
      <div className="room-meta">
        <span><Users size={14} /> {room.capacity}명</span>
        <span><Layers size={14} /> {room.room_type || '일반강의실'}</span>
        <span><Gauge size={14} /> 우선순위 {room.priority || 3}</span>
      </div>
      <div className="equip-row">{equipment.slice(0, 4).map((e) => <em key={e}>{e}</em>)}</div>
      <button className="primary" onClick={() => emit('reserve', { room_id: room.room_id, date, start_period: Number(start), end_period: Number(end), purpose })}>예약 신청</button>
    </article>
  );
}

function ReservationForm({ payload }) {
  const rooms = payload.rooms || [];
  const blocked = payload.blocked || [];
  const reservations = payload.reservations || [];
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [start, setStart] = useState(1);
  const [end, setEnd] = useState(3);
  const [minCapacity, setMinCapacity] = useState(1);
  const [building, setBuilding] = useState('전체');
  const [query, setQuery] = useState('');
  const [sortBy, setSortBy] = useState('score');
  const [purpose, setPurpose] = useState('프로젝트 회의');
  const buildings = useMemo(() => ['전체', ...Array.from(new Set(rooms.map((r) => r.building).filter(Boolean))).sort()], [rooms]);
  const available = useMemo(() => computeAvailableRooms({ rooms, blocked, reservations, date, start, end, minCapacity, building, query, sortBy }), [rooms, blocked, reservations, date, start, end, minCapacity, building, query, sortBy]);

  return (
    <section className="two-col-layout">
      <aside className="filter-card">
        <div className="section-title"><Filter size={18} /><h2>강의실 추천 조건</h2></div>
        <label>날짜</label><input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <div className="field-pair">
          <div><label>시작 교시</label><select value={start} onChange={(e) => setStart(Number(e.target.value))}>{PERIODS.map((p) => <option key={p} value={p}>{p}교시</option>)}</select></div>
          <div><label>종료 교시</label><select value={end} onChange={(e) => setEnd(Number(e.target.value))}>{PERIODS.filter((p) => p > start).concat([13]).map((p) => <option key={p} value={p}>{p === 13 ? '12교시 종료' : `${p}교시 전`}</option>)}</select></div>
        </div>
        <label>최소 인원</label><input type="number" min="1" value={minCapacity} onChange={(e) => setMinCapacity(Number(e.target.value))} />
        <label>건물</label><select value={building} onChange={(e) => setBuilding(e.target.value)}>{buildings.map((b) => <option key={b} value={b}>{b}</option>)}</select>
        <label>검색</label><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="강의실명, 번호, 건물 검색" />
        <label>정렬</label><select value={sortBy} onChange={(e) => setSortBy(e.target.value)}><option value="score">추천 점수순</option><option value="priority">우선순위순</option><option value="capacity">정원 적합순</option><option value="id">강의실 ID순</option></select>
        <label>이용 목적</label><input value={purpose} onChange={(e) => setPurpose(e.target.value)} />
        <div className="mini-info"><Clock size={15} /> {dateToKoreanDay(date)}요일 {start}~{end}교시 · 후보 {available.length}개</div>
      </aside>
      <div className="results-panel">
        <div className="panel-head"><div><h2>추천 가능한 강의실</h2><p>화면 계산 후 실제 예약 시 DB에서 한 번 더 충돌 검사를 수행합니다.</p></div><span>{available.length} rooms</span></div>
        {Number(start) >= Number(end) ? <div className="empty-card">종료 교시는 시작 교시보다 커야 합니다.</div> : available.length === 0 ? <div className="empty-card">조건에 맞는 빈 강의실이 없습니다. 시간 또는 인원을 조정하세요.</div> : <div className="room-grid">{available.slice(0, 24).map((room) => <RoomCard key={room.room_id} room={room} date={date} start={start} end={end} purpose={purpose} />)}</div>}
      </div>
    </section>
  );
}

function MyReservations({ payload, professor = false }) {
  const rows = professor ? (payload.reservations || []) : (payload.userReservations || []);
  return (
    <section className="panel">
      <div className="panel-head"><div><h2>{professor ? '전체 실시간 예약' : '내 예약 내역'}</h2><p>취소 시 reservations에서 삭제되고 reservation_history에 CANCEL 기록이 남습니다.</p></div><span>{rows.length}건</span></div>
      {rows.length === 0 ? <div className="empty-card">예약 내역이 없습니다.</div> : <div className="table-wrap"><table><thead><tr><th>ID</th><th>강의실</th><th>날짜</th><th>시간</th><th>예약자</th><th>목적</th><th></th></tr></thead><tbody>{rows.map((r) => <tr key={r.reservation_id}><td>#{r.reservation_id}</td><td>{r.room_id}</td><td>{r.date} ({r.day})</td><td>{r.start_period}~{r.end_period}교시</td><td>{r.user_name}</td><td>{r.purpose || '-'}</td><td><button className="danger small" onClick={() => emit('cancel', { reservation_id: r.reservation_id })}><Trash2 size={14}/> 취소</button></td></tr>)}</tbody></table></div>}
    </section>
  );
}

function StatusBoard({ payload }) {
  const rooms = payload.rooms || [];
  const blocked = payload.blocked || [];
  const reservations = payload.reservations || [];
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [building, setBuilding] = useState('전체');
  const buildings = useMemo(() => ['전체', ...Array.from(new Set(rooms.map((r) => r.building).filter(Boolean))).sort()], [rooms]);
  const filteredRooms = rooms.filter((r) => building === '전체' || r.building === building).slice(0, 25);
  const day = dateToKoreanDay(date);
  function state(roomId, p) {
    if (blocked.some((b) => b.room_id === roomId && b.day === day && Number(b.period) === p)) return 'blocked';
    if (reservations.some((r) => r.room_id === roomId && r.date === date && Number(r.start_period) <= p && p < Number(r.end_period))) return 'reserved';
    return 'free';
  }
  return (
    <section className="panel">
      <div className="panel-head"><div><h2>실시간 현황판</h2><p>기존 수업과 실시간 예약을 교시 단위로 확인합니다.</p></div><div className="head-controls"><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /><select value={building} onChange={(e) => setBuilding(e.target.value)}>{buildings.map((b) => <option key={b}>{b}</option>)}</select></div></div>
      <div className="legend"><span><i className="free"/>가능</span><span><i className="blocked"/>기존 수업</span><span><i className="reserved"/>실시간 예약</span></div>
      <div className="board-wrap"><table className="board"><thead><tr><th>강의실</th>{PERIODS.map((p) => <th key={p}>{p}</th>)}</tr></thead><tbody>{filteredRooms.map((r) => <tr key={r.room_id}><td><b>{r.room_id}</b><small>{r.capacity}명</small></td>{PERIODS.map((p) => <td key={p}><span className={`cell ${state(r.room_id, p)}`} title={`${r.room_id} ${p}교시`} /></td>)}</tr>)}</tbody></table></div>
    </section>
  );
}

function HistoryView({ payload }) {
  const rows = payload.history || [];
  return (
    <section className="panel">
      <div className="panel-head"><div><h2>예약 이력</h2><p>CREATE / CANCEL / RESTORE 기록을 DB history 테이블에서 조회합니다.</p></div><span>{rows.length}건</span></div>
      {rows.length === 0 ? <div className="empty-card">아직 이력이 없습니다.</div> : <div className="table-wrap"><table><thead><tr><th>이력ID</th><th>Action</th><th>예약ID</th><th>강의실</th><th>날짜</th><th>시간</th><th>사용자</th><th>메모</th></tr></thead><tbody>{rows.map((h) => <tr key={h.history_id}><td>#{h.history_id}</td><td><span className={`action ${String(h.action).toLowerCase()}`}>{h.action}</span></td><td>{h.reservation_id || '-'}</td><td>{h.room_id}</td><td>{h.date}</td><td>{h.start_period}~{h.end_period}</td><td>{h.user_name}</td><td>{h.memo || '-'}</td></tr>)}</tbody></table></div>}
    </section>
  );
}

function ProfessorTools({ payload }) {
  return (
    <section className="panel danger-zone">
      <div className="panel-head"><div><h2>교수/관리용 데이터 제어</h2><p>시연 중 예약 데이터를 초기화할 수 있습니다. 기존 수업 시간표와 사용자 DB는 유지됩니다.</p></div></div>
      <button className="danger" onClick={() => { if (confirm('실시간 예약을 모두 초기화할까요?')) emit('reset_reservations', { clear_history: false }); }}><RefreshCcw size={16}/> 실시간 예약 초기화</button>
    </section>
  );
}

function App({ args }) {
  const payload = args?.payload || {};
  const user = payload.user;
  const [tab, setTab] = useState('reserve');
  useEffect(() => { Streamlit.setFrameHeight(document.documentElement.scrollHeight + 20); });
  useEffect(() => { Streamlit.setFrameHeight(document.documentElement.scrollHeight + 20); }, [payload, tab]);

  if (!user) return <LoginGate payload={payload} />;
  const isProfessor = user.role === 'professor';
  const tabs = isProfessor
    ? [['reserve', '빈 강의실 찾기'], ['board', '실시간 현황판'], ['reservations', '전체 예약'], ['history', '예약 이력'], ['tools', '데이터 관리']]
    : [['reserve', '예약하기'], ['mine', '내 예약'], ['board', '실시간 현황판'], ['history', '예약 이력']];

  return (
    <div className="app-shell">
      <TopHeader user={user} onLogout={() => emit('logout')} undoCount={payload.undoCount || 0} redoCount={payload.redoCount || 0} />
      <main className="content-shell">
        <Notice notice={payload.notice} />
        <StatCards counts={payload.counts || {}} />
        <nav className="tabs">{tabs.map(([id, label]) => <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{label}</button>)}</nav>
        {tab === 'reserve' && <ReservationForm payload={payload} />}
        {tab === 'mine' && <MyReservations payload={payload} />}
        {tab === 'reservations' && <MyReservations payload={payload} professor />}
        {tab === 'board' && <StatusBoard payload={payload} />}
        {tab === 'history' && <HistoryView payload={payload} />}
        {tab === 'tools' && <ProfessorTools payload={payload} />}
      </main>
    </div>
  );
}

const ConnectedApp = withStreamlitConnection(App);
createRoot(document.getElementById('root')).render(<ConnectedApp />);

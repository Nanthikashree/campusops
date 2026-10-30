import { useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";
import Badge from "../components/Badge.jsx";
import { fmtTime } from "../util.js";

const MANAGERS = ["facilities_admin", "department_manager", "system_admin"];
const KIND_TONE = { class: "blue", exam: "red", event: "amber", meeting: "gray" };
const pad = (n) => String(n).padStart(2, "0");
const dateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

export default function Bookings() {
  const { call, user } = useAuth();
  const isManager = MANAGERS.includes(user.role);
  const [date, setDate] = useState(dateStr(new Date(Date.now() + 86400000)));
  const [from, setFrom] = useState("11:00");
  const [to, setTo] = useState("12:00");
  const [people, setPeople] = useState(30);
  const [kind, setKind] = useState("class");
  const [title, setTitle] = useState("");
  const [roomId, setRoomId] = useState("");
  const [allRooms, setAllRooms] = useState([]);
  const [free, setFree] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [ready, setReady] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(null);
  const [busy, setBusy] = useState(false);

  const start = `${date}T${from}:00`;
  const end = `${date}T${to}:00`;

  useEffect(() => {
    Promise.all([call("/api/rooms"), call("/api/bookings")])
      .then(([rooms, all]) => {
        setAllRooms(rooms.filter((r) => ["classroom", "lab", "hall"].includes(r.type) && r.status === "available"));
        const next = all.find((b) => new Date(b.start) >= new Date()) || all[0];
        if (next) setDate(next.start.slice(0, 10)); // jump to the day that has bookings
      })
      .catch((e) => setError(e.message))
      .finally(() => setReady(true));
  }, []);

  const loadDay = () => call(`/api/bookings?date=${date}`).then(setBookings).catch((e) => setError(e.message));
  useEffect(() => {
    if (ready) loadDay();
  }, [date, ready]);

  async function fetchFree() {
    const q = new URLSearchParams({ start, end, attendees: String(Number(people) || 0) });
    setFree(await call(`/api/rooms/availability?${q}`));
  }

  async function findFree(e) {
    e.preventDefault();
    setError("");
    setMsg("");
    setConflict(null);
    setBusy(true);
    try {
      await fetchFree();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function book(room) {
    if (title.trim().length < 3) {
      setError("Enter a title for the booking first (at least 3 letters).");
      return;
    }
    setError("");
    setMsg("");
    setConflict(null);
    setBusy(true);
    try {
      await call("/api/bookings", {
        method: "POST",
        body: { room_id: room.id, title: title.trim(), kind, start_time: start, end_time: end, attendees: Number(people) || 0 },
      });
      setMsg(`Booked ${room.name} from ${from} to ${to}.`);
      setTitle("");
      await loadDay();
      if (free) await fetchFree().catch(() => {});
    } catch (err) {
      setError(err.message);
      if (err.data && (err.data.conflicts || err.data.alternatives)) setConflict(err.data);
    } finally {
      setBusy(false);
    }
  }

  async function cancel(id) {
    setError("");
    setMsg("");
    try {
      await call(`/api/bookings/${id}/cancel`, { method: "POST" });
      setMsg("Booking cancelled.");
      await loadDay();
      if (free) await fetchFree().catch(() => {});
    } catch (err) {
      setError(err.message);
    }
  }

  const selected = allRooms.find((r) => String(r.id) === String(roomId));
  const kinds = ["class", "event", "meeting", ...(isManager ? ["exam"] : [])];

  return (
    <div>
      <div className="page-head">
        <h2>Room bookings</h2>
        <div className="muted">Check availability, book a room, and see clashes before they happen.</div>
      </div>

      <form className="card" onSubmit={findFree}>
        <div className="row">
          <div><label>Date</label><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></div>
          <div><label>From</label><input type="time" value={from} onChange={(e) => setFrom(e.target.value)} /></div>
          <div><label>To</label><input type="time" value={to} onChange={(e) => setTo(e.target.value)} /></div>
          <div><label>People</label><input type="number" min="0" max="500" value={people} onChange={(e) => setPeople(e.target.value)} /></div>
        </div>
        <div className="row">
          <div><label>Title</label><input value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Maths revision class" /></div>
          <div>
            <label>Type</label>
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              {kinds.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </div>
          <div>
            <label>Room (optional)</label>
            <select value={roomId} onChange={(e) => setRoomId(e.target.value)}>
              <option value="">Any room: show free rooms</option>
              {allRooms.map((r) => <option key={r.id} value={r.id}>{r.building} - {r.name} (seats {r.capacity})</option>)}
            </select>
          </div>
        </div>
        <button type="submit" disabled={busy}>Find free rooms</button>
        {selected && (
          <button type="button" className="ghost" disabled={busy} onClick={() => book(selected)}>
            Book {selected.name}
          </button>
        )}
      </form>

      {msg && <div className="notice">{msg}</div>}
      {error && !conflict && <p className="error">{error}</p>}

      {conflict && (
        <div className="notice">
          <b>{error}</b>
          {(conflict.conflicts || []).map((c) => (
            <div className="small" key={c.id}>Clash: {c.title} ({fmtTime(c.start)} to {fmtTime(c.end)}, booked by {c.booked_by})</div>
          ))}
          {conflict.alternatives && conflict.alternatives.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div className="muted">Alternative rooms</div>
              {conflict.alternatives.map((a) => (
                <div className="alt" key={a.room_id}>
                  <div>
                    <b>{a.name}</b> <span className="small">{a.building} · seats {a.capacity} · score {a.score}</span>
                    <div className="small">{a.why.join("; ")}</div>
                  </div>
                  <button disabled={busy} onClick={() => book({ id: a.room_id, name: a.name })}>Book this instead</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {free && (
        <div className="card">
          <h3>Free rooms ({free.length})</h3>
          {free.length === 0 ? (
            <p className="muted">No room is free for that time and group size.</p>
          ) : (
            <table className="table">
              <thead><tr><th>Room</th><th>Building</th><th>Type</th><th>Seats</th><th></th></tr></thead>
              <tbody>
                {free.map((r) => (
                  <tr key={r.id}>
                    <td>{r.name}</td><td>{r.building}</td><td>{r.type}</td><td>{r.capacity}</td>
                    <td><button disabled={busy} onClick={() => book(r)}>Book</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      <div className="card">
        <h3>Bookings on {date}</h3>
        {bookings.length === 0 ? (
          <p className="muted">Nothing is booked on this day.</p>
        ) : (
          <table className="table">
            <thead><tr><th>Time</th><th>Room</th><th>Title</th><th>Type</th><th>People</th><th>Booked by</th><th></th></tr></thead>
            <tbody>
              {bookings.map((b) => (
                <tr key={b.id}>
                  <td>{fmtTime(b.start)} to {fmtTime(b.end)}</td>
                  <td>{b.building} · {b.room}</td>
                  <td>{b.title}{b.note && <div className="small">{b.note}</div>}</td>
                  <td><Badge tone={KIND_TONE[b.kind]}>{b.kind}</Badge></td>
                  <td>{b.attendees}</td>
                  <td>{b.booked_by}</td>
                  <td>{(isManager || b.booked_by === user.name) && <button className="ghost" onClick={() => cancel(b.id)}>Cancel</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
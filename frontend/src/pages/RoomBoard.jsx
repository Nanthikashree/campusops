import { useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";
import Badge from "../components/Badge.jsx";
import { fmtTime } from "../util.js";

const BOOKABLE = ["classroom", "lab", "hall"];
const KIND_TONE = { class: "blue", exam: "red", event: "amber", meeting: "gray" };
const pad = (n) => String(n).padStart(2, "0");
const dateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const overlaps = (a, b) => new Date(a.start) < new Date(b.end) && new Date(a.end) > new Date(b.start);

export default function RoomBoard() {
  const { call } = useAuth();
  const [rooms, setRooms] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [date, setDate] = useState(dateStr(new Date(Date.now() + 86400000)));
  const [ready, setReady] = useState(false);
  const [building, setBuilding] = useState("all");
  const [type, setType] = useState("all");
  const [pickedId, setPickedId] = useState(null);
  const [hoverId, setHoverId] = useState(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadRooms = () =>
    call("/api/rooms").then((r) => setRooms(r.filter((x) => BOOKABLE.includes(x.type)))).catch((e) => setError(e.message));
  const loadDay = (d) => call(`/api/bookings?date=${d}`).then(setBookings).catch((e) => setError(e.message));

  useEffect(() => {
    Promise.all([call("/api/rooms"), call("/api/bookings")])
      .then(([r, all]) => {
        setRooms(r.filter((x) => BOOKABLE.includes(x.type)));
        const next = all.find((b) => new Date(b.start) >= new Date()) || all[0];
        if (next) setDate(next.start.slice(0, 10)); // jump to the day that has bookings
      })
      .catch((e) => setError(e.message))
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    if (ready) loadDay(date);
  }, [date, ready]);

  const picked = bookings.find((b) => b.id === pickedId) || null;
  const roomById = (id) => rooms.find((r) => r.id === id);

  // Why a booking cannot go into a room, or null if it can.
  function reasonNot(room, b, list = bookings) {
    if (room.id === b.room_id) return "Already here";
    if (room.status !== "available") return `${room.name} is out of service`;
    if (b.attendees > room.capacity) return `${room.name} seats only ${room.capacity}, but ${b.attendees} people are coming`;
    const clash = list.find((x) => x.room_id === room.id && x.id !== b.id && overlaps(x, b));
    if (clash) return `${room.name} is busy then: ${clash.title}`;
    return null;
  }

  function score(room, b) {
    const from = roomById(b.room_id);
    let s = 0;
    if (from && room.type === from.type) s += 30;
    if (from && room.building === from.building) s += 20;
    s -= Math.min(Math.floor((room.capacity - b.attendees) / 5), 20);
    return s;
  }

  async function move(b, room) {
    const why = reasonNot(room, b);
    if (why) {
      setError(why);
      setMsg("");
      return;
    }
    setBusy(true);
    setError("");
    setMsg("");
    try {
      await call(`/api/bookings/${b.id}/move`, { method: "POST", body: { room_id: room.id } });
      setMsg(`Moved "${b.title}" to ${room.building} - ${room.name}.`);
      setPickedId(null);
      await loadDay(date);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
      setHoverId(null);
    }
  }

  async function moveAll(room) {
    const mine = bookings.filter((b) => b.room_id === room.id);
    if (mine.length === 0) return;
    if (!window.confirm(`Move all ${mine.length} booking(s) out of ${room.name} to the best available rooms?`)) return;
    mine.sort((a, b) => Number(a.kind !== "exam") - Number(b.kind !== "exam") || new Date(a.start) - new Date(b.start));
    setBusy(true);
    setError("");
    setMsg("");
    let list = [...bookings];
    const done = [];
    const failed = [];
    for (const b of mine) {
      const options = rooms.filter((r) => !reasonNot(r, b, list));
      if (options.length === 0) {
        failed.push(`${b.title} (no free room fits)`);
        continue;
      }
      options.sort((x, y) => score(y, b) - score(x, b) || x.id - y.id);
      const target = options[0];
      try {
        await call(`/api/bookings/${b.id}/move`, { method: "POST", body: { room_id: target.id } });
        list = list.map((x) => (x.id === b.id ? { ...x, room_id: target.id } : x));
        done.push(`${b.title} to ${target.name}`);
      } catch (e) {
        failed.push(`${b.title} (${e.message})`);
      }
    }
    setMsg(done.length ? `Moved: ${done.join("; ")}.` : "");
    setError(failed.length ? `Could not move: ${failed.join("; ")}` : "");
    setBusy(false);
    await loadDay(date);
  }

  async function setStatus(room, status) {
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const r = await call(`/api/rooms/${room.id}/status`, { method: "POST", body: { status } });
      setMsg(status === "unusable" ? `${room.name} is out of service. ${r.summary}.` : `${room.name} is available again.`);
      await loadRooms();
      await loadDay(date);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const buildings = [...new Set(rooms.map((r) => r.building))];
  const shown = rooms.filter(
    (r) => (building === "all" || r.building === building) && (type === "all" || r.type === type)
  );
  const countFree = picked ? shown.filter((r) => !reasonNot(r, picked)).length : 0;

  return (
    <div>
      <div className="page-head">
        <h2>Room board</h2>
        <div className="muted">
          Drag a booking onto another room for an immediate move. Green rooms can take it, grey rooms can not.
        </div>
      </div>

      <div className="card">
        <div className="row">
          <div><label>Day</label><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></div>
          <div>
            <label>Building</label>
            <select value={building} onChange={(e) => setBuilding(e.target.value)}>
              <option value="all">All buildings</option>
              {buildings.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label>Room type</label>
            <select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="all">All types</option>
              <option value="classroom">Classrooms</option>
              <option value="lab">Labs</option>
              <option value="hall">Halls</option>
            </select>
          </div>
        </div>
        {picked ? (
          <div className="notice">
            Selected: <b>{picked.title}</b> ({fmtTime(picked.start)} to {fmtTime(picked.end)}, {picked.attendees} people).{" "}
            {countFree} room(s) can take it.{" "}
            <button className="ghost" onClick={() => setPickedId(null)}>Clear selection</button>
          </div>
        ) : (
          <div className="small">Tip: you can also click a booking to select it, then press "Move here" on a green room.</div>
        )}
      </div>

      {msg && <div className="notice">{msg}</div>}
      {error && <div className="notice error">{error}</div>}

      <div className="board">
        {shown.map((room) => {
          const mine = bookings.filter((b) => b.room_id === room.id).sort((a, b) => new Date(a.start) - new Date(b.start));
          const down = room.status !== "available";
          let state = "";
          let why = null;
          if (picked && picked.room_id !== room.id) {
            why = reasonNot(room, picked);
            state = why ? "bad" : "ok";
          } else if (picked && picked.room_id === room.id) {
            state = "here";
          }
          const from = picked ? roomById(picked.room_id) : null;
          const differentType = picked && !why && from && from.type !== room.type && picked.room_id !== room.id;

          return (
            <div
              key={room.id}
              className={`room-card ${down ? "down" : ""} ${state} ${hoverId === room.id ? "hover" : ""}`}
              onDragOver={(e) => {
                if (picked) {
                  e.preventDefault();
                  setHoverId(room.id);
                }
              }}
              onDragLeave={() => setHoverId((cur) => (cur === room.id ? null : cur))}
              onDrop={(e) => {
                e.preventDefault();
                setHoverId(null);
                if (picked && picked.room_id !== room.id) move(picked, room);
              }}
            >
              <div className="room-head">
                <div>
                  <b>{room.name}</b>
                  <div className="small">{room.building} · {room.type} · seats {room.capacity}</div>
                </div>
                {down ? <Badge tone="red">out of service</Badge> : <Badge tone="green">available</Badge>}
              </div>

              {mine.length === 0 && <div className="small">Free all day</div>}
              {mine.map((b) => (
                <div
                  key={b.id}
                  className={`chip ${b.kind === "exam" ? "exam" : ""} ${b.id === pickedId ? "picked" : ""}`}
                  draggable={!busy}
                  onDragStart={(e) => {
                    e.dataTransfer.setData("text/plain", String(b.id));
                    e.dataTransfer.effectAllowed = "move";
                    setPickedId(b.id);
                    setMsg("");
                    setError("");
                  }}
                  onDragEnd={() => setHoverId(null)}
                  onClick={() => setPickedId(b.id === pickedId ? null : b.id)}
                >
                  <b>{b.title}</b>
                  <div className="small">
                    {fmtTime(b.start)} to {fmtTime(b.end)} · {b.attendees} people{" "}
                    <Badge tone={KIND_TONE[b.kind]}>{b.kind}</Badge>
                  </div>
                </div>
              ))}

              {state === "bad" && <div className="small error">{why}</div>}
              {state === "ok" && (
                <div>
                  {differentType && <div className="small" style={{ color: "#b45309" }}>Different room type ({from.type} to {room.type})</div>}
                  <button disabled={busy} onClick={() => move(picked, room)}>Move here</button>
                </div>
              )}

              <div style={{ marginTop: 8 }}>
                {down ? (
                  <>
                    {mine.length > 0 && <button disabled={busy} onClick={() => moveAll(room)}>Move all to best match</button>}
                    <button className="ghost" disabled={busy} onClick={() => setStatus(room, "available")}>Mark available</button>
                  </>
                ) : (
                  <button className="ghost" disabled={busy} onClick={() => setStatus(room, "unusable")}>Mark out of service</button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
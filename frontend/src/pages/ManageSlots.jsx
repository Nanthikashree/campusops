import { Fragment, useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";
import { fmtNaive, fmtTime, fmt } from "../util.js";

const STATE = {
  open: ["Open", "blue"], opening_soon: ["Opening soon", "cyan"], full: ["Full", "gray"],
  closed: ["Closed", "gray"], cancelled: ["Cancelled", "red"],
};
const toLocalInput = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
const withSecs = (s) => (s.length === 16 ? s + ":00" : s);

export default function ManageSlots() {
  const { call } = useAuth();
  const [slots, setSlots] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("exam");
  const [roomId, setRoomId] = useState("");
  const [date, setDate] = useState(toLocalInput(new Date(Date.now() + 86400000)).slice(0, 10));
  const [from, setFrom] = useState("10:00");
  const [to, setTo] = useState("11:30");
  const [capacity, setCapacity] = useState(40);
  const [opensAt, setOpensAt] = useState(toLocalInput(new Date()));
  const [description, setDescription] = useState("");
  const [openId, setOpenId] = useState(null);
  const [people, setPeople] = useState([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => call("/api/slots?include_past=true").then(setSlots).catch((e) => setError(e.message));
  useEffect(() => {
    load();
    call("/api/rooms")
      .then((r) => setRooms(r.filter((x) => ["classroom", "lab", "hall"].includes(x.type) && x.status === "available")))
      .catch((e) => setError(e.message));
  }, []);

  function pickRoom(id) {
    setRoomId(id);
    const r = rooms.find((x) => String(x.id) === String(id));
    if (r) setCapacity(r.capacity);
  }

  async function create(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMsg("");
    try {
      await call("/api/slots", {
        method: "POST",
        body: {
          title: title.trim(), kind, description, room_id: Number(roomId),
          start_time: `${date}T${from}:00`, end_time: `${date}T${to}:00`,
          capacity: Number(capacity), opens_at: opensAt ? withSecs(opensAt) : null,
        },
      });
      setMsg("Slot created. Students can book it once the booking window opens.");
      setTitle("");
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function showPeople(id) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    try {
      setPeople(await call(`/api/slots/${id}/attendees`));
      setOpenId(id);
    } catch (e) {
      setError(e.message);
    }
  }

  async function cancel(s) {
    if (!window.confirm(`Cancel "${s.title}"? Booked students will be notified.`)) return;
    setError("");
    setMsg("");
    try {
      const r = await call(`/api/slots/${s.id}/cancel`, { method: "POST" });
      setMsg(r.message);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <div className="page-head">
        <h2>Slots</h2>
        <div className="muted">Open exam, lab, workshop and event slots for students. Booking closes 1 hour before the start.</div>
      </div>

      <form className="card" onSubmit={create}>
        <h3>Create a slot</h3>
        <div className="row">
          <div><label>Title</label><input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. CIA-I Exam" /></div>
          <div>
            <label>Type</label>
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              {["exam", "lab", "workshop", "event"].map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </div>
          <div>
            <label>Venue</label>
            <select value={roomId} onChange={(e) => pickRoom(e.target.value)} required>
              <option value="">Choose a room</option>
              {rooms.map((r) => <option key={r.id} value={r.id}>{r.building} - {r.name} (seats {r.capacity})</option>)}
            </select>
          </div>
        </div>
        <div className="row">
          <div><label>Date</label><input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></div>
          <div><label>From</label><input type="time" value={from} onChange={(e) => setFrom(e.target.value)} /></div>
          <div><label>To</label><input type="time" value={to} onChange={(e) => setTo(e.target.value)} /></div>
          <div><label>Seats available</label><input type="number" min="1" max="500" value={capacity} onChange={(e) => setCapacity(e.target.value)} /></div>
        </div>
        <div className="row">
          <div><label>Booking opens</label><input type="datetime-local" value={opensAt} onChange={(e) => setOpensAt(e.target.value)} /></div>
          <div><label>Note for students (optional)</label><input value={description} onChange={(e) => setDescription(e.target.value)} /></div>
        </div>
        <button type="submit" disabled={busy || title.trim().length < 3 || !roomId}>Create slot</button>
      </form>

      {msg && <div className="notice">{msg}</div>}
      {error && <p className="error">{error}</p>}

      {!slots ? <p>Loading...</p> : (
        <table className="table">
          <thead>
            <tr><th>Slot</th><th>Venue</th><th>When</th><th>Booked</th><th>Booking window</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {slots.map((s) => {
              const [text, tone] = STATE[s.state];
              return (
                <Fragment key={s.id}>
                  <tr>
                    <td><b>{s.title}</b><div className="small" style={{ textTransform: "capitalize" }}>{s.kind}</div></td>
                    <td>{s.venue}</td>
                    <td>{fmtNaive(s.start)} to {fmtTime(s.end)}</td>
                    <td>{s.booked}/{s.capacity}</td>
                    <td className="small">{fmtNaive(s.opens_at)} to {fmtNaive(s.closes_at)}</td>
                    <td><span className={"tag " + tone}>{text}</span></td>
                    <td>
                      <button className="ghost" onClick={() => showPeople(s.id)}>{openId === s.id ? "Hide" : "Attendees"}</button>
                      {s.state !== "cancelled" && <button className="danger" onClick={() => cancel(s)}>Cancel slot</button>}
                    </td>
                  </tr>
                  {openId === s.id && (
                    <tr>
                      <td colSpan={7}>
                        {people.length === 0 ? <span className="muted">Nobody has booked yet.</span> : (
                          <ul style={{ margin: 0 }}>
                            {people.map((p) => <li key={p.email}>{p.name} <span className="small">({p.email}, booked {fmt(p.booked_at)})</span></li>)}
                          </ul>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
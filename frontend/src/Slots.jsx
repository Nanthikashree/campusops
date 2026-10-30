import { useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";
import { fmtNaive, fmtTime } from "../util.js";

const STATE = {
  open: ["Open", "blue"], opening_soon: ["Opening soon", "cyan"], full: ["Full", "gray"],
  closed: ["Closed", "gray"], cancelled: ["Cancelled", "red"],
};
const TABS = [["all", "All"], ["exam", "Exams"], ["lab", "Labs"], ["workshop", "Workshops"], ["event", "Events"], ["mine", "My bookings"]];

export default function Slots() {
  const { call } = useAuth();
  const [rows, setRows] = useState(null);
  const [tab, setTab] = useState("all");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => call("/api/slots").then(setRows).catch((e) => setError(e.message));
  useEffect(() => {
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, []);

  async function act(id, path, okText) {
    setBusy(true);
    setError("");
    setMsg("");
    try {
      await call(`/api/slots/${id}/${path}`, { method: "POST" });
      setMsg(okText);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
      load();
    }
  }

  if (!rows) return <p>{error || "Loading..."}</p>;
  const shown = rows.filter((s) => (tab === "all" ? true : tab === "mine" ? s.my_seat : s.kind === tab));

  return (
    <div>
      <div className="page-head">
        <h2>Exams and events</h2>
        <div className="muted">Book your seat in the slots opened by the college. Booking closes 1 hour before the start.</div>
      </div>

      <div className="tabs">
        {TABS.map(([key, text]) => (
          <button key={key} className={tab === key ? "" : "ghost"} onClick={() => setTab(key)}>{text}</button>
        ))}
      </div>

      {msg && <div className="notice">{msg}</div>}
      {error && <p className="error">{error}</p>}
      {shown.length === 0 && <p className="muted">No slots here right now.</p>}

      <div className="slot-grid">
        {shown.map((s) => {
          const [text, tone] = STATE[s.state];
          const pct = Math.min(100, Math.round((100 * s.booked) / s.capacity));
          return (
            <div className="card slot-card" key={s.id}>
              <div className="slot-head">
                <h3>{s.title}</h3>
                <span className={"tag " + tone}>{text}</span>
              </div>
              <div className="small" style={{ textTransform: "capitalize" }}>{s.kind}</div>
              <div className="muted">{fmtNaive(s.start)} to {fmtTime(s.end)}</div>
              <div className="muted">Venue: {s.venue}</div>
              {s.description && <div className="small">{s.description}</div>}
              <div className="small">Booking window: {fmtNaive(s.opens_at)} to {fmtNaive(s.closes_at)}</div>
              <div className="small">Cancellation ends: {fmtNaive(s.cancel_until)}</div>
              <div>Capacity: <b>{s.booked}/{s.capacity}</b> <span className="small">({s.seats_left} left)</span></div>
              <div className="progress"><div style={{ width: pct + "%", background: pct >= 100 ? "#dc3545" : "#198754" }} /></div>
              <div style={{ marginTop: 8 }}>
                {s.my_seat ? (
                  <>
                    <span className="tag green">Booked</span>{" "}
                    {s.can_cancel_seat ? (
                      <button className="ghost" disabled={busy} onClick={() => act(s.id, "cancel-seat", "Your seat was cancelled.")}>Cancel my seat</button>
                    ) : (
                      <span className="small">Cancellation has ended</span>
                    )}
                  </>
                ) : s.can_book ? (
                  <button disabled={busy} onClick={() => act(s.id, "book", `Seat booked for ${s.title}.`)}>Book now</button>
                ) : (
                  <button disabled className="ghost">
                    {s.state === "opening_soon" ? `Opens ${fmtNaive(s.opens_at)}` : s.state === "full" ? "Slot full"
                      : s.state === "cancelled" ? "Cancelled" : "Booking closed"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import Badge from "../components/Badge.jsx";
import { PRIORITY_TONE } from "../util.js";

const pct = (v, max) => Math.round((100 * v) / Math.max(1, max)) + "%";
const utilTone = (p) => (p >= 80 ? "red" : p >= 50 ? "amber" : "green");

function Stat({ text, value, hint }) {
  return (
    <div className="card stat">
      <div>
        <div className="muted">{text}</div>
        <div className="big">{value ?? "-"}</div>
        {hint && <div className="small">{hint}</div>}
      </div>
    </div>
  );
}

export default function Analytics() {
  const { call } = useAuth();
  const [o, setO] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [date, setDate] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const q = date ? `?date=${date}` : "";
    Promise.all([call(`/api/analytics/overview${q}`), call("/api/incidents")])
      .then(([a, i]) => {
        setO(a);
        setIncidents(i);
        if (!date) setDate(a.utilisation.date);
      })
      .catch((e) => setError(e.message));
  }, [date]);

  if (error) return <p className="error">{error}</p>;
  if (!o) return <p>Loading...</p>;
  const maxTrend = Math.max(1, ...o.trend.map((d) => Math.max(d.opened, d.resolved)));

  return (
    <div>
      <div className="page-head">
        <h2>Analytics</h2>
        <div className="muted">How requests, deadlines, rooms and stock are doing.</div>
      </div>

      <div className="grid">
        <Stat text="Open requests" value={o.open_requests} hint={`${o.total_requests} in total`} />
        <Stat text="SLA compliance" value={o.sla_compliance === null ? "-" : o.sla_compliance + "%"} hint="resolved on time" />
        <Stat text="Average time to resolve" value={o.avg_resolution_hours === null ? "-" : o.avg_resolution_hours + " h"} />
        <Stat text="Room utilisation" value={o.utilisation.percent + "%"} hint={`on ${o.utilisation.date}`} />
        <Stat text="Parts short of stock" value={o.shortages.length} />
        <Stat text="Purchases awaiting approval" value={o.pending_purchases.count}
          hint={o.pending_purchases.amount ? `Rs ${o.pending_purchases.amount.toLocaleString()}` : ""} />
      </div>

      {incidents.length > 0 && (
        <div className="card">
          <h3>Related complaints, merged into incidents</h3>
          {incidents.map((i, n) => (
            <div className="impact" key={n}>
              <b style={{ textTransform: "capitalize" }}>{i.title}</b>{" "}
              <Badge tone={PRIORITY_TONE[i.priority]}>{i.priority}</Badge>{" "}
              <span className="small">{i.count} complaints</span>
              <div className="muted">{i.summary}</div>
              <div className="small">
                Requests: {i.ticket_ids.map((id) => <span key={id}><Link to={`/tickets/${id}`}>#{id}</Link>{" "}</span>)}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="two-col">
        <div className="card">
          <h3>Requests over the last 7 days</h3>
          <div className="legend">
            <span><i style={{ background: "var(--accent)" }} />Opened</span>
            <span><i style={{ background: "#198754" }} />Resolved</span>
          </div>
          {o.trend.map((d) => (
            <div className="bar-row" key={d.day}>
              <div className="name" style={{ width: 70 }}>{d.day}</div>
              <div style={{ flex: 1 }}>
                <div className="bar-track"><div className="bar-fill" style={{ width: pct(d.opened, maxTrend) }} /></div>
                <div className="bar-track" style={{ marginTop: 4 }}><div className="bar-fill green" style={{ width: pct(d.resolved, maxTrend) }} /></div>
              </div>
              <div className="num" style={{ width: 54 }}>{d.opened} / {d.resolved}</div>
            </div>
          ))}
        </div>

        <div className="card">
          <h3>Room utilisation</h3>
          <label>Day</label>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <div className="muted">
            {o.utilisation.booked_hours} room-hours booked between 8 AM and 6 PM ({o.utilisation.percent}% of all classrooms, labs and halls).
          </div>
          {o.utilisation.rooms.length === 0 && <p className="muted">Nothing is booked on this day.</p>}
          {o.utilisation.rooms.map((r) => (
            <div className="bar-row" key={r.building + r.name}>
              <div className="name" style={{ width: 120 }}>{r.name}</div>
              <div className="bar-track"><div className={"bar-fill " + utilTone(r.percent)} style={{ width: r.percent + "%" }} /></div>
              <div className="num" style={{ width: 44 }}>{r.percent}%</div>
            </div>
          ))}
        </div>
      </div>

      <div className="two-col">
        <div className="card">
          <h3>Shortages</h3>
          {o.shortages.length === 0 ? (
            <p className="muted">Every part is above its minimum stock.</p>
          ) : (
            <table className="table">
              <thead><tr><th>Part</th><th>Available</th><th>Minimum</th></tr></thead>
              <tbody>
                {o.shortages.map((s) => (
                  <tr key={s.name}>
                    <td>{s.name}</td>
                    <td><Badge tone={s.available <= 0 ? "red" : "amber"}>{s.available}</Badge></td>
                    <td>{s.min_stock}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h3>Recurring problems (last 30 days)</h3>
          {o.recurring.length === 0 ? (
            <p className="muted">No problem has repeated in the same place yet.</p>
          ) : (
            o.recurring.map((r, i) => (
              <div className="task" key={i}>
                <div>
                  <b style={{ textTransform: "capitalize" }}>{r.what}</b> in {r.where}
                  <div className="small">
                    {r.ticket_ids.map((id) => <span key={id}><Link to={`/tickets/${id}`}>#{id}</Link>{" "}</span>)}
                  </div>
                </div>
                <Badge tone={r.count >= 3 ? "red" : "amber"}>{r.count} times</Badge>
              </div>
            ))
          )}
          {o.recurring.length > 0 && <p className="small">Repeated faults may mean the item should be replaced, not repaired again.</p>}
        </div>
      </div>
    </div>
  );
}
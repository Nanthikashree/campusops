import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList, Wrench, Hourglass, Check, Clock, Flame, Gauge, ShieldCheck, Package, DoorClosed, Siren } from "lucide-react";
import { useAuth } from "../auth.jsx";
import Badge from "../components/Badge.jsx";
import { label, STATUS_TONE, PRIORITY_TONE } from "../util.js";

function Stat({ icon: Icon, tone, label: text, value, hint }) {
  return (
    <div className="card stat">
      <div className={"icon-bubble " + tone}><Icon size={20} /></div>
      <div>
        <div className="muted">{text}</div>
        <div className="big">{value ?? "-"}</div>
        {hint && <div className="small">{hint}</div>}
      </div>
    </div>
  );
}

export default function AdminHome() {
  const { call } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([call("/api/dashboard/summary"), call("/api/incidents"), call("/api/tickets")])
      .then(([summary, incidents, tickets]) => setData({ summary, incidents, tickets }))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading...</p>;
  const { summary: s, incidents, tickets } = data;
  const max = Math.max(1, ...Object.values(s.by_type));
  const top = incidents[0];

  return (
    <div>
      <div className="page-head">
        <h2>Dashboard</h2>
        <div className="muted">Here is what is happening on campus today.</div>
      </div>

      {top && (
        <div className="banner">
          <div className="icon-bubble"><Siren size={22} /></div>
          <div style={{ flex: 1 }}>
            <b>Critical incident: {top.title}</b>
            <div className="muted">{top.summary}</div>
          </div>
          <Link to="/tickets"><button>View requests</button></Link>
        </div>
      )}

      <div className="grid">
        <Stat icon={ClipboardList} tone="blue" label="Open requests" value={s.open_requests} />
        <Stat icon={Wrench} tone="teal" label="In progress" value={s.in_progress} />
        <Stat icon={Hourglass} tone="amber" label="Blocked (waiting for parts)" value={s.blocked} />
        <Stat icon={Check} tone="green" label="Resolved" value={s.resolved} />
        <Stat icon={Clock} tone="amber" label="Deadline at risk" value={s.sla_at_risk} />
        <Stat icon={Flame} tone="red" label="Deadline breached" value={s.sla_breached} />
        <Stat icon={Gauge} tone="green" label="SLA compliance" value={s.sla_compliance === null ? "-" : s.sla_compliance + "%"} />
        <Stat icon={ShieldCheck} tone="blue" label="Pending approvals" value={s.pending_approvals} />
        <Stat icon={Package} tone="amber" label="Low-stock parts" value={s.low_stock_parts} />
        <Stat icon={DoorClosed} tone="red" label="Rooms out of service" value={s.unusable_rooms} />
      </div>

      <div className="two-col">
        <div className="card">
          <h3>Requests by type</h3>
          {Object.entries(s.by_type).length === 0 && <p className="muted">No requests yet.</p>}
          {Object.entries(s.by_type).map(([k, v]) => (
            <div className="bar-row" key={k}>
              <div className="name">{label(k)}</div>
              <div className="bar-track"><div className="bar-fill" style={{ width: (100 * v) / max + "%" }} /></div>
              <div className="num">{v}</div>
            </div>
          ))}
        </div>
        <div className="card">
          <h3>Recent requests</h3>
          {tickets.slice(0, 5).map((t) => (
            <div key={t.id} style={{ padding: "8px 0", borderTop: "1px solid var(--line)" }}>
              <Link to={`/tickets/${t.id}`}>#{t.id} {t.title.slice(0, 38)}</Link>
              <div style={{ marginTop: 4 }}>
                <Badge tone={STATUS_TONE[t.status]}>{label(t.status)}</Badge>{" "}
                <Badge tone={PRIORITY_TONE[t.priority]}>{t.priority}</Badge>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
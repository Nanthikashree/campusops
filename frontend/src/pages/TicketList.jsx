import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import Badge from "../components/Badge.jsx";
import { label, STATUS_TONE, PRIORITY_TONE, SLA_TONE } from "../util.js";

export default function TicketList() {
  const { call, user } = useAuth();
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    call("/api/tickets").then(setRows).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!rows) return <p>Loading...</p>;
  const staff = user.portal === "admin";

  return (
    <div>
      <div className="page-head">
        <h2>{user.role === "technician" ? "My jobs" : staff ? "All requests" : "My requests"}</h2>
      </div>
      {rows.length === 0 ? (
        <p className="muted">Nothing here yet.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>#</th><th>Issue</th><th>Where</th><th>Status</th><th>Current step</th><th>Waiting for</th>
              {staff && <th>Priority</th>}{staff && <th>Deadline</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.id}>
                <td><Link to={`/tickets/${t.id}`}>#{t.id}</Link></td>
                <td>{t.title}</td>
                <td>{t.room || "-"}</td>
                <td><Badge tone={STATUS_TONE[t.status]}>{label(t.status)}</Badge></td>
                <td>{t.stage}</td>
                <td>{t.waiting_for || "-"}</td>
                {staff && <td><Badge tone={PRIORITY_TONE[t.priority]}>{t.priority}</Badge></td>}
                {staff && <td><Badge tone={SLA_TONE[t.sla.state]}>{label(t.sla.state)}</Badge></td>}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
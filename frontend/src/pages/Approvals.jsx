import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import ApprovalLevels from "../components/ApprovalLevels.jsx";
import { fmt } from "../util.js";

export default function Approvals() {
  const { call } = useAuth();
  const [rows, setRows] = useState(null);
  const [notes, setNotes] = useState({});
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const load = () => call("/api/approvals").then(setRows).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  async function decide(id, decision) {
    setError("");
    setMsg("");
    try {
      const r = await call(`/api/approvals/${id}/decide`, { method: "POST", body: { decision, note: notes[id] || "" } });
      setMsg(r.message);
      setNotes({ ...notes, [id]: "" });
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  if (!rows) return <p>{error || "Loading..."}</p>;

  return (
    <div>
      <div className="page-head">
        <h2>Approvals</h2>
        <div className="muted">Purchase requests go through every level, in order.</div>
      </div>
      {msg && <div className="notice">{msg}</div>}
      {error && <p className="error">{error}</p>}
      {rows.length === 0 && <p className="muted">No purchase requests yet.</p>}
      {rows.map((a) => (
        <div className="card" key={a.id}>
          <div className="group-head">
            <h3>Purchase request #{a.id}: {a.quantity} x {a.part}</h3>
            <span className={"tag " + ({ pending: "amber", approved: "green", rejected: "red", cancelled: "gray" }[a.status])}>
              {a.status.charAt(0).toUpperCase() + a.status.slice(1)}
            </span>
          </div>
          <div className="muted" style={{ marginBottom: 10 }}>
            Rs {a.amount.toLocaleString()} · requested by {a.requested_by} on {fmt(a.created_at)}
            {a.ticket_id && <> · for <Link to={`/tickets/${a.ticket_id}`}>request #{a.ticket_id}</Link></>}
            {a.waiting_for && <> · <b>waiting for the {a.waiting_for}</b></>}
          </div>
          <ApprovalLevels steps={a.steps} />
          {a.can_decide && (
            <div style={{ marginTop: 12 }}>
              <input value={notes[a.id] || ""} onChange={(e) => setNotes({ ...notes, [a.id]: e.target.value })} placeholder="Remarks (optional)" />
              <button onClick={() => decide(a.id, "approve")}>Approve</button>
              <button className="danger" onClick={() => decide(a.id, "reject")}>Reject</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
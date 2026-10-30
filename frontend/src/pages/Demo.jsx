import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import Badge from "../components/Badge.jsx";
import { fmt } from "../util.js";

const SENDERS = [
  ["student@campus.edu", "Student"],
  ["faculty@campus.edu", "Faculty"],
  ["stranger@gmail.com", "Unknown sender (not registered)"],
];
const SAMPLE = {
  subject: "Projector problem",
  body: "The projector in B203 is not working since morning",
};
const INBOX_TONE = { processed: "green", invalid: "red", received: "gray" };

export default function Demo() {
  const { call } = useAuth();
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [exam, setExam] = useState(null);
  const [wifi, setWifi] = useState(null);

  const [sender, setSender] = useState(SENDERS[0][0]);
  const [subject, setSubject] = useState(SAMPLE.subject);
  const [body, setBody] = useState(SAMPLE.body);
  const [lastId, setLastId] = useState("");
  const [mailResult, setMailResult] = useState(null);
  const [inbox, setInbox] = useState([]);

  const loadInbox = () => call("/api/integrations/email/inbox").then(setInbox).catch(() => {});
  useEffect(() => {
    loadInbox();
  }, []);

  async function run(key, fn) {
    setBusy(key);
    setError("");
    setMsg("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  const runExam = () =>
    run("exam", async () => {
      setExam(await call("/api/demo/scenario/exam-ac-failure", { method: "POST" }));
      setMsg("Scenario 1 is running. Follow the next step shown below.");
    });

  const runWifi = () =>
    run("wifi", async () => {
      setWifi(await call("/api/demo/scenario/wifi-outage", { method: "POST" }));
      setMsg("Scenario 2 is running. Follow the next step shown below.");
    });

  const reset = () => {
    if (!window.confirm("Reset the demo? This removes all requests, slot bookings and notifications, and restores rooms, staff and stock.")) return;
    run("reset", async () => {
      const r = await call("/api/demo/reset", { method: "POST" });
      setExam(null);
      setWifi(null);
      setMailResult(null);
      setLastId("");
      setMsg(r.message);
      loadInbox();
    });
  };

  const sendMail = (messageId) =>
    run("mail", async () => {
      const r = await call("/api/integrations/email/simulate", {
        method: "POST",
        body: { sender, subject, body, message_id: messageId || null },
      });
      setLastId(r.message_id);
      setMailResult(r);
      loadInbox();
    });

  return (
    <div>
      <div className="page-head">
        <h2>Demo control</h2>
        <div className="muted">Run the disruption scenarios, simulate incoming email and reset between runs.</div>
      </div>

      {msg && <div className="notice">{msg}</div>}
      {error && <div className="notice error">{error}</div>}

      <div className="two-col">
        <div className="card">
          <h3>Scenario 1: classroom unavailable before an exam</h3>
          <p className="muted">
            The AC fails in B203, where an exam is scheduled. The room is marked out of service, the exam is flagged with
            replacement rooms, a technician is assigned and a part runs out, so the job is blocked and sent for approval.
          </p>
          <button disabled={!!busy} onClick={runExam}>{busy === "exam" ? "Running..." : "Run scenario 1"}</button>
          {exam && (
            <div className="impact">
              <div>Request <Link to={`/tickets/${exam.ticket_id}`}><b>#{exam.ticket_id}</b></Link>, technician <b>{exam.technician}</b>, room <b>{exam.room}</b> out of service.</div>
              <div className="muted" style={{ marginTop: 6 }}>{exam.parts}</div>
              {exam.bookings_affected.map((b, i) => (
                <div key={i} className="small">
                  Affected: {b.booking} ({b.kind}). Suggested rooms: {b.alternatives.join(", ") || "none free"}
                </div>
              ))}
              <div className="step-wait">{exam.next_step}</div>
              <Link to="/rooms"><button className="ghost">Open Rooms to move the exam</button></Link>
              <Link to="/approvals"><button className="ghost">Open Approvals</button></Link>
            </div>
          )}
        </div>

        <div className="card">
          <h3>Scenario 2: Wi-Fi outage reported by many users</h3>
          <p className="muted">
            Four complaints arrive about the Wi-Fi. They are merged into one incident, the network technician goes on leave so
            the job is reassigned automatically, and the deadline passes, so it is escalated.
          </p>
          <button disabled={!!busy} onClick={runWifi}>{busy === "wifi" ? "Running..." : "Run scenario 2"}</button>
          {wifi && (
            <div className="impact">
              <div>
                Requests {wifi.ticket_ids.map((id) => <span key={id}><Link to={`/tickets/${id}`}>#{id}</Link>{" "}</span>)}
              </div>
              <div className="muted" style={{ marginTop: 6 }}>
                <b>{wifi.first_technician}</b> went on leave, so the job moved to <b>{wifi.reassigned_to || "nobody (no one free)"}</b>.
                Deadline status: <Badge tone={wifi.sla === "breached" ? "red" : "amber"}>{wifi.sla}</Badge>
              </div>
              <div className="step-wait">{wifi.next_step}</div>
              <Link to="/"><button className="ghost">Open the dashboard</button></Link>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h3>Simulated email inbox (external integration)</h3>
        <p className="muted">
          An outside email service posts each message to the system. Unknown senders are rejected, and the same email arriving twice
          never creates a second request.
        </p>
        <div className="row">
          <div>
            <label>From</label>
            <select value={sender} onChange={(e) => setSender(e.target.value)}>
              {SENDERS.map(([v, t]) => <option key={v} value={v}>{t} ({v})</option>)}
            </select>
          </div>
          <div><label>Subject</label><input value={subject} onChange={(e) => setSubject(e.target.value)} /></div>
        </div>
        <label>Message</label>
        <textarea rows={3} value={body} onChange={(e) => setBody(e.target.value)} />
        <button disabled={!!busy || body.trim().length < 3} onClick={() => sendMail(null)}>Send new email</button>
        <button className="ghost" disabled={!!busy || !lastId} onClick={() => sendMail(lastId)}>Send the same email again</button>
        <button className="ghost" onClick={loadInbox}>Refresh inbox</button>

        {mailResult && (
          <div className="impact">
            <div>
              Result: <Badge tone={mailResult.status === "processed" ? "green" : mailResult.status === "duplicate" ? "amber" : "red"}>{mailResult.status}</Badge>
              {mailResult.ticket_id && <> request <Link to={`/tickets/${mailResult.ticket_id}`}>#{mailResult.ticket_id}</Link></>}
            </div>
            {mailResult.status === "processed" && (
              <div className="small">
                Read as {mailResult.issue_type}, room {mailResult.room || "not found"}, urgency {mailResult.urgency}.
                {mailResult.question && <> Follow-up sent to the sender: {mailResult.question}</>}
              </div>
            )}
            {mailResult.status === "duplicate" && <div className="small">{mailResult.message}</div>}
          </div>
        )}

        <table className="table" style={{ marginTop: 14 }}>
          <thead><tr><th>Time</th><th>From</th><th>Subject</th><th>Status</th><th>Request</th></tr></thead>
          <tbody>
            {inbox.length === 0 && <tr><td colSpan={5} className="muted">No emails yet.</td></tr>}
            {inbox.map((m) => (
              <tr key={m.id}>
                <td>{fmt(m.at)}</td>
                <td>{m.from}</td>
                <td>{m.subject || "-"}</td>
                <td><Badge tone={INBOX_TONE[m.status] || "gray"}>{m.status}</Badge></td>
                <td>{m.ticket_id ? <Link to={`/tickets/${m.ticket_id}`}>#{m.ticket_id}</Link> : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Reset</h3>
        <p className="muted">Clears requests, approvals, notifications, emails and slot seats, and restores rooms, staff, stock and the demo timetable. Users stay the same.</p>
        <button className="danger" disabled={!!busy} onClick={reset}>{busy === "reset" ? "Resetting..." : "Reset demo data"}</button>
      </div>
    </div>
  );
}
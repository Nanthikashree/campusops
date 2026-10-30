import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { label } from "../util.js";

const TYPES = ["maintenance", "it_network", "room_booking", "equipment", "inventory", "other"];
const URGENCY = ["low", "medium", "high", "critical"];

export default function Raise() {
  const { call } = useAuth();
  const [text, setText] = useState("");
  const [extra, setExtra] = useState("");
  const [result, setResult] = useState(null);
  const [created, setCreated] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function analyze(full) {
    setBusy(true);
    setError("");
    try {
      setResult(await call("/api/intake/analyze", { method: "POST", body: { text: full } }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function start(e) {
    e.preventDefault();
    if (text.trim().length >= 3) analyze(text.trim());
  }

  function addDetails(e) {
    e.preventDefault();
    if (!extra.trim()) return;
    const full = (text + " " + extra).trim();
    setText(full);
    setExtra("");
    analyze(full);
  }

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const t = await call("/api/tickets", {
        method: "POST",
        body: {
          description: text.trim(),
          room_id: result.room ? result.room.id : null,
          issue_type: result.issue_type,
          asset: result.asset || "",
          urgency: result.urgency,
          channel: "form",
        },
      });
      setCreated(t);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setText("");
    setExtra("");
    setResult(null);
    setCreated(null);
  }

  if (created) {
    return (
      <div className="card">
        <h2 className="ok">Request sent</h2>
        <p>Your request <b>#{created.id}</b> was logged and the facilities team was notified.</p>
        {created.similar_ticket_ids?.length > 0 && (
          <div className="notice">
            Others have reported something similar (#{created.similar_ticket_ids.join(", #")}). We will handle them together.
          </div>
        )}
        <Link to={`/tickets/${created.id}`}><button>Track this request</button></Link>
        <button className="ghost" onClick={reset}>Raise another</button>
      </div>
    );
  }

  return (
    <div>
      <h2>Raise a request</h2>
      <p className="muted">Describe the problem in your own words. We will work out the details.</p>

      <form className="card" onSubmit={start}>
        <textarea
          rows={4}
          maxLength={500}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. The AC in B block room 203 is not working since this morning"
        />
        <button type="submit" disabled={busy || text.trim().length < 3}>
          {busy ? "Reading..." : result ? "Re-read my description" : "Continue"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="card">
          <h3>What we understood</h3>
          <div className="row">
            <div>
              <label className="small">Issue type</label>
              <select value={result.issue_type} onChange={(e) => setResult({ ...result, issue_type: e.target.value })}>
                {TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}
              </select>
            </div>
            <div>
              <label className="small">Urgency</label>
              <select value={result.urgency} onChange={(e) => setResult({ ...result, urgency: e.target.value })}>
                {URGENCY.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
          </div>
          <p>
            <b>Location:</b> {result.room ? `${result.room.building} - ${result.room.name}` : "not found"}
            {"  "}
            <b>Item:</b> {result.asset || "not specified"}
          </p>
          <div className="small">Read by: {result.extracted_by}</div>

          {result.question && (
            <form className="notice" onSubmit={addDetails}>
              <b>{result.question}</b>
              <input value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="Type your answer" />
              <button type="submit" className="ghost" disabled={busy}>Add this detail</button>
            </form>
          )}

          <button onClick={submit} disabled={busy}>
            {result.question ? "Submit anyway" : "Submit request"}
          </button>
        </div>
      )}
    </div>
  );
}
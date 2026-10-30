import { useState } from "react";
import { ShieldCheck, Sparkles, ClipboardCheck } from "lucide-react";
import { useAuth } from "../auth.jsx";

const DEMO = [
  ["student", "Student"], ["faculty", "Faculty"], ["electrician", "Electrician"],
  ["network", "Network technician"], ["general", "General technician"], ["plumber", "Plumber"],
  ["manager", "Department manager"], ["facilities", "Facilities admin"],
  ["procurement", "Procurement approver"], ["admin", "System admin"],
];

export default function Login() {
  const { login } = useAuth();
  const [id, setId] = useState("student");
  const [password, setPassword] = useState("campus123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(id.trim(), password);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-hero">
        <div className="brand"><div className="logo">C</div><span>CampusOps</span></div>
        <h1>One place to report, track and fix every campus issue.</h1>
        <p>CampusOps links complaints, rooms, staff and spare parts, with a fixed workflow so everyone knows what is waiting for them.</p>
        <ul>
          <li><Sparkles size={18} /> AI reads your complaint and asks only what is missing</li>
          <li><ClipboardCheck size={18} /> A signed job card records who did what, and when</li>
          <li><ShieldCheck size={18} /> Role-based access enforced by the server</li>
        </ul>
      </div>
      <div className="login-panel">
        <div className="box">
          <h2>Sign in</h2>
          <p className="muted">Use your user ID and password</p>
          <form onSubmit={submit}>
            <label>User ID</label>
            <input value={id} onChange={(e) => setId(e.target.value)} />
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="submit" disabled={busy} style={{ width: "100%", justifyContent: "center" }}>
              {busy ? "Signing in..." : "Sign in"}
            </button>
            {error && <p className="error">{error}</p>}
          </form>
          <div className="card" style={{ marginTop: 18 }}>
            <div className="small" style={{ marginBottom: 6 }}>Demo user IDs (password: campus123)</div>
            <div className="chips">
              {DEMO.map(([uid, name]) => (
                <button key={uid} className="ghost" type="button" onClick={() => setId(uid)}>{name}</button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
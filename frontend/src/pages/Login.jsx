import { useState } from "react";
import { ShieldCheck, Sparkles, ClipboardCheck } from "lucide-react";
import { useAuth } from "../auth.jsx";
import { BRAND } from "../brand.js";

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
        <div className="brand">
          <div className="logo">{BRAND.app[0]}</div>
          <div>
            <div className="brand-name">{BRAND.app}</div>
            <div className="brand-sub">{BRAND.college}</div>
          </div>
        </div>
        <h1>{BRAND.headline}</h1>
        <p>Complaints, rooms, technicians and spare parts, linked in one workflow so everyone knows what is waiting for them.</p>
        <div className="feature-list">
          <div className="feature">
            <Sparkles size={24} />
            <div><b>AI that listens</b><span>Describe a problem in plain words. We ask only for what is missing.</span></div>
          </div>
          <div className="feature">
            <ClipboardCheck size={24} />
            <div><b>A signed record of every fix</b><span>Who did what and when, with before and after photos.</span></div>
          </div>
          <div className="feature">
            <ShieldCheck size={24} />
            <div><b>Rules you can trust</b><span>Permissions, stock and approvals are enforced by the server, not left to AI.</span></div>
          </div>
        </div>
        <div className="hero-foot">{BRAND.tagline}</div>
      </div>

      <div className="login-panel">
        <div className="box">
          <h2>Welcome back</h2>
          <p className="muted">Sign in with your user ID</p>
          <form onSubmit={submit} style={{ marginTop: 18 }}>
            <label>User ID</label>
            <input value={id} onChange={(e) => setId(e.target.value)} />
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="submit" disabled={busy} style={{ width: "100%", justifyContent: "center", padding: "13px 20px", fontSize: 16 }}>
              {busy ? "Signing in..." : "Sign in"}
            </button>
            {error && <p className="error">{error}</p>}
          </form>
          <div style={{ marginTop: 22, paddingTop: 18, borderTop: "1px solid var(--line)" }}>
            <div className="small" style={{ marginBottom: 8 }}>Demo accounts (password: campus123)</div>
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
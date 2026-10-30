import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { fmt } from "../util.js";

export default function Notifications() {
  const { call } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = () => call("/api/notifications").then(setData).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  async function readAll() {
    await call("/api/notifications/read-all", { method: "POST" });
    load();
  }

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading...</p>;

  return (
    <div>
      <h2>Notifications</h2>
      {data.unread > 0 && <button className="ghost" onClick={readAll}>Mark all as read</button>}
      {data.items.length === 0 && <p className="muted">Nothing yet.</p>}
      {data.items.map((n) => (
        <div key={n.id} className="card" style={{ opacity: n.read ? 0.65 : 1 }}>
          {n.message}
          <div className="small">
            {fmt(n.at)} {n.ticket_id && <Link to={`/tickets/${n.ticket_id}`}>open request #{n.ticket_id}</Link>}
          </div>
        </div>
      ))}
    </div>
  );
}
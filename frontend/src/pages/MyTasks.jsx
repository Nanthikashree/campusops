import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function MyTasks() {
  const { call } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    call("/api/my-tasks").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading...</p>;

  return (
    <div>
      <div className="page-head">
        <h2>My tasks</h2>
        <div className="muted">{data.headline}</div>
      </div>
      {data.groups.map((g) => (
        <div className="card" key={g.title}>
          <div className="group-head">
            <h3>{g.title}</h3>
            <span className="count-pill">{g.items.length}</span>
          </div>
          {g.items.length === 0 && <div className="muted">{g.empty}</div>}
          {g.items.map((it, i) => (
            <div className="task" key={i}>
              <div>
                <Link to={it.link}><b>{it.title}</b></Link>
                <div className="small">{it.detail}</div>
              </div>
              <div>
                <span className={"tag " + it.tone} style={{ marginRight: 10 }}>{it.tag}</span>
                <Link to={it.link}><button className="ghost">{it.action}</button></Link>
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
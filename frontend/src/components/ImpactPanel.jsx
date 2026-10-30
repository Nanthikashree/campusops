import Badge from "./Badge.jsx";
import { fmtNaive, fmtTime } from "../util.js";

const KIND_TONE = { class: "blue", exam: "red", event: "amber", meeting: "gray" };

export default function ImpactPanel({ affected, onMove, busy }) {
  if (!affected || affected.length === 0) {
    return <p className="muted">No upcoming classes or exams are affected.</p>;
  }
  return (
    <div>
      {affected.map((a) => (
        <div className="impact" key={a.booking.id}>
          <div>
            <b>{a.booking.title}</b> <Badge tone={KIND_TONE[a.booking.kind]}>{a.booking.kind}</Badge>
          </div>
          <div className="small">
            {fmtNaive(a.booking.start)} to {fmtTime(a.booking.end)} · {a.booking.attendees} people · {a.booking.building} {a.booking.room}
          </div>
          <div className="muted" style={{ marginTop: 8 }}>Suggested replacement rooms</div>
          {a.alternatives.length === 0 && <div className="error">No free room fits. A manager must decide.</div>}
          {a.alternatives.map((x) => (
            <div className="alt" key={x.room_id}>
              <div>
                <b>{x.name}</b> <span className="small">{x.building} · seats {x.capacity} · score {x.score}</span>
                <div className="small">{x.why.join("; ")}</div>
              </div>
              <button disabled={busy} onClick={() => onMove(a.booking.id, x.room_id)}>Move here</button>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
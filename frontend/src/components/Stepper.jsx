import { fmt } from "../util.js";

const TAG = {
  done: ["Completed", "green"],
  current: ["In progress", "blue"],
  pending: ["Pending", "gray"],
  blocked: ["Blocked", "red"],
  skipped: ["Not needed", "gray"],
};

export default function Stepper({ steps }) {
  return (
    <ol className="stepper">
      {steps.map((s) => {
        const [text, tone] = TAG[s.state] || TAG.pending;
        return (
          <li key={s.key} className={"step " + s.state}>
            <span className="dot" />
            <div>
              <div className="step-title">{s.title}<span className={"pill " + tone}>{text}</span></div>
              <div className="step-desc">{s.description}</div>
              {s.note && <div className="step-note">{s.note}</div>}
              {(s.at || s.by) && (
                <div className="step-meta">{s.at ? fmt(s.at) : ""}{s.at && s.by ? " · " : ""}{s.by || ""}</div>
              )}
              {s.waiting_for && s.state !== "done" && <div className="step-wait">Waiting for: {s.waiting_for}</div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
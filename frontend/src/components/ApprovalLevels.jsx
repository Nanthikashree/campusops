import { fmt } from "../util.js";

const TONE = { approved: "green", pending: "amber", rejected: "red", skipped: "gray", cancelled: "gray" };
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

export default function ApprovalLevels({ steps }) {
  const currentIndex = steps.findIndex((s) => s.status === "pending");
  return (
    <table className="table">
      <thead>
        <tr><th>Level</th><th>Role</th><th>Approver</th><th>Remarks</th><th>Status</th><th>Instruction</th></tr>
      </thead>
      <tbody>
        {steps.map((s, i) => (
          <tr key={s.level}>
            <td>{s.level}</td>
            <td>{s.role_label}</td>
            <td>{s.approver || (s.status === "skipped" ? "Skipped" : "Awaiting")}{s.at && <div className="small">{fmt(s.at)}</div>}</td>
            <td>{s.remarks || "-"}</td>
            <td><span className={"tag " + TONE[s.status]}>{cap(s.status)}</span></td>
            <td>{i === currentIndex ? "Decision needed" : "-"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
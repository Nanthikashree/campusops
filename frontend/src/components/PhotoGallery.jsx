import { useState } from "react";
import AuthImage from "./AuthImage.jsx";
import { fmt } from "../util.js";

const GROUPS = [
  ["complaint", "Photos from the reporter"],
  ["before", "Before the work"],
  ["after", "After the work"],
];

export default function PhotoGallery({ items }) {
  const [big, setBig] = useState(null);
  return (
    <div>
      {GROUPS.map(([kind, title]) => {
        const rows = items.filter((p) => p.kind === kind);
        if (rows.length === 0) return null;
        return (
          <div key={kind} style={{ marginBottom: 12 }}>
            <div className="muted"><b>{title}</b></div>
            <div className="thumb-row">
              {rows.map((p) => (
                <div key={p.id}>
                  <AuthImage id={p.id} alt={title} onOpen={setBig} />
                  <div className="small">{p.by}, {fmt(p.at)}</div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
      {big && (
        <div className="lightbox" onClick={() => setBig(null)}>
          <img src={big} alt="Enlarged" />
        </div>
      )}
    </div>
  );
}
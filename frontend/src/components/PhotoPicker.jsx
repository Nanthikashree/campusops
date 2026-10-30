import { useState } from "react";
import { fileToDataUrl } from "../util.js";

export default function PhotoPicker({ value, onChange, max = 3, label = "Add photos" }) {
  const [error, setError] = useState("");

  async function pick(e) {
    setError("");
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    const room = max - value.length;
    if (room <= 0) {
      setError(`You can add up to ${max} photos here`);
      return;
    }
    try {
      const urls = [];
      for (const f of files.slice(0, room)) urls.push(await fileToDataUrl(f));
      onChange([...value, ...urls]);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <div className="thumb-row">
        {value.map((src, i) => (
          <div className="thumb-wrap" key={i}>
            <img className="thumb" src={src} alt={`Selected ${i + 1}`} />
            <button type="button" className="thumb-x" onClick={() => onChange(value.filter((_, j) => j !== i))}>x</button>
          </div>
        ))}
      </div>
      {value.length < max && (
        <label className="photo-add">
          <input type="file" accept="image/*" multiple onChange={pick} />
          {label}
        </label>
      )}
      <span className="small" style={{ marginLeft: 10 }}>{value.length}/{max}</span>
      {error && <div className="error small">{error}</div>}
    </div>
  );
}
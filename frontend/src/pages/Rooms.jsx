import { useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";
import Badge from "../components/Badge.jsx";
import ImpactPanel from "../components/ImpactPanel.jsx";

export default function Rooms() {
  const { call } = useAuth();
  const [rooms, setRooms] = useState(null);
  const [building, setBuilding] = useState("all");
  const [impact, setImpact] = useState(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => call("/api/rooms").then(setRooms).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  async function setStatus(room, status) {
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const r = await call(`/api/rooms/${room.id}/status`, { method: "POST", body: { status } });
      if (status === "unusable") {
        setImpact({ room: room.name, summary: r.summary, affected: r.affected });
        setMsg(`${room.name} is now out of service.`);
      } else {
        setImpact(null);
        setMsg(`${room.name} is available again.`);
      }
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function move(bookingId, roomId) {
    setBusy(true);
    setError("");
    setMsg("");
    try {
      await call(`/api/bookings/${bookingId}/move`, { method: "POST", body: { room_id: roomId } });
      setMsg("Booking moved to the new room.");
      setImpact((cur) => cur && { ...cur, affected: cur.affected.filter((a) => a.booking.id !== bookingId) });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!rooms) return <p>{error || "Loading..."}</p>;
  const buildings = [...new Set(rooms.map((r) => r.building))];
  const shown = building === "all" ? rooms : rooms.filter((r) => r.building === building);

  return (
    <div>
      <div className="page-head">
        <h2>Rooms</h2>
        <div className="muted">Mark a room out of service and see which classes and exams it affects.</div>
      </div>
      {msg && <div className="notice">{msg}</div>}
      {error && <p className="error">{error}</p>}

      {impact && (
        <div className="card">
          <h3>Impact of closing {impact.room}</h3>
          <p className="muted">{impact.summary}</p>
          <ImpactPanel affected={impact.affected} onMove={move} busy={busy} />
        </div>
      )}

      <select value={building} onChange={(e) => setBuilding(e.target.value)} style={{ maxWidth: 260 }}>
        <option value="all">All buildings</option>
        {buildings.map((b) => <option key={b} value={b}>{b}</option>)}
      </select>
      <table className="table">
        <thead><tr><th>Room</th><th>Building</th><th>Type</th><th>Seats</th><th>Status</th><th></th></tr></thead>
        <tbody>
          {shown.map((r) => (
            <tr key={r.id}>
              <td>{r.name}</td><td>{r.building}</td><td>{r.type.replace("_", " ")}</td><td>{r.capacity}</td>
              <td><Badge tone={r.status === "available" ? "green" : "red"}>{r.status === "available" ? "available" : "out of service"}</Badge></td>
              <td>
                {r.status === "available" ? (
                  <button className="danger" disabled={busy} onClick={() => setStatus(r, "unusable")}>Mark out of service</button>
                ) : (
                  <button className="ghost" disabled={busy} onClick={() => setStatus(r, "available")}>Mark available</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
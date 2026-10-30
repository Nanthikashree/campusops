import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import Badge from "../components/Badge.jsx";
import Stepper from "../components/Stepper.jsx";
import ApprovalLevels from "../components/ApprovalLevels.jsx";
import ImpactPanel from "../components/ImpactPanel.jsx";
import PhotoPicker from "../components/PhotoPicker.jsx";
import PhotoGallery from "../components/PhotoGallery.jsx";
import { fmt, label, STATUS_TONE, PRIORITY_TONE, SLA_TONE } from "../util.js";

const MANAGERS = ["facilities_admin", "department_manager", "system_admin"];

export default function TicketDetail() {
  const { id } = useParams();
  const { call, user } = useAuth();
  const [t, setT] = useState(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [comment, setComment] = useState("");
  const [rating, setRating] = useState(5);
  const [note, setNote] = useState("");
  const [apNote, setApNote] = useState("");
  const [parts, setParts] = useState([]);
  const [partId, setPartId] = useState("");
  const [qty, setQty] = useState(1);
  const [preview, setPreview] = useState(null);
  const [impact, setImpact] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [complaintQ, setComplaintQ] = useState([]);
  const [beforeQ, setBeforeQ] = useState([]);
  const [afterQ, setAfterQ] = useState([]);

  const isManager = MANAGERS.includes(user.role);

  async function load() {
    try {
      const data = await call(`/api/tickets/${id}`);
      setT(data);

      try {
        setPhotos(await call(`/api/tickets/${id}/attachments`));
      } catch {
        setPhotos([]);
      }

      if (isManager && ["new", "triaged", "assigned"].includes(data.status)) {
        setPreview(await call(`/api/tickets/${id}/assignment-preview`));
      } else {
        setPreview(null);
      }

      if (isManager && data.room) {
        try {
          setImpact(await call(`/api/tickets/${id}/impact`));
        } catch {
          setImpact(null);
        }
      } else {
        setImpact(null);
      }

      const mineNow = user.role === "technician" && data.assignee_id === user.id;
      if ((mineNow || isManager) && ["assigned", "in_progress", "blocked"].includes(data.status)) {
        const p = await call("/api/parts");
        setParts(p);
        setPartId((cur) => cur || (p.length ? String(p[0].id) : ""));
      }
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  async function act(path, body, okText) {
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const r = await call(path, { method: "POST", body });
      setMsg(okText || (r && r.message) || "Done");
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function uploadPhotos(kind, queue, clear) {
    setBusy(true);
    setError("");
    setMsg("");
    try {
      for (const d of queue) {
        await call(`/api/tickets/${id}/attachments`, { method: "POST", body: { kind, data_url: d } });
      }
      clear([]);
      setMsg(`${queue.length} photo(s) uploaded`);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function moveBooking(bookingId, roomId) {
    await act(`/api/bookings/${bookingId}/move`, { room_id: roomId }, "Booking moved to the new room");
  }

  async function decide(approvalId, decision) {
    await act(`/api/approvals/${approvalId}/decide`, { decision, note: apNote });
    setApNote("");
  }

  if (error && !t) return <p className="error">{error}</p>;
  if (!t) return <p>Loading...</p>;

  const mine = user.role === "technician" && t.assignee_id === user.id;
  const canPart = (mine || isManager) && ["assigned", "in_progress", "blocked"].includes(t.status);
  const count = (k) => photos.filter((p) => p.kind === k).length;
  const nBefore = count("before");
  const nAfter = count("after");
  const nComplaint = count("complaint");
  const photosReady = nBefore > 0 && nAfter > 0;

  return (
    <div>
      <div className="page-head">
        <h2>#{t.id} {t.title}</h2>
      </div>

      <div className="card">
        <Badge tone={STATUS_TONE[t.status]}>{label(t.status)}</Badge>{" "}
        <Badge tone={PRIORITY_TONE[t.priority]}>{t.priority}</Badge>{" "}
        <Badge tone={SLA_TONE[t.sla.state]}>deadline: {label(t.sla.state)}</Badge>
        <div className="row" style={{ marginTop: 14 }}>
          <div><div className="small">Location</div>{t.room || "-"}</div>
          <div><div className="small">Item</div>{t.asset || "-"}</div>
          <div><div className="small">Reported by</div>{t.reporter}</div>
          <div><div className="small">Assigned to</div>{t.assignee || "Not yet"}</div>
          <div><div className="small">Waiting for</div>{t.waiting_for || (t.status === "closed" ? "Nobody, request closed" : "-")}</div>
        </div>
        {t.sla.minutes_left !== null && (
          <p className="small">
            Deadline {fmt(t.sla.deadline)} ({t.sla.minutes_left > 0 ? `${Math.round(t.sla.minutes_left / 60)} h left` : "passed"})
          </p>
        )}
      </div>

      {msg && <div className="notice">{msg}</div>}
      {error && <p className="error">{error}</p>}

      {photos.length > 0 && (
        <div className="card">
          <h3>Photos</h3>
          <PhotoGallery items={photos} />
        </div>
      )}

      {/* Reporter: add more photos */}
      {user.portal === "user" && t.status !== "closed" && nComplaint < 3 && (
        <div className="card">
          <h3>Add photos to your request</h3>
          <PhotoPicker value={complaintQ} onChange={setComplaintQ} max={3 - nComplaint} />
          {complaintQ.length > 0 && (
            <button disabled={busy} onClick={() => uploadPhotos("complaint", complaintQ, setComplaintQ)}>
              Upload {complaintQ.length} photo(s)
            </button>
          )}
        </div>
      )}

      {/* Manager: choose a technician */}
      {isManager && preview && (
        <div className="card">
          <h3>Assign a technician</h3>
          <p className="muted">
            Skill needed: <b>{preview.needed_skill}</b>.{" "}
            {preview.recommended ? <>Recommended: <b>{preview.recommended}</b></> : "Nobody is free right now."}
          </p>
          <table className="table">
            <thead><tr><th>Technician</th><th>Score</th><th>Why</th><th></th></tr></thead>
            <tbody>
              {preview.ranking.map((r) => (
                <tr key={r.technician_id} style={{ opacity: r.eligible ? 1 : 0.55 }}>
                  <td>{r.name}<div className="small">{r.skills.join(", ")}</div></td>
                  <td>{r.eligible ? r.score : "-"}</td>
                  <td className="small">{r.why.join("; ")}</td>
                  <td>
                    {r.eligible && (
                      <button disabled={busy} onClick={() => act(`/api/tickets/${id}/assign`, { technician_id: r.technician_id }, `Assigned to ${r.name}`)}>
                        Assign
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {preview.recommended && (
            <button disabled={busy} onClick={() => act(`/api/tickets/${id}/assign`, {}, "Assigned to the best match")}>
              Assign best match
            </button>
          )}
        </div>
      )}

      {/* Technician: start */}
      {mine && t.status === "assigned" && (
        <div className="card">
          <h3>Your job</h3>
          <p className="muted">Take a before photo below, then press start when you begin.</p>
          <button disabled={busy} onClick={() => act(`/api/tickets/${id}/start`, undefined, "Work started")}>Start work</button>
        </div>
      )}

      {/* Technician: before and after photos */}
      {mine && ["assigned", "in_progress", "blocked"].includes(t.status) && (
        <div className="card">
          <h3>Work photos</h3>
          <p className="muted">A photo of the problem before you start and of the finished work are both needed to complete the job.</p>
          <div className="row">
            <div>
              <label>Before the work ({nBefore} uploaded)</label>
              <PhotoPicker value={beforeQ} onChange={setBeforeQ} max={3 - nBefore} label="Add before photo" />
              {beforeQ.length > 0 && (
                <button disabled={busy} onClick={() => uploadPhotos("before", beforeQ, setBeforeQ)}>
                  Upload {beforeQ.length} before photo(s)
                </button>
              )}
            </div>
            {t.status === "in_progress" && (
              <div>
                <label>After the work ({nAfter} uploaded)</label>
                <PhotoPicker value={afterQ} onChange={setAfterQ} max={3 - nAfter} label="Add after photo" />
                {afterQ.length > 0 && (
                  <button disabled={busy} onClick={() => uploadPhotos("after", afterQ, setAfterQ)}>
                    Upload {afterQ.length} after photo(s)
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Technician or manager: parts */}
      {canPart && (
        <div className="card">
          <h3>Parts</h3>
          <div className="row">
            <div>
              <label>Part</label>
              <select value={partId} onChange={(e) => setPartId(e.target.value)}>
                {parts.map((p) => <option key={p.id} value={p.id}>{p.name} (available {p.available})</option>)}
              </select>
            </div>
            <div>
              <label>Quantity</label>
              <input type="number" min="1" max="50" value={qty} onChange={(e) => setQty(e.target.value)} />
            </div>
          </div>
          <button disabled={busy || !partId} onClick={() => act(`/api/tickets/${id}/parts`, { part_id: Number(partId), quantity: Number(qty) })}>
            Reserve part
          </button>
          <div className="small">If the part is out of stock, the job is blocked and a purchase request starts the approval levels.</div>
        </div>
      )}

      {/* Technician: finish */}
      {mine && t.status === "in_progress" && (
        <div className="card">
          <h3>Finish the job</h3>
          {!photosReady && (
            <div className="notice">
              Before you can complete this job, upload at least one before photo ({nBefore}) and one after photo ({nAfter}) in the Work photos card above.
            </div>
          )}
          <label>What did you do? (signed with your name and the time)</label>
          <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Replaced the capacitor, tested the AC, cooling is normal" />
          <button
            disabled={busy || note.trim().length < 3 || !photosReady}
            onClick={async () => {
              await act(`/api/tickets/${id}/complete`, { note: note.trim() }, "Marked as complete. The reporter will be asked to confirm.");
              setNote("");
            }}
          >
            Mark as complete
          </button>
        </div>
      )}

      {/* Reporter: confirm */}
      {t.status === "resolved" && user.portal === "user" && (
        <div className="notice">
          <b>The technician says this is fixed. Check the before and after photos above. Is it fixed?</b>
          <input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional comment" />
          <label>Rating</label>
          <select value={rating} onChange={(e) => setRating(e.target.value)}>
            {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} / 5</option>)}
          </select>
          <button onClick={() => act(`/api/tickets/${id}/verify`, { fixed: true, comment, rating: Number(rating) }, "Thank you. Request closed.")}>
            Yes, it is fixed
          </button>
          <button className="danger" onClick={() => act(`/api/tickets/${id}/verify`, { fixed: false, comment }, "Reopened. The technician was told.")}>
            No, still broken
          </button>
        </div>
      )}

      {/* Manager: impact on classes and exams */}
      {isManager && impact && impact.room && (
        <div className="card">
          <h3>Impact on classes and exams</h3>
          <p className="muted">
            Upcoming bookings in room {impact.room}
            {impact.room_status === "unusable" ? " (out of service)" : ""}.
          </p>
          <ImpactPanel affected={impact.affected} onMove={moveBooking} busy={busy} />
        </div>
      )}

      <div className="two-col">
        <div className="card">
          <h3>Progress</h3>
          <Stepper steps={t.workflow} />
        </div>
        <div className="card">
          <h3>Job card (signed record)</h3>
          <ul className="timeline">
            {t.job_card.map((e, i) => (
              <li key={i}>
                <b>{label(e.event)}</b> <span className="small">{fmt(e.at)}</span>
                <div>{e.note}</div>
                <div className="small">{e.by} ({label(e.role)})</div>
              </li>
            ))}
          </ul>
          <Badge tone={t.log_intact ? "green" : "red"}>
            {t.log_intact ? "Record verified: no entry was altered" : "Warning: the record was altered"}
          </Badge>
        </div>
      </div>

      {/* Approval levels, with buttons for whoever's turn it is */}
      {t.approvals.map((a) => (
        <div className="card" key={a.id}>
          <h3>Purchase approval #{a.id}: {a.quantity} x {a.part} (Rs {a.amount.toLocaleString()})</h3>
          <ApprovalLevels steps={a.steps} />
          {a.can_decide && (
            <div style={{ marginTop: 12 }}>
              <input value={apNote} onChange={(e) => setApNote(e.target.value)} placeholder="Remarks (optional)" />
              <button disabled={busy} onClick={() => decide(a.id, "approve")}>Approve</button>
              <button className="danger" disabled={busy} onClick={() => decide(a.id, "reject")}>Reject</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
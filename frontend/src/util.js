export function fmt(s) {
  if (!s) return "";
  const hasZone = /[zZ]$|[+-]\d\d:\d\d$/.test(s);
  const d = new Date(hasZone ? s : s + "Z");
  return d.toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export const label = (s) => (s || "").replace(/_/g, " ");

export const STATUS_TONE = { new: "blue", triaged: "blue", assigned: "blue", in_progress: "amber", blocked: "red", resolved: "green", closed: "gray" };
export const PRIORITY_TONE = { low: "gray", medium: "blue", high: "amber", critical: "red" };
export const SLA_TONE = { on_track: "green", at_risk: "amber", breached: "red", met: "green", missed: "red" };
export const ROLE_LABEL = { student_faculty: "Student / Faculty", technician: "Technician", department_manager: "Department Manager", facilities_admin: "Facilities Administrator", procurement_approver: "Procurement Approver", system_admin: "System Administrator" };
// Booking times have no time zone, so they are shown exactly as stored.
export function fmtNaive(s) {
  if (!s) return "";
  return new Date(s).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function fmtTime(s) {
  if (!s) return "";
  return new Date(s).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
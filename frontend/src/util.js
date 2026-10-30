export function fmt(s) {
  if (!s) return "";
  const hasZone = /[zZ]$|[+-]\d\d:\d\d$/.test(s);
  const d = new Date(hasZone ? s : s + "Z");
  return d.toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

// Booking and slot times have no time zone, so they are shown exactly as stored.
export function fmtNaive(s) {
  if (!s) return "";
  return new Date(s).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function fmtTime(s) {
  if (!s) return "";
  return new Date(s).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export const label = (s) => (s || "").replace(/_/g, " ");

export const STATUS_TONE = { new: "blue", triaged: "blue", assigned: "blue", in_progress: "amber", blocked: "red", resolved: "green", closed: "gray" };
export const PRIORITY_TONE = { low: "gray", medium: "blue", high: "amber", critical: "red" };
export const SLA_TONE = { on_track: "green", at_risk: "amber", breached: "red", met: "green", missed: "red" };

export const ROLE_LABEL = {
  student_faculty: "Student / Faculty",
  technician: "Technician",
  department_manager: "Department Manager",
  facilities_admin: "Facilities Administrator",
  procurement_approver: "Procurement Approver",
  system_admin: "System Administrator",
};

// Shrinks a photo in the browser so uploads are quick, and returns it as a JPEG data URL.
export function fileToDataUrl(file, maxSide = 1280, quality = 0.8) {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith("image/")) return reject(new Error("Please choose an image file"));
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/jpeg", quality));
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("That image could not be read. Try a JPEG or PNG."));
    };
    img.src = url;
  });
}
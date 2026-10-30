const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function api(path, { method = "GET", body, token } = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    // some responses have no body
  }
  if (!res.ok) {
    const d = data && data.detail;
    let msg = `Request failed (${res.status})`;
    if (typeof d === "string") msg = d;
    else if (Array.isArray(d)) msg = d.map((x) => x.msg).join(", ");
    else if (d && d.message) msg = d.message;
    const err = new Error(msg);
    err.status = res.status;
    err.data = d;
    throw err;
  }
  return data;
}

export async function apiBlob(path, token) {
  const res = await fetch(BASE + path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) throw new Error(`Could not load the image (${res.status})`);
  return await res.blob();
}
import { createContext, useContext, useState } from "react";
import { api, apiBlob } from "./api.js";

const Ctx = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("session"));
    } catch {
      return null;
    }
  });

  async function login(email, password) {
    const data = await api("/api/auth/login", { method: "POST", body: { email, password } });
    localStorage.setItem("session", JSON.stringify(data));
    setSession(data);
    return data.user;
  }

  function logout() {
    localStorage.removeItem("session");
    setSession(null);
  }

  // Every call attaches the token. An expired login sends you back to the login page.
  async function call(path, opts = {}) {
    try {
      return await api(path, { ...opts, token: session?.token });
    } catch (e) {
      if (e.status === 401) logout();
      throw e;
    }
  }

  const callBlob = (path) => apiBlob(path, session?.token);

  return (
    <Ctx.Provider value={{ user: session?.user || null, login, logout, call, callBlob }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
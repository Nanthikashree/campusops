import { useEffect, useState } from "react";
import { NavLink, Link } from "react-router-dom";
import { Bell, LogOut } from "lucide-react";
import { useAuth } from "../auth.jsx";
import { NAV } from "../nav.js";
import { ROLE_LABEL } from "../util.js";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function Layout({ children }) {
  const { user, logout, call } = useAuth();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let alive = true;
    const load = () => call("/api/notifications").then((d) => alive && setUnread(d.unread)).catch(() => {});
    load();
    const id = setInterval(load, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const items = NAV[user.portal].filter((i) => !i.roles || i.roles.includes(user.role));
  const initials = user.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">C</div>
          <span>CampusOps</span>
        </div>
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => "navitem" + (isActive ? " active" : "")}>
              <Icon size={18} />
              <span>{item.text}</span>
              {item.to === "/notifications" && unread > 0 && <span className="count">{unread}</span>}
            </NavLink>
          );
        })}
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <div className="hello">{greeting()}, {user.name}</div>
            <div className="small">{new Date().toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })}</div>
          </div>
          <div className="topbar-right">
            <Link to="/notifications" className="bell">
              <Bell size={18} />
              {unread > 0 && <span className="dot">{unread}</span>}
            </Link>
            <div className="avatar">{initials}</div>
            <div className="who">
              <div style={{ fontWeight: 600 }}>{user.name}</div>
              <div className="small">{ROLE_LABEL[user.role]}</div>
            </div>
            <button className="ghost" onClick={logout}><LogOut size={16} /> Log out</button>
          </div>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
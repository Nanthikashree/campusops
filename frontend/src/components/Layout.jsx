import { useEffect, useState } from "react";
import { NavLink, Link } from "react-router-dom";
import { Bell, LogOut } from "lucide-react";
import { useAuth } from "../auth.jsx";
import { NAV } from "../nav.js";
import { BRAND } from "../brand.js";
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

  const items = NAV[user.portal].filter(
    (i) => (!i.roles || i.roles.includes(user.role)) && (!i.types || i.types.includes(user.user_type))
  );
  const initials = user.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const roleText = ROLE_LABEL[user.role] || user.role;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">{BRAND.app[0]}</div>
          <div>
            <div className="brand-name">{BRAND.app}</div>
            <div className="brand-sub">{BRAND.college}</div>
          </div>
        </div>

        <div className="nav-label">Menu</div>
        <nav className="nav">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => "navitem" + (isActive ? " active" : "")}>
                <Icon size={19} />
                <span>{item.text}</span>
                {item.to === "/notifications" && unread > 0 && <span className="count">{unread}</span>}
              </NavLink>
            );
          })}
        </nav>

        <div className="side-user">
          <div className="avatar">{initials}</div>
          <div className="info">
            <div className="who-name">{user.name}</div>
            <div className="who-role">{roleText}</div>
          </div>
          <button className="icon-btn" title="Log out" onClick={logout}><LogOut size={18} /></button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="hello">{greeting()}, {user.name}</div>
            <div className="date">
              {new Date().toLocaleDateString([], { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
            </div>
          </div>
          <div className="topbar-right">
            <span className="role-chip">{roleText}</span>
            <Link to="/notifications" className="bell" title="Notifications">
              <Bell size={19} />
              {unread > 0 && <span className="dot">{unread}</span>}
            </Link>
          </div>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
import { LayoutDashboard, FilePlus2, ClipboardList, Bell, ShieldCheck } from "lucide-react";

const APPROVAL_ROLES = ["procurement_approver", "facilities_admin", "department_manager", "system_admin"];

export const NAV = {
  user: [
    { to: "/", text: "Raise a request", icon: FilePlus2 },
    { to: "/tickets", text: "My requests", icon: ClipboardList },
    { to: "/notifications", text: "Notifications", icon: Bell },
  ],
  admin: [
    { to: "/", text: "Dashboard", icon: LayoutDashboard },
    { to: "/tickets", text: "Requests", icon: ClipboardList },
    { to: "/approvals", text: "Approvals", icon: ShieldCheck, roles: APPROVAL_ROLES },
    { to: "/notifications", text: "Notifications", icon: Bell },
  ],
};
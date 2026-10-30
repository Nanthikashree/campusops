import { LayoutDashboard, FilePlus2, ClipboardList, Bell, ShieldCheck, ListChecks, CalendarDays, DoorOpen, CalendarCheck, PlayCircle, BarChart3, LayoutGrid } from "lucide-react";

const MANAGER_ROLES = ["facilities_admin", "department_manager", "system_admin"];
const APPROVAL_ROLES = ["department_manager", "procurement_approver", "system_admin", "facilities_admin"];
const STAFF_ROLES = ["technician", ...MANAGER_ROLES, "procurement_approver"];

export const NAV = {
  user: [
    { to: "/", text: "Raise a request", icon: FilePlus2 },
    { to: "/tickets", text: "My requests", icon: ClipboardList },
    { to: "/slots", text: "Exams and events", icon: CalendarCheck, types: ["student"] },
    { to: "/notifications", text: "Notifications", icon: Bell },
  ],
  admin: [
    { to: "/", text: "Dashboard", icon: LayoutDashboard, roles: MANAGER_ROLES },
    { to: "/tasks", text: "My tasks", icon: ListChecks, roles: STAFF_ROLES },
    { to: "/tickets", text: "Requests", icon: ClipboardList, roles: [...MANAGER_ROLES, "technician"] },
    { to: "/slots", text: "Slots", icon: CalendarCheck, roles: MANAGER_ROLES },
    { to: "/board", text: "Room board", icon: LayoutGrid, roles: MANAGER_ROLES },
    { to: "/bookings", text: "Timetable", icon: CalendarDays, roles: MANAGER_ROLES },
    { to: "/rooms", text: "Rooms", icon: DoorOpen, roles: MANAGER_ROLES },
    { to: "/analytics", text: "Analytics", icon: BarChart3, roles: MANAGER_ROLES },
    { to: "/approvals", text: "Approvals", icon: ShieldCheck, roles: APPROVAL_ROLES },
    { to: "/demo", text: "Demo", icon: PlayCircle, roles: ["facilities_admin", "system_admin"] },
    { to: "/notifications", text: "Notifications", icon: Bell },
  ],
};
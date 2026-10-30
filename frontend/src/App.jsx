import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Raise from "./pages/Raise.jsx";
import TicketList from "./pages/TicketList.jsx";
import TicketDetail from "./pages/TicketDetail.jsx";
import Notifications from "./pages/Notifications.jsx";
import AdminHome from "./pages/AdminHome.jsx";
import Approvals from "./pages/Approvals.jsx";
import MyTasks from "./pages/MyTasks.jsx";
import Bookings from "./pages/Bookings.jsx";
import Rooms from "./pages/Rooms.jsx";
import RoomBoard from "./pages/RoomBoard.jsx";
import Slots from "./pages/Slots.jsx";
import ManageSlots from "./pages/ManageSlots.jsx";
import Demo from "./pages/Demo.jsx";
import Analytics from "./pages/Analytics.jsx";

const MANAGERS = ["facilities_admin", "department_manager", "system_admin"];
const DEMO_ROLES = ["facilities_admin", "system_admin"];

export default function App() {
  const { user } = useAuth();
  if (!user) return <Login />;
  const admin = user.portal === "admin";
  const manager = MANAGERS.includes(user.role);
  const tasksHome = ["technician", "procurement_approver"].includes(user.role);
  const home = !admin ? <Raise /> : tasksHome ? <Navigate to="/tasks" replace /> : <AdminHome />;
  const slotsPage = manager ? <ManageSlots /> : user.role === "student_faculty" ? <Slots /> : <Navigate to="/" replace />;

  return (
    <Layout>
      <Routes>
        <Route path="/" element={home} />
        <Route path="/tasks" element={admin ? <MyTasks /> : <Navigate to="/" replace />} />
        <Route path="/tickets" element={<TicketList />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route path="/slots" element={slotsPage} />
        <Route path="/board" element={manager ? <RoomBoard /> : <Navigate to="/" replace />} />
        <Route path="/bookings" element={manager ? <Bookings /> : <Navigate to="/" replace />} />
        <Route path="/rooms" element={manager ? <Rooms /> : <Navigate to="/" replace />} />
        <Route path="/analytics" element={manager ? <Analytics /> : <Navigate to="/" replace />} />
        <Route path="/demo" element={DEMO_ROLES.includes(user.role) ? <Demo /> : <Navigate to="/" replace />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/approvals" element={admin ? <Approvals /> : <Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
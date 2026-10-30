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

export default function App() {
  const { user } = useAuth();
  if (!user) return <Login />;
  const admin = user.portal === "admin";
  const tasksHome = ["technician", "procurement_approver"].includes(user.role);
  const home = !admin ? <Raise /> : tasksHome ? <Navigate to="/tasks" replace /> : <AdminHome />;

  return (
    <Layout>
      <Routes>
        <Route path="/" element={home} />
        <Route path="/tasks" element={admin ? <MyTasks /> : <Navigate to="/" replace />} />
        <Route path="/tickets" element={<TicketList />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/approvals" element={admin ? <Approvals /> : <Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
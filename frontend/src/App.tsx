// All pages of the app. If you are not logged in, you see the login page.
import { Route, Routes } from "react-router-dom";

import { getToken } from "./api";
import Layout from "./components/Layout";
import Applications from "./pages/Applications";
import Automation from "./pages/Automation";
import Dashboard from "./pages/Dashboard";
import Interview from "./pages/Interview";
import JobBoards from "./pages/JobBoards";
import JobDetail from "./pages/JobDetail";
import Jobs from "./pages/Jobs";
import Login from "./pages/Login";
import Recruiters from "./pages/Recruiters";
import Settings from "./pages/Settings";
import Strategy from "./pages/Strategy";

export default function App() {
  if (!getToken()) return <Login />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/jobs/:id" element={<JobDetail />} />
        <Route path="/jobs/:id/interview" element={<Interview />} />
        <Route path="/strategy" element={<Strategy />} />
        <Route path="/job-boards" element={<JobBoards />} />
        <Route path="/applications" element={<Applications />} />
        <Route path="/recruiters" element={<Recruiters />} />
        <Route path="/automation" element={<Automation />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}

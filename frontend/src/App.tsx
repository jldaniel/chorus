import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ProjectList from "./views/ProjectList";
import ProjectLayout from "./views/ProjectLayout";
import TaskTreeView from "./views/TaskTreeView";
import KanbanBoard from "./views/KanbanBoard";
import LockMonitor from "./views/LockMonitor";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<ProjectList />} />
        <Route path="projects/:projectId" element={<ProjectLayout />}>
          <Route index element={<Navigate to="tree" replace />} />
          <Route path="tree" element={<TaskTreeView />} />
          <Route path="kanban" element={<KanbanBoard />} />
          <Route path="locks" element={<LockMonitor />} />
        </Route>
      </Route>
    </Routes>
  );
}

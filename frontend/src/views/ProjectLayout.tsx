import { useState, useCallback, useEffect } from "react";
import {
  NavLink,
  Outlet,
  useParams,
  useOutletContext,
} from "react-router-dom";
import { useProject } from "../api/hooks";
import Spinner from "../components/Spinner";
import ErrorMessage from "../components/ErrorMessage";
import TaskDetailPanel from "../components/TaskDetailPanel";

type ContextType = {
  selectTask: (id: string) => void;
};

// eslint-disable-next-line react-refresh/only-export-components
export function useProjectLayoutContext() {
  return useOutletContext<ContextType>();
}

const tabs = [
  { to: "tree", label: "Tree" },
  { to: "kanban", label: "Kanban" },
  { to: "locks", label: "Locks" },
];

export default function ProjectLayout() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading, error, refetch } = useProject(projectId!);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const selectTask = useCallback((id: string) => setSelectedTaskId(id), []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setSelectedTaskId(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (isLoading) return <Spinner />;
  if (error || !project)
    return <ErrorMessage message="Failed to load project" onRetry={refetch} />;

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-4 border-b border-gray-800 px-6 py-3">
        <h2 className="text-lg font-semibold text-white">{project.name}</h2>
        <span className="text-sm text-gray-500">
          {project.task_count} tasks &middot; {project.points_completed}/
          {project.points_total} pts
        </span>
        <nav className="ml-auto flex gap-1">
          {tabs.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              className={({ isActive }) =>
                `rounded px-3 py-1.5 text-sm ${
                  isActive
                    ? "bg-gray-800 text-white"
                    : "text-gray-400 hover:text-gray-200"
                }`
              }
            >
              {t.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <div className="relative flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          <Outlet context={{ selectTask } satisfies ContextType} />
        </div>
        {selectedTaskId && (
          <TaskDetailPanel
            taskId={selectedTaskId}
            projectId={projectId!}
            onClose={() => setSelectedTaskId(null)}
          />
        )}
      </div>
    </div>
  );
}

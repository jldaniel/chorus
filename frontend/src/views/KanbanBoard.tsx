import { useParams } from "react-router-dom";
import { useProjectTasks, useInProgress } from "../api/hooks";
import { useProjectLayoutContext } from "./ProjectLayout";
import TaskCard from "../components/TaskCard";
import Spinner from "../components/Spinner";
import ErrorMessage from "../components/ErrorMessage";
import type { Status, TaskRead, TaskWithLockInfo } from "../api/types";

const columns: { status: Status; label: string }[] = [
  { status: "todo", label: "To Do" },
  { status: "doing", label: "Doing" },
  { status: "done", label: "Done" },
  { status: "wont_do", label: "Won't Do" },
];

export default function KanbanBoard() {
  const { projectId } = useParams<{ projectId: string }>();
  const { selectTask } = useProjectLayoutContext();
  const { data: tasks, isLoading, error, refetch } = useProjectTasks(projectId!);
  const { data: inProgress } = useInProgress(projectId!);

  if (isLoading) return <Spinner />;
  if (error)
    return <ErrorMessage message="Failed to load tasks" onRetry={refetch} />;

  // Build a map of in-progress tasks with lock info
  const lockMap = new Map<string, TaskWithLockInfo>();
  inProgress?.forEach((t) => lockMap.set(t.id, t));

  // Group all tasks (including nested) by status — for now show root tasks only
  const grouped: Record<Status, (TaskRead | TaskWithLockInfo)[]> = {
    todo: [],
    doing: [],
    done: [],
    wont_do: [],
  };
  tasks?.forEach((t) => {
    const display = lockMap.get(t.id) ?? t;
    grouped[t.status].push(display);
  });

  return (
    <div className="flex h-full gap-4 overflow-x-auto p-4">
      {columns.map(({ status, label }) => (
        <div
          key={status}
          className="flex w-72 shrink-0 flex-col rounded border border-gray-800 bg-gray-900/50"
        >
          <div className="flex items-center justify-between border-b border-gray-800 px-3 py-2">
            <h3 className="text-sm font-medium text-gray-300">{label}</h3>
            <span className="text-xs text-gray-500">
              {grouped[status].length}
            </span>
          </div>
          <div className="flex-1 space-y-2 overflow-y-auto p-2">
            {grouped[status].length === 0 && (
              <p className="py-4 text-center text-xs text-gray-600">
                No tasks
              </p>
            )}
            {grouped[status].map((t) => (
              <TaskCard
                key={t.id}
                task={t}
                onClick={() => selectTask(t.id)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

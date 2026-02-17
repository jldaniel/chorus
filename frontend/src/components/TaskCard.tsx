import { ReadinessBadge } from "./Badge";
import type { TaskRead, TaskWithLockInfo } from "../api/types";

interface Props {
  task: TaskRead | TaskWithLockInfo;
  onClick: () => void;
}

function hasLockInfo(t: TaskRead | TaskWithLockInfo): t is TaskWithLockInfo {
  return "lock_caller_label" in t;
}

export default function TaskCard({ task, onClick }: Props) {
  return (
    <div
      onClick={onClick}
      className="cursor-pointer rounded border border-gray-700 bg-gray-800 p-3 hover:border-gray-600"
    >
      <p className="text-sm font-medium text-gray-200">{task.name}</p>
      <div className="mt-2 flex items-center gap-2">
        <ReadinessBadge readiness={task.readiness} />
        {task.effective_points != null && (
          <span className="text-xs text-gray-500">
            {task.effective_points}pt
          </span>
        )}
        {task.is_locked && hasLockInfo(task) && task.lock_caller_label && (
          <span className="text-xs text-yellow-500" title={`Locked by ${task.lock_caller_label}`}>
            &#128274; {task.lock_caller_label}
          </span>
        )}
        {task.is_locked && !hasLockInfo(task) && (
          <span className="text-xs text-yellow-500">&#128274;</span>
        )}
      </div>
    </div>
  );
}

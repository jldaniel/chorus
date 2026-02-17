import { useState } from "react";
import { useTaskTree } from "../api/hooks";
import { ReadinessBadge } from "./Badge";
import type { TaskRead, TaskTreeNode } from "../api/types";

const statusDots: Record<string, string> = {
  todo: "bg-gray-500",
  doing: "bg-blue-400",
  done: "bg-green-400",
  wont_do: "bg-gray-600",
};

interface Props {
  task: TaskRead;
  depth: number;
  onSelect: (id: string) => void;
}

export default function TaskTreeRow({ task, depth, onSelect }: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasChildren = task.children_count > 0;
  const { data: tree } = useTaskTree(task.id, expanded && hasChildren);
  const children: TaskTreeNode[] = tree?.children ?? [];

  return (
    <>
      <div
        className="flex cursor-pointer items-center gap-2 border-b border-gray-800/50 px-4 py-2 hover:bg-gray-800/50"
        style={{ paddingLeft: `${depth * 20 + 16}px` }}
        onClick={() => onSelect(task.id)}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="w-4 text-center text-xs text-gray-500 hover:text-gray-300"
          >
            {expanded ? "\u25BC" : "\u25B6"}
          </button>
        ) : (
          <span className="w-4" />
        )}
        <span className={`h-2 w-2 rounded-full ${statusDots[task.status]}`} />
        <span className="flex-1 truncate text-sm text-gray-200">
          {task.name}
        </span>
        <ReadinessBadge readiness={task.readiness} />
        {task.effective_points != null && (
          <span className="text-xs text-gray-500">
            {task.effective_points}pt
          </span>
        )}
        {hasChildren && (
          <span className="text-xs text-gray-600">
            {task.children_count} sub
          </span>
        )}
        {task.is_locked && (
          <span className="text-xs text-yellow-500" title="Locked">
            &#128274;
          </span>
        )}
      </div>
      {expanded &&
        children.map((child) => (
          <TaskTreeRow
            key={child.id}
            task={child}
            depth={depth + 1}
            onSelect={onSelect}
          />
        ))}
    </>
  );
}

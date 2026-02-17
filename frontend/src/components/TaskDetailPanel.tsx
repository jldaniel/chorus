import { useState } from "react";
import {
  useTask,
  useUpdateTask,
  useUpdateStatus,
  useDeleteTask,
  useFlagRefinement,
  useCreateSubtask,
} from "../api/hooks";
import { ReadinessBadge, StatusBadge, TaskTypeBadge } from "./Badge";
import Spinner from "./Spinner";
import WorkLogTimeline from "./WorkLogTimeline";
import CommitList from "./CommitList";
import type { Status, TaskType } from "../api/types";
import type { FormEvent } from "react";

const statusTransitions: Record<Status, Status[]> = {
  todo: ["doing", "wont_do"],
  doing: ["done", "todo", "wont_do"],
  done: ["todo", "wont_do"],
  wont_do: ["todo"],
};

const statusLabels: Record<Status, string> = {
  todo: "To do",
  doing: "Doing",
  done: "Done",
  wont_do: "Won't do",
};

type Tab = "details" | "worklog" | "commits";

interface Props {
  taskId: string;
  projectId: string;
  onClose: () => void;
}

export default function TaskDetailPanel({ taskId, projectId, onClose }: Props) {
  const { data: task, isLoading } = useTask(taskId);
  const updateTask = useUpdateTask(taskId, projectId);
  const updateStatus = useUpdateStatus(taskId, projectId);
  const deleteTask = useDeleteTask(projectId);
  const flagRefinement = useFlagRefinement(taskId, projectId);
  const createSubtask = useCreateSubtask(taskId, projectId);
  const [tab, setTab] = useState<Tab>("details");
  const [editName, setEditName] = useState<string | null>(null);
  const [editDesc, setEditDesc] = useState<string | null>(null);
  const [editContext, setEditContext] = useState<string | null>(null);
  const [subtaskName, setSubtaskName] = useState("");
  const [subtaskType, setSubtaskType] = useState<TaskType>("feature");

  if (isLoading || !task)
    return (
      <div className="w-96 border-l border-gray-800 bg-gray-900">
        <Spinner />
      </div>
    );

  function saveField(field: "name" | "description" | "context", value: string) {
    updateTask.mutate({ [field]: value || null });
    if (field === "name") setEditName(null);
    if (field === "description") setEditDesc(null);
    if (field === "context") setEditContext(null);
  }

  return (
    <div className="flex w-96 flex-col border-l border-gray-800 bg-gray-900 max-sm:absolute max-sm:inset-0 max-sm:w-full">
      {/* Header */}
      <div className="flex items-start gap-2 border-b border-gray-800 p-4">
        <div className="min-w-0 flex-1">
          {editName !== null ? (
            <input
              autoFocus
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={() => saveField("name", editName)}
              onKeyDown={(e) => {
                if (e.key === "Enter") saveField("name", editName);
                if (e.key === "Escape") setEditName(null);
              }}
              className="w-full rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm font-semibold text-white focus:outline-none"
            />
          ) : (
            <h3
              className="cursor-pointer truncate font-semibold text-white"
              onClick={() => setEditName(task.name)}
            >
              {task.name}
            </h3>
          )}
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            <StatusBadge status={task.status} />
            <ReadinessBadge readiness={task.readiness} />
            <TaskTypeBadge taskType={task.task_type} />
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300"
        >
          &#x2715;
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 text-sm">
        {(["details", "worklog", "commits"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 capitalize ${
              tab === t
                ? "border-b-2 border-indigo-500 text-white"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {t === "worklog" ? "Work log" : t}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {tab === "details" && (
          <div className="space-y-4 p-4">
            {/* Description */}
            <div>
              <label className="text-xs font-medium uppercase text-gray-500">
                Description
              </label>
              {editDesc !== null ? (
                <textarea
                  autoFocus
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  onBlur={() => saveField("description", editDesc)}
                  rows={4}
                  className="mt-1 w-full rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-300 focus:outline-none"
                />
              ) : (
                <p
                  className="mt-1 cursor-pointer whitespace-pre-wrap text-sm text-gray-300"
                  onClick={() => setEditDesc(task.description ?? "")}
                >
                  {task.description || (
                    <span className="italic text-gray-600">
                      Click to add description
                    </span>
                  )}
                </p>
              )}
            </div>

            {/* Context */}
            <div>
              <label className="text-xs font-medium uppercase text-gray-500">
                Context
              </label>
              {editContext !== null ? (
                <textarea
                  autoFocus
                  value={editContext}
                  onChange={(e) => setEditContext(e.target.value)}
                  onBlur={() => saveField("context", editContext)}
                  rows={3}
                  className="mt-1 w-full rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-300 focus:outline-none"
                />
              ) : (
                <p
                  className="mt-1 cursor-pointer whitespace-pre-wrap text-sm text-gray-300"
                  onClick={() => setEditContext(task.context ?? "")}
                >
                  {task.context || (
                    <span className="italic text-gray-600">
                      Click to add context
                    </span>
                  )}
                </p>
              )}
            </div>

            {/* Task Type */}
            <div>
              <label className="text-xs font-medium uppercase text-gray-500">
                Type
              </label>
              <select
                value={task.task_type}
                onChange={(e) =>
                  updateTask.mutate({
                    task_type: e.target.value as TaskType,
                  })
                }
                className="mt-1 block rounded border border-gray-700 bg-gray-800 px-2 py-1 text-sm text-gray-300"
              >
                <option value="feature">Feature</option>
                <option value="bug">Bug</option>
                <option value="tech_debt">Tech debt</option>
              </select>
            </div>

            {/* Points */}
            <div>
              <label className="text-xs font-medium uppercase text-gray-500">
                Points
              </label>
              <p className="mt-1 text-sm text-gray-300">
                {task.effective_points ?? "Unsized"}
                {task.rolled_up_points != null &&
                  task.rolled_up_points !== task.effective_points && (
                    <span className="ml-2 text-gray-500">
                      (rolled up: {task.rolled_up_points})
                    </span>
                  )}
              </p>
            </div>

            {/* Status transitions */}
            <div>
              <label className="text-xs font-medium uppercase text-gray-500">
                Actions
              </label>
              <div className="mt-1 flex flex-wrap gap-2">
                {statusTransitions[task.status].map((s) => (
                  <button
                    key={s}
                    onClick={() => updateStatus.mutate({ status: s })}
                    disabled={updateStatus.isPending}
                    className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-800"
                  >
                    &rarr; {statusLabels[s]}
                  </button>
                ))}
                {task.readiness !== "needs_refinement" && (
                  <button
                    onClick={() =>
                      flagRefinement.mutate({
                        refinement_notes: "Flagged from UI",
                      })
                    }
                    disabled={flagRefinement.isPending}
                    className="rounded border border-purple-800 px-2 py-1 text-xs text-purple-300 hover:bg-purple-900/30"
                  >
                    Flag refinement
                  </button>
                )}
              </div>
            </div>

            {/* Add subtask */}
            <div>
              <label className="text-xs font-medium uppercase text-gray-500">
                Add subtask
                {task.children_count > 0 && (
                  <span className="ml-1 normal-case text-gray-600">
                    ({task.children_count} existing)
                  </span>
                )}
              </label>
              <form
                className="mt-1 flex gap-2"
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  if (!subtaskName.trim()) return;
                  createSubtask.mutate(
                    { name: subtaskName.trim(), task_type: subtaskType },
                    { onSuccess: () => setSubtaskName("") },
                  );
                }}
              >
                <input
                  value={subtaskName}
                  onChange={(e) => setSubtaskName(e.target.value)}
                  placeholder="Subtask name"
                  className="min-w-0 flex-1 rounded border border-gray-700 bg-gray-800 px-2 py-1 text-sm text-gray-300 placeholder-gray-600 focus:outline-none"
                />
                <select
                  value={subtaskType}
                  onChange={(e) => setSubtaskType(e.target.value as TaskType)}
                  className="rounded border border-gray-700 bg-gray-800 px-2 py-1 text-sm text-gray-300"
                >
                  <option value="feature">Feature</option>
                  <option value="bug">Bug</option>
                  <option value="tech_debt">Tech debt</option>
                </select>
                <button
                  type="submit"
                  disabled={createSubtask.isPending || !subtaskName.trim()}
                  className="rounded bg-indigo-600 px-2 py-1 text-xs text-white hover:bg-indigo-500 disabled:opacity-50"
                >
                  Add
                </button>
              </form>
            </div>

            {/* Delete */}
            <button
              onClick={() => {
                if (confirm(`Delete "${task.name}"?`)) {
                  deleteTask.mutate(task.id);
                  onClose();
                }
              }}
              className="text-xs text-red-500 hover:text-red-400"
            >
              Delete task
            </button>
          </div>
        )}

        {tab === "worklog" && <WorkLogTimeline taskId={taskId} />}
        {tab === "commits" && <CommitList taskId={taskId} />}
      </div>
    </div>
  );
}

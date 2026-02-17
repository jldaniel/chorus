import { useState } from "react";
import { useParams } from "react-router-dom";
import { useProjectTasks, useCreateTask } from "../api/hooks";
import { useProjectLayoutContext } from "./ProjectLayout";
import TaskTreeRow from "../components/TaskTreeRow";
import Spinner from "../components/Spinner";
import ErrorMessage from "../components/ErrorMessage";
import type { TaskType } from "../api/types";

export default function TaskTreeView() {
  const { projectId } = useParams<{ projectId: string }>();
  const { selectTask } = useProjectLayoutContext();
  const { data: tasks, isLoading, error, refetch } = useProjectTasks(projectId!);
  const createTask = useCreateTask(projectId!);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState<TaskType>("feature");

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    createTask.mutate(
      { name: newName.trim(), task_type: newType },
      { onSuccess: () => setNewName("") },
    );
  }

  if (isLoading) return <Spinner />;
  if (error)
    return <ErrorMessage message="Failed to load tasks" onRetry={refetch} />;

  return (
    <div className="p-4">
      <form onSubmit={handleCreate} className="mb-4 flex gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New task name"
          className="flex-1 rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-gray-500 focus:outline-none"
        />
        <select
          value={newType}
          onChange={(e) => setNewType(e.target.value as TaskType)}
          className="rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-sm text-gray-300"
        >
          <option value="feature">Feature</option>
          <option value="bug">Bug</option>
          <option value="tech_debt">Tech debt</option>
        </select>
        <button
          type="submit"
          disabled={!newName.trim() || createTask.isPending}
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          Add
        </button>
      </form>

      {tasks && tasks.length === 0 && (
        <p className="text-sm text-gray-500">No tasks yet.</p>
      )}

      <div className="rounded border border-gray-800">
        {tasks?.map((task) => (
          <TaskTreeRow
            key={task.id}
            task={task}
            depth={0}
            onSelect={selectTask}
          />
        ))}
      </div>
    </div>
  );
}

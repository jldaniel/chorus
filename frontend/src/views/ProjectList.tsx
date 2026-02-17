import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProjects, useCreateProject, useDeleteProject } from "../api/hooks";
import Spinner from "../components/Spinner";
import ErrorMessage from "../components/ErrorMessage";

export default function ProjectList() {
  const { data: projects, isLoading, error, refetch } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createProject.mutate(
      { name: name.trim(), description: description.trim() || null },
      {
        onSuccess: (p) => {
          setName("");
          setDescription("");
          navigate(`/projects/${p.id}/tree`);
        },
      },
    );
  }

  if (isLoading) return <Spinner />;
  if (error)
    return <ErrorMessage message="Failed to load projects" onRetry={refetch} />;

  return (
    <div className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-bold text-white">Projects</h1>

      <form onSubmit={handleCreate} className="mt-6 flex flex-col gap-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Project name"
          className="rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-gray-500 focus:outline-none"
        />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          className="rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-gray-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!name.trim() || createProject.isPending}
          className="self-start rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          Create project
        </button>
      </form>

      {projects && projects.length === 0 && (
        <p className="mt-8 text-gray-500">No projects yet. Create one above.</p>
      )}

      <div className="mt-6 space-y-2">
        {projects?.map((p) => (
          <div
            key={p.id}
            onClick={() => navigate(`/projects/${p.id}/tree`)}
            className="flex cursor-pointer items-center justify-between rounded border border-gray-800 bg-gray-900 px-4 py-3 hover:border-gray-700"
          >
            <div>
              <p className="font-medium text-white">{p.name}</p>
              {p.description && (
                <p className="mt-0.5 text-sm text-gray-400">{p.description}</p>
              )}
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>{p.task_count} tasks</span>
              <span>
                {p.points_completed}/{p.points_total} pts
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm(`Delete "${p.name}"?`))
                    deleteProject.mutate(p.id);
                }}
                className="text-gray-600 hover:text-red-400"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

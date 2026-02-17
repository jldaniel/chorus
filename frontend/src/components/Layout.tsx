import { Link, Outlet, useParams } from "react-router-dom";
import { useProjects } from "../api/hooks";

export default function Layout() {
  const { projectId } = useParams();
  const { data: projects } = useProjects();

  return (
    <div className="flex h-screen bg-gray-950 text-gray-200">
      <aside className="flex w-56 flex-col border-r border-gray-800 bg-gray-900">
        <Link
          to="/"
          className="border-b border-gray-800 px-4 py-3 text-lg font-bold tracking-tight text-white"
        >
          Chorus
        </Link>
        <nav className="flex-1 overflow-y-auto p-2">
          <p className="px-2 py-1 text-xs font-semibold uppercase text-gray-500">
            Projects
          </p>
          {projects?.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}/tree`}
              className={`block rounded px-2 py-1.5 text-sm ${
                p.id === projectId
                  ? "bg-gray-800 text-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
              }`}
            >
              {p.name}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}

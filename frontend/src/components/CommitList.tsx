import { useCommits } from "../api/hooks";
import Spinner from "./Spinner";

export default function CommitList({ taskId }: { taskId: string }) {
  const { data: commits, isLoading } = useCommits(taskId);

  if (isLoading) return <Spinner />;
  if (!commits?.length)
    return <p className="p-4 text-sm text-gray-500">No commits.</p>;

  return (
    <div className="space-y-2 p-4">
      {commits.map((c) => (
        <div
          key={c.id}
          className="flex items-start gap-3 text-sm"
        >
          <code className="shrink-0 rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-400">
            {c.commit_hash.slice(0, 7)}
          </code>
          <div className="min-w-0 flex-1">
            <p className="truncate text-gray-300">{c.message ?? "(no message)"}</p>
            <p className="text-xs text-gray-500">
              {c.author && <>{c.author} &middot; </>}
              {new Date(c.committed_at).toLocaleString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

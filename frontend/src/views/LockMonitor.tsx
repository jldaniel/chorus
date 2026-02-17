import { useParams } from "react-router-dom";
import { useInProgress, useForceReleaseLock } from "../api/hooks";
import Spinner from "../components/Spinner";
import ErrorMessage from "../components/ErrorMessage";

function timeRemaining(expiresAt: string): string {
  const diff = new Date(expiresAt).getTime() - Date.now();
  if (diff <= 0) return "Expired";
  const mins = Math.floor(diff / 60000);
  const secs = Math.floor((diff % 60000) / 1000);
  return `${mins}m ${secs}s`;
}

export default function LockMonitor() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: tasks, isLoading, error, refetch } = useInProgress(projectId!);
  const forceRelease = useForceReleaseLock(projectId!);

  if (isLoading) return <Spinner />;
  if (error)
    return <ErrorMessage message="Failed to load locks" onRetry={refetch} />;

  const locked = tasks?.filter((t) => t.lock_caller_label) ?? [];

  if (locked.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        <p>No active locks.</p>
        <p className="mt-1 text-xs">Auto-refreshes every 10 seconds.</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-xs uppercase text-gray-500">
            <th className="px-3 py-2">Task</th>
            <th className="px-3 py-2">Caller</th>
            <th className="px-3 py-2">Purpose</th>
            <th className="px-3 py-2">Time remaining</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {locked.map((t) => (
            <tr key={t.id} className="border-b border-gray-800/50">
              <td className="px-3 py-2 text-gray-200">{t.name}</td>
              <td className="px-3 py-2 text-gray-400">
                {t.lock_caller_label}
              </td>
              <td className="px-3 py-2 capitalize text-gray-400">
                {t.lock_purpose}
              </td>
              <td className="px-3 py-2 font-mono text-xs text-gray-400">
                {t.lock_expires_at ? timeRemaining(t.lock_expires_at) : "—"}
              </td>
              <td className="px-3 py-2">
                <button
                  onClick={() => {
                    if (confirm("Force-release this lock?"))
                      forceRelease.mutate(t.id);
                  }}
                  disabled={forceRelease.isPending}
                  className="rounded border border-red-800 px-2 py-1 text-xs text-red-400 hover:bg-red-900/30"
                >
                  Release
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-gray-600">
        Auto-refreshes every 10 seconds.
      </p>
    </div>
  );
}

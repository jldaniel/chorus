import { useWorkLog } from "../api/hooks";
import Spinner from "./Spinner";

const opIcons: Record<string, string> = {
  sizing: "\u{1F4CF}",
  breakdown: "\u{1F4CB}",
  refinement: "\u{1F50D}",
  implementation: "\u{1F528}",
  note: "\u{1F4DD}",
};

export default function WorkLogTimeline({ taskId }: { taskId: string }) {
  const { data: entries, isLoading } = useWorkLog(taskId);

  if (isLoading) return <Spinner />;
  if (!entries?.length)
    return <p className="p-4 text-sm text-gray-500">No work log entries.</p>;

  return (
    <div className="space-y-3 p-4">
      {entries.map((e) => (
        <div key={e.id} className="border-l-2 border-gray-700 pl-3">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>{opIcons[e.operation] ?? "\u2022"}</span>
            <span className="capitalize">{e.operation}</span>
            {e.author && <span>&middot; {e.author}</span>}
            <span>&middot; {new Date(e.created_at).toLocaleString()}</span>
          </div>
          <p className="mt-1 whitespace-pre-wrap text-sm text-gray-300">
            {e.content}
          </p>
        </div>
      ))}
    </div>
  );
}

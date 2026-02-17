import type { Readiness, Status, TaskType } from "../api/types";

const readinessColors: Record<Readiness, string> = {
  ready: "bg-green-900 text-green-300",
  needs_sizing: "bg-yellow-900 text-yellow-300",
  needs_breakdown: "bg-orange-900 text-orange-300",
  needs_refinement: "bg-purple-900 text-purple-300",
  blocked_by_children: "bg-red-900 text-red-300",
};

const readinessLabels: Record<Readiness, string> = {
  ready: "Ready",
  needs_sizing: "Needs sizing",
  needs_breakdown: "Needs breakdown",
  needs_refinement: "Needs refinement",
  blocked_by_children: "Blocked",
};

const statusColors: Record<Status, string> = {
  todo: "bg-gray-700 text-gray-300",
  doing: "bg-blue-900 text-blue-300",
  done: "bg-green-900 text-green-300",
  wont_do: "bg-gray-800 text-gray-500",
};

const statusLabels: Record<Status, string> = {
  todo: "To do",
  doing: "Doing",
  done: "Done",
  wont_do: "Won't do",
};

const typeColors: Record<TaskType, string> = {
  feature: "bg-indigo-900 text-indigo-300",
  bug: "bg-red-900 text-red-300",
  tech_debt: "bg-amber-900 text-amber-300",
};

const typeLabels: Record<TaskType, string> = {
  feature: "Feature",
  bug: "Bug",
  tech_debt: "Tech debt",
};

function BaseBadge({
  className,
  children,
}: {
  className: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${className}`}
    >
      {children}
    </span>
  );
}

export function ReadinessBadge({ readiness }: { readiness: Readiness }) {
  return (
    <BaseBadge className={readinessColors[readiness]}>
      {readinessLabels[readiness]}
    </BaseBadge>
  );
}

export function StatusBadge({ status }: { status: Status }) {
  return (
    <BaseBadge className={statusColors[status]}>
      {statusLabels[status]}
    </BaseBadge>
  );
}

export function TaskTypeBadge({ taskType }: { taskType: TaskType }) {
  return (
    <BaseBadge className={typeColors[taskType]}>
      {typeLabels[taskType]}
    </BaseBadge>
  );
}

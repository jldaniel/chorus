// Enums

export type TaskType = "feature" | "bug" | "tech_debt";
export type Status = "todo" | "doing" | "done" | "wont_do";
export type Readiness =
  | "needs_refinement"
  | "needs_sizing"
  | "needs_breakdown"
  | "blocked_by_children"
  | "ready";
export type Operation =
  | "sizing"
  | "breakdown"
  | "refinement"
  | "implementation"
  | "note";
export type LockPurpose =
  | "sizing"
  | "breakdown"
  | "refinement"
  | "implementation";

// Projects

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  task_count: number;
  points_total: number;
  points_completed: number;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  description?: string | null;
}

// Tasks

export interface TaskRead {
  id: string;
  project_id: string;
  parent_task_id: string | null;
  name: string;
  description: string | null;
  context: string | null;
  task_type: TaskType;
  status: Status;
  points: number | null;
  position: number;
  created_at: string;
  updated_at: string;
  effective_points: number | null;
  rolled_up_points: number | null;
  unsized_children: number;
  readiness: Readiness;
  children_count: number;
  is_locked: boolean;
}

export interface TaskTreeNode extends TaskRead {
  children: TaskTreeNode[];
}

export interface TaskWithLockInfo extends TaskRead {
  lock_caller_label: string | null;
  lock_purpose: string | null;
  lock_expires_at: string | null;
}

export interface TaskCreate {
  name: string;
  description?: string | null;
  context?: string | null;
  task_type: TaskType;
  position?: number | null;
}

export interface TaskUpdate {
  name?: string;
  description?: string | null;
  context?: string | null;
  task_type?: TaskType;
}

export interface StatusUpdate {
  status: Status;
}

export interface ReorderRequest {
  position: number;
}

// Locks

export interface LockRead {
  id: string;
  task_id: string;
  caller_label: string;
  lock_purpose: LockPurpose;
  acquired_at: string;
  last_heartbeat_at: string | null;
  expires_at: string;
}

// Work Log

export interface WorkLogEntry {
  id: string;
  task_id: string;
  author: string | null;
  operation: string;
  content: string;
  created_at: string;
}

export interface WorkLogCreate {
  author?: string | null;
  operation: Operation;
  content: string;
}

// Commits

export interface Commit {
  id: string;
  task_id: string;
  author: string | null;
  commit_hash: string;
  message: string | null;
  committed_at: string;
}

// Task Context

export interface TaskAncestryItem {
  id: string;
  name: string;
  description: string | null;
  context: string | null;
  updated_at: string;
}

export interface TaskContextResponse {
  task: TaskRead;
  ancestors: TaskAncestryItem[];
  work_log: WorkLogEntry[];
  commits: Commit[] | null;
  context_captured_at: string | null;
  context_freshness: "fresh" | "stale";
  stale_reasons: string[];
}

// Flag refinement

export interface FlagRefinementRequest {
  refinement_notes: string;
}

// API Error

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string;
}

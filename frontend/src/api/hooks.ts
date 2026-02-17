import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { get, post, put, patch, del } from "./client";
import type {
  ProjectDetail,
  ProjectCreate,
  ProjectUpdate,
  TaskRead,
  TaskTreeNode,
  TaskCreate,
  TaskUpdate,
  StatusUpdate,
  ReorderRequest,
  WorkLogEntry,
  Commit,
  TaskWithLockInfo,
  FlagRefinementRequest,
} from "./types";

// --- Query Keys ---

const keys = {
  projects: ["projects"] as const,
  project: (id: string) => ["projects", id] as const,
  projectTasks: (id: string) => ["projects", id, "tasks"] as const,
  task: (id: string) => ["tasks", id] as const,
  taskTree: (id: string) => ["tasks", id, "tree"] as const,
  workLog: (id: string) => ["tasks", id, "work-log"] as const,
  commits: (id: string) => ["tasks", id, "commits"] as const,
  backlog: (id: string) => ["projects", id, "backlog"] as const,
  inProgress: (id: string) => ["projects", id, "in-progress"] as const,
  needsRefinement: (id: string) =>
    ["projects", id, "needs-refinement"] as const,
};

// --- Projects ---

export function useProjects() {
  return useQuery({
    queryKey: keys.projects,
    queryFn: () => get<ProjectDetail[]>("/projects"),
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: keys.project(id),
    queryFn: () => get<ProjectDetail>(`/projects/${id}`),
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectCreate) =>
      post<ProjectDetail>("/projects", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.projects }),
  });
}

export function useUpdateProject(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectUpdate) =>
      put<ProjectDetail>(`/projects/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.projects });
      qc.invalidateQueries({ queryKey: keys.project(id) });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => del(`/projects/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.projects }),
  });
}

// --- Tasks ---

export function useProjectTasks(projectId: string) {
  return useQuery({
    queryKey: keys.projectTasks(projectId),
    queryFn: () => get<TaskRead[]>(`/projects/${projectId}/tasks`),
  });
}

export function useTask(id: string) {
  return useQuery({
    queryKey: keys.task(id),
    queryFn: () => get<TaskRead>(`/tasks/${id}`),
    enabled: !!id,
  });
}

export function useTaskTree(id: string, enabled = true) {
  return useQuery({
    queryKey: keys.taskTree(id),
    queryFn: () => get<TaskTreeNode>(`/tasks/${id}/tree`),
    enabled,
  });
}

export function useCreateTask(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) =>
      post<TaskRead>(`/projects/${projectId}/tasks`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.projectTasks(projectId) });
      qc.invalidateQueries({ queryKey: keys.project(projectId) });
    },
  });
}

export function useCreateSubtask(parentId: string, projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) =>
      post<TaskRead>(`/tasks/${parentId}/subtasks`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.projectTasks(projectId) });
      qc.invalidateQueries({ queryKey: keys.taskTree(parentId) });
      qc.invalidateQueries({ queryKey: keys.task(parentId) });
      qc.invalidateQueries({ queryKey: keys.project(projectId) });
    },
  });
}

export function useUpdateTask(id: string, projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskUpdate) => put<TaskRead>(`/tasks/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.task(id) });
      qc.invalidateQueries({ queryKey: keys.projectTasks(projectId) });
    },
  });
}

export function useDeleteTask(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => del(`/tasks/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.projectTasks(projectId) });
      qc.invalidateQueries({ queryKey: keys.project(projectId) });
    },
  });
}

export function useUpdateStatus(id: string, projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: StatusUpdate) =>
      patch<TaskRead>(`/tasks/${id}/status`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.task(id) });
      qc.invalidateQueries({ queryKey: keys.projectTasks(projectId) });
      qc.invalidateQueries({ queryKey: keys.project(projectId) });
      qc.invalidateQueries({ queryKey: keys.inProgress(projectId) });
      qc.invalidateQueries({ queryKey: keys.backlog(projectId) });
    },
  });
}

export function useReorderTask(id: string, projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ReorderRequest) =>
      patch<TaskRead>(`/tasks/${id}/reorder`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: keys.projectTasks(projectId) }),
  });
}

// --- Work Log ---

export function useWorkLog(taskId: string) {
  return useQuery({
    queryKey: keys.workLog(taskId),
    queryFn: () => get<WorkLogEntry[]>(`/tasks/${taskId}/work-log`),
    enabled: !!taskId,
  });
}

// --- Commits ---

export function useCommits(taskId: string) {
  return useQuery({
    queryKey: keys.commits(taskId),
    queryFn: () => get<Commit[]>(`/tasks/${taskId}/commits`),
    enabled: !!taskId,
  });
}

// --- Discovery ---

export function useBacklog(projectId: string) {
  return useQuery({
    queryKey: keys.backlog(projectId),
    queryFn: () => get<TaskRead[]>(`/projects/${projectId}/backlog`),
  });
}

export function useInProgress(projectId: string) {
  return useQuery({
    queryKey: keys.inProgress(projectId),
    queryFn: () =>
      get<TaskWithLockInfo[]>(`/projects/${projectId}/in-progress`),
    refetchInterval: 10_000,
  });
}

export function useNeedsRefinement(projectId: string) {
  return useQuery({
    queryKey: keys.needsRefinement(projectId),
    queryFn: () => get<TaskRead[]>(`/projects/${projectId}/needs-refinement`),
  });
}

// --- Locks ---

export function useForceReleaseLock(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) =>
      del(`/tasks/${taskId}/lock?force=true&caller_label=dashboard`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: keys.inProgress(projectId) }),
  });
}

// --- Atomic Ops ---

export function useFlagRefinement(id: string, projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: FlagRefinementRequest) =>
      post<TaskRead>(`/tasks/${id}/flag-refinement`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.task(id) });
      qc.invalidateQueries({ queryKey: keys.projectTasks(projectId) });
    },
  });
}

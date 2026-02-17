import type { ApiError } from "./types";

const BASE_URL = "/api";

export class ApiRequestError extends Error {
  constructor(
    public status: number,
    public error: ApiError,
  ) {
    super(error.message);
    this.name = "ApiRequestError";
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let error: ApiError;
    try {
      const json = await res.json();
      error = json.error ?? {
        code: "unknown",
        message: res.statusText,
        details: {},
        request_id: "",
      };
    } catch {
      error = {
        code: "unknown",
        message: res.statusText,
        details: {},
        request_id: "",
      };
    }
    throw new ApiRequestError(res.status, error);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export function get<T>(path: string): Promise<T> {
  return request<T>("GET", path);
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

export function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>("PUT", path, body);
}

export function patch<T>(path: string, body: unknown): Promise<T> {
  return request<T>("PATCH", path, body);
}

export function del(path: string): Promise<void> {
  return request<void>("DELETE", path);
}

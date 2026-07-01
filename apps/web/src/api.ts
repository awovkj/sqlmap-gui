import type { ReportRead, ScanConfig, TaskEvent, TaskRead } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765/api";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response.json() as Promise<T>;
}

export async function health(): Promise<{ status: string; service: string }> {
  return requestJson("/health");
}

export async function createTask(config: ScanConfig): Promise<TaskRead> {
  return requestJson("/tasks", {
    method: "POST",
    body: JSON.stringify(config),
  });
}

export async function listTasks(): Promise<TaskRead[]> {
  return requestJson("/tasks");
}

export async function getTaskLogs(taskId: string): Promise<TaskEvent[]> {
  return requestJson(`/tasks/${taskId}/logs`);
}

export async function getTaskReport(taskId: string): Promise<ReportRead | null> {
  try {
    return await requestJson(`/tasks/${taskId}/report`);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("404")) {
      return null;
    }
    throw error;
  }
}

export function subscribeEvents(onEvent: (event: TaskEvent) => void, onError: () => void): EventSource {
  const source = new EventSource(`${API_BASE}/events`);
  source.onmessage = (message) => {
    onEvent(JSON.parse(message.data) as TaskEvent);
  };
  source.onerror = () => {
    onError();
  };
  return source;
}

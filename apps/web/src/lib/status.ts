/* Task status → Chinese label + CSS class used by the task queue. */

const STATUS_LABELS: Record<string, string> = {
  created: "已创建",
  queued: "排队中",
  running: "运行中",
  parsing: "解析中",
  completed: "已完成",
  failed: "失败",
  cancelling: "取消中",
  cancelled: "已取消",
  interrupted: "已中断",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function statusClass(status: string): string {
  if (status === "running") return "status-running";
  if (status === "completed") return "status-done";
  if (status === "failed") return "status-fail";
  if (status === "cancelled" || status === "interrupted") return "status-warn";
  return "";
}

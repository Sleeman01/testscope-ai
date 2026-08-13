export type StatusBadgeVariant = "success" | "danger" | "warning" | "progress" | "neutral";

export function classifyStatus(raw: string): StatusBadgeVariant {
  const s = raw.toLowerCase();
  if (s.includes("not covered") || s.includes("fail") || s.includes("missing")) return "danger";
  if (s.includes("partial")) return "warning";
  if (s.includes("covered") || s.includes("pass") || s.includes("completed")) return "success";
  if (s.includes("pending") || s.includes("running") || s.includes("progress")) return "progress";
  return "neutral";
}

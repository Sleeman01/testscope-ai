import { CheckCircle2, XCircle, AlertTriangle, Clock, Circle, type LucideIcon } from "lucide-react";
import { cn } from "../lib/cn";

export type Variant = "success" | "danger" | "warning" | "progress" | "neutral";

export function classify(raw: string): Variant {
  const s = raw.toLowerCase();
  if (s.includes("not covered") || s.includes("fail") || s.includes("missing")) return "danger";
  if (s.includes("partial")) return "warning";
  if (s.includes("covered") || s.includes("pass") || s.includes("completed")) return "success";
  if (s.includes("pending") || s.includes("running") || s.includes("progress")) return "progress";
  return "neutral";
}

const ICONS: Record<Variant, LucideIcon> = {
  success: CheckCircle2,
  danger: XCircle,
  warning: AlertTriangle,
  progress: Clock,
  neutral: Circle,
};

const VARIANT_CLASSES: Record<Variant, string> = {
  success: "bg-success/15 text-success",
  danger: "bg-danger/15 text-danger",
  warning: "bg-warning/15 text-warning",
  progress: "bg-progress/15 text-progress",
  neutral: "bg-neutral/15 text-neutral",
};

export function StatusBadge({ status }: { status: string }) {
  const variant = classify(status);
  const Icon = ICONS[variant];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold",
        VARIANT_CLASSES[variant]
      )}
    >
      <Icon aria-hidden="true" className="h-3.5 w-3.5 flex-shrink-0" />
      <span>{status}</span>
    </span>
  );
}

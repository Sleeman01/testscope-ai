import { forwardRef, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/cn";

export type StatTileTone = "success" | "warning" | "danger" | "neutral";

export interface StatTileProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tone?: StatTileTone;
}

const TONE_BG: Record<StatTileTone, string> = {
  success: "bg-success/10",
  warning: "bg-warning/10",
  danger: "bg-danger/10",
  neutral: "bg-neutral/10",
};

const TONE_TEXT: Record<StatTileTone, string> = {
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  neutral: "text-neutral",
};

export const StatTile = forwardRef<HTMLDivElement, StatTileProps>(function StatTile(
  { label, value, icon, tone = "neutral", className, ...props },
  ref
) {
  return (
    <div ref={ref} className={cn("rounded-xl p-5", TONE_BG[tone], className)} {...props}>
      <div className={cn("flex items-center gap-2", TONE_TEXT[tone])}>
        {icon}
        <span className="text-xs font-semibold uppercase tracking-wide">{label}</span>
      </div>
      <div className="mt-2 text-3xl font-bold text-text">{value}</div>
    </div>
  );
});

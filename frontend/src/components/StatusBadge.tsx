type Variant = "success" | "danger" | "warning" | "progress" | "neutral";

function classify(raw: string): Variant {
  const s = raw.toLowerCase();
  if (s.includes("not covered") || s.includes("fail") || s.includes("missing")) return "danger";
  if (s.includes("partial")) return "warning";
  if (s.includes("covered") || s.includes("pass") || s.includes("completed")) return "success";
  if (s.includes("pending") || s.includes("running") || s.includes("progress")) return "progress";
  return "neutral";
}

const ICONS: Record<Variant, JSX.Element> = {
  success: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 8.5 6.5 12 13 4" />
    </svg>
  ),
  danger: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  ),
  warning: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 2 14.5 13.5H1.5L8 2Z" />
      <path d="M8 6.5v3M8 11.5h.01" />
    </svg>
  ),
  progress: (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6" />
      <path d="M8 4.5V8l2.5 1.5" />
    </svg>
  ),
  neutral: (
    <svg viewBox="0 0 16 16" fill="currentColor">
      <circle cx="8" cy="8" r="2.5" />
    </svg>
  ),
};

export function StatusBadge({ status }: { status: string }) {
  const variant = classify(status);
  return (
    <span className={`badge badge-${variant}`}>
      <span aria-hidden="true">{ICONS[variant]}</span>
      <span>{status}</span>
    </span>
  );
}

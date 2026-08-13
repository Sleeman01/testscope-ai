import { forwardRef, type HTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/cn";

export interface SpinnerProps extends HTMLAttributes<HTMLDivElement> {
  message?: string;
  size?: "sm" | "md" | "lg";
}

const SIZE_CLASSES = {
  sm: "h-5 w-5",
  md: "h-8 w-8",
  lg: "h-10 w-10",
} as const;

export const Spinner = forwardRef<HTMLDivElement, SpinnerProps>(function Spinner(
  { message, size = "md", className, ...props },
  ref
) {
  const label = message ?? "Loading";

  return (
    <div
      ref={ref}
      role="status"
      aria-live="polite"
      aria-label={label}
      className={cn(
        "flex flex-col items-center justify-center gap-4 text-center text-text-secondary",
        className
      )}
      {...props}
    >
      <Loader2 className={cn("animate-spin text-accent", SIZE_CLASSES[size])} aria-hidden="true" />
      {message ? <p>{message}</p> : <span className="sr-only">{label}</span>}
    </div>
  );
});

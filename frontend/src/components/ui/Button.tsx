import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: cn(
    "bg-accent text-white shadow-button",
    "hover:bg-accent/90 hover:shadow-button-hover hover:-translate-y-px",
    "active:translate-y-0 active:scale-[0.98]",
    "disabled:hover:translate-y-0 disabled:hover:shadow-button"
  ),
  secondary: cn(
    "border border-border bg-surface text-text shadow-sm",
    "hover:border-border hover:bg-surface-elevated hover:-translate-y-px",
    "active:translate-y-0 active:scale-[0.98]",
    "disabled:hover:translate-y-0"
  ),
  ghost: cn(
    "bg-transparent text-text-secondary",
    "hover:bg-surface-muted hover:text-text",
    "active:scale-[0.98]"
  ),
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", className, type = "button", disabled, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 py-2.5",
        "text-sm font-semibold transition-[color,background-color,border-color,box-shadow,transform]",
        "duration-[var(--duration-fast)] ease-[var(--ease-default)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
        "disabled:cursor-not-allowed disabled:opacity-60",
        VARIANT_CLASSES[variant],
        className
      )}
      {...props}
    />
  );
});

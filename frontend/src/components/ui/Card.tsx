import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export type CardVariant = "default" | "bordered" | "elevated";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
}

const VARIANT_CLASSES: Record<CardVariant, string> = {
  default: "bg-surface",
  bordered: "border border-border bg-surface",
  elevated: "border border-border bg-surface-elevated shadow-card",
};

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { variant = "bordered", className, ...props },
  ref
) {
  return (
    <div
      ref={ref}
      className={cn("rounded-2xl p-6", VARIANT_CLASSES[variant], className)}
      {...props}
    />
  );
});

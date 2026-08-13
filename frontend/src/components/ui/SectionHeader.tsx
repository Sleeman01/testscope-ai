import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export interface SectionHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  as?: "h2" | "h3";
}

export const SectionHeader = forwardRef<HTMLDivElement, SectionHeaderProps>(function SectionHeader(
  { title, subtitle, as: Heading = "h2", className, ...props },
  ref
) {
  return (
    <div ref={ref} className={cn("mb-4 flex flex-col gap-1", className)} {...props}>
      <Heading className="text-heading font-semibold tracking-tight text-text">{title}</Heading>
      {subtitle && <p className="text-sm text-text-secondary">{subtitle}</p>}
    </div>
  );
});

import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export type PageMaxWidth = "2xl" | "4xl" | "5xl";

export interface PageContainerProps extends HTMLAttributes<HTMLDivElement> {
  maxWidth?: PageMaxWidth;
}

const MAX_WIDTH_CLASSES: Record<PageMaxWidth, string> = {
  "2xl": "max-w-2xl",
  "4xl": "max-w-4xl",
  "5xl": "max-w-5xl",
};

export const PageContainer = forwardRef<HTMLDivElement, PageContainerProps>(function PageContainer(
  { maxWidth = "2xl", className, ...props },
  ref
) {
  return (
    <div
      ref={ref}
      className={cn(
        "mx-auto flex w-full flex-col gap-6 px-5 py-6 pb-12 sm:px-6 sm:py-8",
        MAX_WIDTH_CLASSES[maxWidth],
        className
      )}
      {...props}
    />
  );
});

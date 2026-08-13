import { AnimatePresence, motion } from "framer-motion";
import { Radar } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { cn } from "../lib/cn";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return cn(
    "rounded-lg px-4 py-2.5 text-sm font-semibold no-underline transition-all duration-[var(--duration-fast)]",
    "hover:no-underline",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
    isActive
      ? "bg-accent text-white shadow-button hover:bg-accent-strong"
      : "border border-border bg-surface-elevated text-text-secondary hover:border-accent/40 hover:bg-accent-muted/40 hover:text-text"
  );
}

export function Layout() {
  const location = useLocation();
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-accent focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
      >
        Skip to main content
      </a>
      <header className="sticky top-0 z-10 border-b border-border/80 bg-surface/90 px-5 py-3 shadow-header backdrop-blur-md sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
          <NavLink
            to="/"
            end
            className="flex items-center gap-2.5 text-text no-underline transition-opacity duration-[var(--duration-fast)] hover:opacity-90 hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-accent text-white shadow-button">
              <Radar className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="text-base font-bold tracking-tight">TestScope</span>
          </NavLink>
          <nav className="flex gap-2 rounded-xl border border-border/60 bg-surface-muted/80 p-1.5" aria-label="Main navigation">
            <NavLink to="/" end className={navLinkClass}>
              New analysis
            </NavLink>
            <NavLink to="/history" className={navLinkClass}>
              History
            </NavLink>
          </nav>
        </div>
      </header>
      <main id="main-content">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </>
  );
}

import { AnimatePresence, motion } from "framer-motion";
import { Radar } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { cn } from "../lib/cn";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return cn(
    "relative px-1 py-2 text-sm font-medium no-underline transition-colors duration-[var(--duration-fast)]",
    "hover:text-text hover:no-underline",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
    isActive ? "text-text" : "text-text-secondary",
    isActive &&
      "after:absolute after:inset-x-0 after:-bottom-[17px] after:h-0.5 after:rounded-full after:bg-accent"
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
      <header className="sticky top-0 z-10 border-b border-border bg-surface/80 px-5 py-4 shadow-header backdrop-blur-md sm:px-6">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4">
          <NavLink
            to="/"
            end
            className="flex items-center gap-2.5 text-text no-underline transition-opacity duration-[var(--duration-fast)] hover:opacity-90 hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-accent text-white shadow-button">
              <Radar className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="text-base font-bold tracking-tight">TestScope</span>
          </NavLink>
          <nav className="flex gap-6" aria-label="Main navigation">
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

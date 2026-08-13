import { AnimatePresence, motion } from "framer-motion";
import { Radar } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { cn } from "../lib/cn";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return cn(
    "text-sm no-underline transition-colors hover:text-text hover:no-underline",
    isActive ? "font-bold text-text" : "font-medium text-text-secondary"
  );
}

export function Layout() {
  const location = useLocation();
  return (
    <>
      <header className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-4 border-b border-border bg-surface px-5 py-4">
        <NavLink to="/" end className="flex items-center gap-2.5 text-text no-underline hover:no-underline">
          <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-[7px] bg-accent text-white">
            <Radar className="h-4 w-4" aria-hidden="true" />
          </span>
          <span className="text-base font-bold tracking-tight">TestScope</span>
        </NavLink>
        <nav className="flex gap-6">
          <NavLink to="/" end className={navLinkClass}>
            New analysis
          </NavLink>
          <NavLink to="/history" className={navLinkClass}>
            History
          </NavLink>
        </nav>
      </header>
      <main>
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

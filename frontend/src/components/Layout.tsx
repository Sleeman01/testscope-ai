import { AnimatePresence, motion } from "framer-motion";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { cn } from "../lib/cn";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return cn(
    "border-b-2 border-transparent px-0 py-2 text-sm font-semibold text-text-secondary no-underline transition-colors hover:text-text hover:no-underline",
    isActive && "border-accent text-text"
  );
}

export function Layout() {
  const location = useLocation();
  return (
    <>
      <header className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-4 border-b border-border bg-surface/60 px-5 py-4 backdrop-blur-md">
        <NavLink to="/" end className="text-base font-bold tracking-tight text-text no-underline">
          TestScope AI
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

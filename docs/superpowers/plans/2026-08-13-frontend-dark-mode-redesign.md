# Frontend Dark-Mode Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the existing 3-page TestScope AI frontend (Home, Results, History) into a dark-only, high-contrast Linear/Vercel/Stripe-inspired dashboard aesthetic, per `docs/2026-08-13-frontend-dark-mode-redesign-design.md`.

**Architecture:** Add Tailwind v4 (via `@tailwindcss/vite`, no separate config file — CSS-first `@theme`), `lucide-react`, `framer-motion`, `clsx`, `tailwind-merge` to the existing React 18 + Vite + TS app. Migrate the current hand-rolled CSS custom-property system (`tokens.css` + `base.css`) into a Tailwind `@theme` block plus inline utility classes in JSX, one page/component at a time, so the app never sits in a fully-broken visual state between commits. No new routes, files beyond one `cn()` helper, or dependencies.

**Tech Stack:** React 18, Vite, TypeScript, React Router 6, Tailwind CSS v4, `@tailwindcss/vite`, `lucide-react`, `framer-motion`, `clsx`, `tailwind-merge`, Vitest + Testing Library (existing).

## Global Constraints

- Working directory for all steps: `frontend/`.
- Exactly these 5 new dependencies, no others: `tailwindcss`, `@tailwindcss/vite`, `lucide-react`, `framer-motion`, `clsx`, `tailwind-merge`. Versions: `tailwindcss@^4.3.3`, `@tailwindcss/vite@^4.3.3`, `lucide-react@^1.31.0`, `framer-motion@^13.1.0`, `clsx@^2.1.1`, `tailwind-merge@^3.6.0` (latest published as of this plan).
- Dark-only. No theme toggle, no `data-theme`/`prefers-color-scheme` branching.
- No new routes/pages. Only `Home`, `Results`, `History`, `Layout`, `StatusBadge` are touched, plus one new file: `src/lib/cn.ts`.
- All 9 existing tests (`Home.test.tsx` ×1, `Results.test.tsx` ×2, `History.test.tsx` ×1, `App.test.tsx` ×3, `client.test.ts` ×2) must stay green throughout — they query by role/label/text only, never by class name, so this is a real constraint the restyle must respect (keep `id`/`htmlFor` pairs, button/link accessible names, and rendered text exactly as today).
- `npm run build` (`tsc -b && vite build`) must stay green after every task.
- This plan is a visual migration of already-tested behavior, not new business logic — so tasks follow "change → run the existing test file → run full suite/build → commit" rather than TDD's "write a new failing test first." No new test files are added except if Task 6 turns out to require one (see Task 6's note).
- Tailwind v4 naming convention used throughout: an `@theme` key `--color-<name>` auto-generates `bg-<name>`/`text-<name>`/`border-<name>`/`ring-<name>` utilities; `--radius-<name>` generates `rounded-<name>`; `--spacing-<name>` generates `p-<name>`/`gap-<name>`/etc (and overrides that one numeric slot in Tailwind's default spacing scale if `<name>` is a number). This plan relies on that mechanism — do not rename the custom properties.

---

### Task 1: Install Tailwind v4 and wire the dark token theme

**Files:**
- Modify: `frontend/package.json` (via `npm install`, not hand-edited)
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/vitest.config.ts`
- Modify: `frontend/src/styles/tokens.css`

**Interfaces:**
- Produces: Tailwind utility classes for `bg-bg`, `bg-surface`, `border-border`, `text-text`, `text-text-secondary`, `text-text-muted`, `bg-accent`/`text-accent`/`border-accent`/`ring-accent`, `bg-success`/`text-success`, `bg-warning`/`text-warning`, `bg-danger`/`text-danger`, `bg-progress`/`text-progress`, `bg-neutral`/`text-neutral`, `rounded-sm`/`rounded-md`/`rounded-lg` (overridden to 6/10/16px), `p-5`/`gap-5` etc (5/6/8 overridden to 24/32/48px, 1-4 use Tailwind's matching defaults), `font-sans`/`font-mono` (overridden to the project's stacks). These are consumed by every later task.
- Consumes: nothing new (first task).

- [ ] **Step 1: Install the 5 approved dependencies**

Run from `frontend/`:
```bash
npm install tailwindcss@^4.3.3 @tailwindcss/vite@^4.3.3 lucide-react@^1.31.0 framer-motion@^13.1.0 clsx@^2.1.1 tailwind-merge@^3.6.0
```

- [ ] **Step 2: Wire the Tailwind Vite plugin into both Vite configs**

`frontend/vite.config.ts` (full file):
```ts
/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
```

`frontend/vitest.config.ts` (full file):
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/setupTests.ts"] },
});
```

- [ ] **Step 3: Rewrite `tokens.css` as a Tailwind `@theme` block with the dark palette**

`frontend/src/styles/tokens.css` (full file — replaces the old `:root` token block; the trailing legacy `:root` block keeps `Layout.css` working until Task 3 deletes both together):
```css
@import "tailwindcss";

@theme {
  /* Colors */
  --color-bg: #0b0f17;
  --color-surface: #0f172a;
  --color-border: #1e293b;
  --color-text: #f8fafc;
  --color-text-secondary: #94a3b8;
  --color-text-muted: #64748b;
  --color-accent: #6366f1;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-progress: #3b82f6;
  --color-neutral: #64748b;

  /* Radius — overrides Tailwind's default rounded-sm/md/lg to this project's values */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  /* Spacing — overrides only the 3 slots that diverge from Tailwind's default
     4px-multiple scale (1-4 already match: 4/8/12/16px) */
  --spacing-5: 24px;
  --spacing-6: 32px;
  --spacing-8: 48px;

  /* Fonts */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}

/* Legacy chrome tokens — still consumed by Layout.css until Task 3 removes both together.
   Values unchanged from before this redesign (the header was already dark). */
:root {
  --color-chrome-bg: #14141f;
  --color-chrome-text: #eeedf8;
  --color-chrome-text-muted: #9a97b8;
  --color-chrome-border: #24243a;
}
```

- [ ] **Step 4: Verify the build and dev server still work**

Run: `npm run build`
Expected: succeeds, no errors (the app will render with dark CSS-variable values through the old, still-present `base.css` component classes — visually rough, but functional; later tasks replace `base.css` page by page).

Run: `npm run dev` in the background, then `curl -sf http://localhost:5173/ | head -5`, then stop the dev server.
Expected: HTML response containing `<div id="root">`, no connection error.

- [ ] **Step 5: Run the full test suite**

Run: `npm test`
Expected: 9/9 passing, unchanged (no JSX changed yet).

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/vitest.config.ts frontend/src/styles/tokens.css
git commit -m "feat(frontend): add Tailwind v4 and dark theme tokens"
```

---

### Task 2: `cn()` helper and dark `StatusBadge`

**Files:**
- Create: `frontend/src/lib/cn.ts`
- Modify: `frontend/src/components/StatusBadge.tsx`

**Interfaces:**
- Produces: `cn(...inputs: ClassValue[]): string` from `src/lib/cn.ts`, used by every later task that needs conditional classes.
- Consumes: `@theme` tokens from Task 1 (`bg-success`, `text-success`, etc. and their `/15` opacity variants).

- [ ] **Step 1: Add the `cn()` helper**

`frontend/src/lib/cn.ts` (full file):
```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Restyle `StatusBadge` with Tailwind + `lucide-react` icons**

`frontend/src/components/StatusBadge.tsx` (full file):
```tsx
import { CheckCircle2, XCircle, AlertTriangle, Clock, Circle, type LucideIcon } from "lucide-react";
import { cn } from "../lib/cn";

type Variant = "success" | "danger" | "warning" | "progress" | "neutral";

function classify(raw: string): Variant {
  const s = raw.toLowerCase();
  if (s.includes("not covered") || s.includes("fail") || s.includes("missing")) return "danger";
  if (s.includes("partial")) return "warning";
  if (s.includes("covered") || s.includes("pass") || s.includes("completed")) return "success";
  if (s.includes("pending") || s.includes("running") || s.includes("progress")) return "progress";
  return "neutral";
}

const ICONS: Record<Variant, LucideIcon> = {
  success: CheckCircle2,
  danger: XCircle,
  warning: AlertTriangle,
  progress: Clock,
  neutral: Circle,
};

const VARIANT_CLASSES: Record<Variant, string> = {
  success: "bg-success/15 text-success",
  danger: "bg-danger/15 text-danger",
  warning: "bg-warning/15 text-warning",
  progress: "bg-progress/15 text-progress",
  neutral: "bg-neutral/15 text-neutral",
};

export function StatusBadge({ status }: { status: string }) {
  const variant = classify(status);
  const Icon = ICONS[variant];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold",
        VARIANT_CLASSES[variant]
      )}
    >
      <Icon aria-hidden="true" className="h-3.5 w-3.5 flex-shrink-0" />
      <span>{status}</span>
    </span>
  );
}
```

- [ ] **Step 3: Run the tests that exercise `StatusBadge` (via `Results`/`History`)**

Run: `npm test -- Results History`
Expected: all pass — `Results.test.tsx`'s `getByText(/not covered/i)` and `History.test.tsx` still match the badge's rendered `{status}` text node.

- [ ] **Step 4: Run the full suite and build**

Run: `npm test && npm run build`
Expected: 9/9 passing, build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/cn.ts frontend/src/components/StatusBadge.tsx
git commit -m "feat(frontend): dark StatusBadge with lucide icons and cn() helper"
```

---

### Task 3: Dark `Layout` header/nav + page-transition motion

**Files:**
- Modify: `frontend/src/components/Layout.tsx`
- Delete: `frontend/src/components/Layout.css`
- Modify: `frontend/src/styles/tokens.css` (remove the now-unused legacy chrome `:root` block from Task 1)

**Interfaces:**
- Produces: no new exports; `Layout` still renders `<Outlet />` for the router.
- Consumes: `cn()` from Task 2, `@theme` tokens from Task 1.

- [ ] **Step 1: Restyle `Layout` and add the route-transition wrapper**

`frontend/src/components/Layout.tsx` (full file):
```tsx
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
```

- [ ] **Step 2: Delete `Layout.css` and the now-unused legacy chrome tokens**

```bash
rm frontend/src/components/Layout.css
```

Remove the trailing legacy block from `frontend/src/styles/tokens.css` (everything from `/* Legacy chrome tokens ... */` through the closing `}` of that second `:root { ... }` block, added in Task 1 Step 3) — the file should end after the `@theme { ... }` block's closing brace.

- [ ] **Step 3: Run the routing tests**

Run: `npm test -- App`
Expected: all 3 `App.test.tsx` tests pass — `getByRole("heading", { name: /testscope ai/i })` still matches `Home`'s `<h1>` (the header brand is a link, not a heading, so it doesn't collide), `Results`/`History` route tests unaffected by header/motion changes.

- [ ] **Step 4: Run the full suite and build**

Run: `npm test && npm run build`
Expected: 9/9 passing, build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Layout.tsx frontend/src/styles/tokens.css
git rm frontend/src/components/Layout.css
git commit -m "feat(frontend): dark glass header and route-transition motion"
```

---

### Task 4: Restyle `Home` (form, primary button, spinner)

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

**Interfaces:**
- Consumes: `@theme` tokens (Task 1). No new exports.

- [ ] **Step 1: Restyle `Home`**

`frontend/src/pages/Home.tsx` (full file):
```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { createAnalysis } from "../api/client";

export function Home() {
  const [repository, setRepository] = useState("");
  const [issueNumber, setIssueNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const result = await createAnalysis(repository, Number(issueNumber), notes);
      navigate(`/analyses/${result.analysis_id}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-5 py-6 pb-12">
      <div className="rounded-2xl border border-border bg-surface/60 p-5 shadow-sm backdrop-blur-md">
        <h1 className="text-2xl font-bold tracking-tight text-text">TestScope AI</h1>
        <p className="mt-1 text-text-secondary">
          Point this at a GitHub issue and get back a test coverage matrix, missing scenarios, and a
          ready-to-file follow-up issue.
        </p>
        <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="repository" className="text-sm font-semibold text-text-secondary">
              Repository (owner/repo)
            </label>
            <input
              id="repository"
              placeholder="acme/widgets"
              value={repository}
              onChange={(e) => setRepository(e.target.value)}
              required
              className="rounded-md border border-border bg-bg px-3 py-3 text-text placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="issue-number" className="text-sm font-semibold text-text-secondary">
              Issue number
            </label>
            <input
              id="issue-number"
              type="number"
              placeholder="42"
              value={issueNumber}
              onChange={(e) => setIssueNumber(e.target.value)}
              required
              className="rounded-md border border-border bg-bg px-3 py-3 text-text placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="notes" className="text-sm font-semibold text-text-secondary">
              Notes (optional)
            </label>
            <textarea
              id="notes"
              rows={4}
              placeholder="Anything extra the analysis should take into account..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="min-h-22 resize-y rounded-md border border-border bg-bg px-3 py-3 text-text placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </div>

          <motion.button
            type="submit"
            disabled={submitting}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-gradient-to-r from-indigo-500 to-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-shadow hover:shadow-lg hover:shadow-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Analyzing...
              </>
            ) : (
              "Analyze test coverage"
            )}
          </motion.button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run `Home`'s tests**

Run: `npm test -- Home`
Expected: pass — `getByLabelText(/repository/i)`, `getByLabelText(/issue number/i)`, and `getByRole("button", { name: /analyze test coverage/i })` all still resolve (same `id`/`htmlFor` pairs, same button text; `motion.button` renders a real `<button>`).

- [ ] **Step 3: Run the full suite and build**

Run: `npm test && npm run build`
Expected: 9/9 passing, build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat(frontend): dark restyle of Home page"
```

---

### Task 5: Restyle `Results` (state panels, coverage matrix, missing scenarios, tool trace)

**Files:**
- Modify: `frontend/src/pages/Results.tsx`

**Interfaces:**
- Consumes: `StatusBadge` (Task 2), `@theme` tokens (Task 1). No new exports.

- [ ] **Step 1: Restyle `Results`**

`frontend/src/pages/Results.tsx` (full file):
```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { AlertCircle, AlertTriangle, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { getAnalysis, getReport, createGithubIssue } from "../api/client";
import type { AnalysisStatus, Report } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

type CoverageRow = { criterion_id: string; status: string; explanation: string };
type MissingTestRow = { behavior: string };
type ToolCallRow = { node: string; tool: string; duration_ms: number };

export function Results() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [issueUrl, setIssueUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    async function poll() {
      const current = await getAnalysis(id!);
      if (cancelled) return;
      setStatus(current);
      if (current.status === "completed") {
        setReport(await getReport(id!));
      } else if (current.status !== "failed") {
        setTimeout(poll, 3000);
      }
    }
    poll();
    return () => { cancelled = true; };
  }, [id]);

  async function handleCreateIssue() {
    if (!id) return;
    if (!window.confirm("Create a GitHub issue for the missing tests?")) return;
    const result = await createGithubIssue(id);
    setIssueUrl(result.github_issue_url);
  }

  if (!status) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-5 px-5 py-6 pb-12">
        <div className="flex flex-col items-center justify-center gap-4 py-12 text-center text-text-secondary">
          <Loader2 className="h-8 w-8 animate-spin text-accent" aria-hidden="true" />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (status.status === "failed") {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-5 px-5 py-6 pb-12">
        <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-border bg-surface/60 p-8 text-center text-danger backdrop-blur-md">
          <AlertCircle className="h-8 w-8" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-danger">Analysis failed</h2>
          <p>{status.error_message}</p>
        </div>
      </div>
    );
  }

  if (status.status !== "completed" || !report) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-5 px-5 py-6 pb-12">
        <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-border bg-surface/60 p-8 text-center text-text-secondary backdrop-blur-md">
          <Loader2 className="h-8 w-8 animate-spin text-accent" aria-hidden="true" />
          <p>Analyzing... ({status.status})</p>
        </div>
      </div>
    );
  }

  const missingTests = report.missing_tests as MissingTestRow[];
  const coverageMatrix = report.coverage_matrix as CoverageRow[];
  const toolCallTrace = report.tool_call_trace as ToolCallRow[];
  const finalIssueUrl = issueUrl ?? status.github_issue_url;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-5 py-6 pb-12">
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-border bg-surface/60 p-5 backdrop-blur-md">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">
            {status.repository}#{status.issue_number}
          </h1>
          {status.requirement_summary && (
            <p className="mt-1 text-text-secondary">{status.requirement_summary}</p>
          )}
        </div>
        <div className="flex min-w-20 flex-col items-end">
          <span className="bg-gradient-to-r from-indigo-400 to-violet-500 bg-clip-text text-3xl font-bold leading-tight text-transparent">
            {status.coverage_summary?.percent_covered ?? "-"}%
          </span>
          <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">Coverage</span>
        </div>
      </div>

      <section className="rounded-2xl border border-border bg-surface/60 p-5 backdrop-blur-md">
        <h2 className="mb-4 text-lg font-semibold text-text">Coverage Matrix</h2>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="whitespace-nowrap border-b border-border px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Criterion
                </th>
                <th className="whitespace-nowrap border-b border-border px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Status
                </th>
                <th className="whitespace-nowrap border-b border-border px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Explanation
                </th>
              </tr>
            </thead>
            <tbody>
              {coverageMatrix.map((row, i) => (
                <motion.tr
                  key={row.criterion_id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="hover:bg-bg"
                >
                  <td className="border-b border-border px-3 py-3 align-top font-mono text-xs text-text-secondary">
                    {row.criterion_id}
                  </td>
                  <td className="border-b border-border px-3 py-3 align-top">
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="border-b border-border px-3 py-3 align-top text-text">{row.explanation}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-surface/60 p-5 backdrop-blur-md">
        <h2 className="mb-4 text-lg font-semibold text-text">Missing Scenarios</h2>
        {missingTests.length === 0 ? (
          <p className="text-text-secondary">No missing scenarios detected.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {missingTests.map((m, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-start gap-2 text-text"
              >
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-warning" aria-hidden="true" />
                {m.behavior}
              </motion.li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border border-border bg-surface/60 p-5 backdrop-blur-md">
        <h2 className="mb-4 text-lg font-semibold text-text">Tool Call History</h2>
        <ul className="flex flex-col gap-3">
          {toolCallTrace.map((t, i) => (
            <li
              key={i}
              className="border-b border-dashed border-border pb-2 font-mono text-xs text-text-secondary last:border-b-0 last:pb-0"
            >
              <span className="float-right text-text-muted">{t.duration_ms}ms</span>
              <span className="font-semibold text-text">{t.node}</span> → {t.tool}
            </li>
          ))}
        </ul>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <motion.button
          onClick={handleCreateIssue}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-accent/15 px-4 py-3 text-sm font-semibold text-accent transition-colors hover:bg-accent/25 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!!status.github_issue_url || !!issueUrl}
        >
          Create GitHub issue
        </motion.button>
      </div>
      {finalIssueUrl && (
        <p className="text-text-secondary">
          Issue: <a href={finalIssueUrl} className="text-accent hover:underline">{finalIssueUrl}</a>
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run `Results`'s tests**

Run: `npm test -- Results`
Expected: both tests pass — `getByText(/not covered/i)`, `getByText(/401 on bad password/i)`, `queryByRole("link", { name: /download report/i })` absent, `getByText("50%")`, `getByText("acme/widgets#42")`, `getByText("-%")` all still resolve (same text nodes, same conditional rendering logic — only the classNames and icon components changed).

- [ ] **Step 3: Run the full suite and build**

Run: `npm test && npm run build`
Expected: 9/9 passing, build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Results.tsx
git commit -m "feat(frontend): dark restyle of Results page with staggered motion"
```

---

### Task 6: Restyle `History` (table, skeleton loading, motion link)

**Files:**
- Modify: `frontend/src/pages/History.tsx`

**Interfaces:**
- Consumes: `StatusBadge` (Task 2), `@theme` tokens (Task 1). No new exports.

- [ ] **Step 1: Restyle `History`**

`frontend/src/pages/History.tsx` (full file):
```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { listAnalyses } from "../api/client";
import type { AnalysisStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

const MotionLink = motion(Link);

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}

function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: 5 }).map((_, i) => (
        <td key={i} className="border-b border-border px-3 py-3">
          <div className="h-4 rounded bg-border" />
        </td>
      ))}
    </tr>
  );
}

export function History() {
  const [analyses, setAnalyses] = useState<AnalysisStatus[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    listAnalyses().then((result) => {
      setAnalyses(result.analyses);
      setLoaded(true);
    });
  }, []);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5 px-5 py-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Analysis History</h1>
      </div>
      <div className="overflow-hidden rounded-2xl border border-border bg-surface/60 backdrop-blur-md">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="whitespace-nowrap border-b border-border px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Repository
                </th>
                <th className="whitespace-nowrap border-b border-border px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Issue
                </th>
                <th className="whitespace-nowrap border-b border-border px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Date
                </th>
                <th className="whitespace-nowrap border-b border-border px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Status
                </th>
                <th className="whitespace-nowrap border-b border-border px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Coverage
                </th>
              </tr>
            </thead>
            <tbody>
              {!loaded && Array.from({ length: 3 }).map((_, i) => <SkeletonRow key={i} />)}
              {loaded && analyses.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-text-secondary">
                    <div className="font-semibold text-text">No analyses yet</div>
                    <div>Run one from the New analysis page to see it here.</div>
                  </td>
                </tr>
              )}
              {analyses.map((a) => (
                <tr key={a.analysis_id} className="hover:bg-bg">
                  <td className="border-b border-border px-3 py-3 align-top text-text">{a.repository}</td>
                  <td className="border-b border-border px-3 py-3 align-top">
                    <MotionLink
                      to={`/analyses/${a.analysis_id}`}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      className="inline-block text-accent hover:underline"
                    >
                      {a.issue_number}
                    </MotionLink>
                  </td>
                  <td className="border-b border-border px-3 py-3 align-top text-text-secondary">
                    {formatDate(a.created_at)}
                  </td>
                  <td className="border-b border-border px-3 py-3 align-top">
                    <StatusBadge status={a.status} />
                  </td>
                  <td className="border-b border-border px-3 py-3 align-top text-text">
                    {a.coverage_summary?.percent_covered ?? "-"}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run `History`'s tests**

Run: `npm test -- History`
Expected: pass — `getByText("acme/widgets")` and `getByRole("link", { name: /42/ })` with `href="/analyses/a1"` still resolve (`MotionLink` forwards `to` through to the underlying `react-router` `Link`, which still renders a real `<a href>`).

- [ ] **Step 3: Run the full suite and build**

Run: `npm test && npm run build`
Expected: 9/9 passing, build succeeds. (`App.test.tsx`'s History route test checks `getByRole("columnheader", { name: /repository/i })`, which is present regardless of loading state since `<thead>` always renders.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/History.tsx
git commit -m "feat(frontend): dark restyle of History page with skeleton loading"
```

---

### Task 7: Remove `base.css`, final verification

**Files:**
- Delete: `frontend/src/styles/base.css`
- Modify: `frontend/src/main.tsx`

**Interfaces:**
- None — cleanup only.

- [ ] **Step 1: Confirm nothing still references `base.css`'s classes or the file itself**

Run: `grep -rn "base.css" frontend/src`
Expected: no output (only `main.tsx`'s import, removed in the next step).

Run: `grep -rnE 'className="[^"]*\b(card|btn|badge|field|form|spinner|state-panel|data-table|table-scroll|table-card|actions-row|scenario-list|trace-list|coverage-stat|results-header|page-narrow|page-wide|page-header|empty-state|empty-inline|issue-link)\b' frontend/src`
Expected: no output (all old class-based markup was replaced in Tasks 2–6).

- [ ] **Step 2: Remove the `base.css` import and delete the file**

`frontend/src/main.tsx` (full file):
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/tokens.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode><App /></StrictMode>
);
```

```bash
rm frontend/src/styles/base.css
```

- [ ] **Step 3: Full verification — tests, build, and a real browser check**

Run: `npm test`
Expected: 9/9 passing.

Run: `npm run build`
Expected: succeeds with no errors or warnings about unresolved imports.

Start the dev server (`npm run dev`) and, using the project's `run` skill or a browser tool, walk through: Home (form renders, dark background, gradient button) → submit an analysis and land on Results (loading spinner, then either the completed report layout with the coverage matrix/missing scenarios/tool trace, or the failed-state panel) → History (skeleton rows while loading, then the populated table with a working link back to Results). Confirm no unstyled-flash, no light-background remnants, and no console errors. Per this project's CLAUDE.md, this manual browser check is required before calling the frontend change complete — screenshots or a written walkthrough description count as evidence.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.tsx
git rm frontend/src/styles/base.css
git commit -m "chore(frontend): remove legacy base.css now fully migrated to Tailwind"
```

---

## Plan Self-Review Notes

- **Spec coverage:** §3 (tooling) → Task 1, 2. §4 (palette/tokens) → Task 1 Step 3. §5 (component changes: Layout/cards/buttons/forms/tables/loading/StatusBadge) → Tasks 2–6. §6 (motion: page transitions, hover/tap, Results stagger) → Tasks 3, 4, 5, 6. §7 (non-goals) → respected throughout (no new routes/deps/toggle). §8 (testing/verification) → each task's Step 2/3 + Task 7 Step 3's manual browser walkthrough. §9 (risks) → Task 1 Step 4 verifies the Vite plugin wiring immediately; Tasks 2–6 migrate one page/component at a time as the risk mitigation specified.
- **Placeholder scan:** no TBDs; every step has literal runnable commands or complete file contents.
- **Type consistency:** `cn()` signature (`cn(...inputs: ClassValue[]): string`) is defined once in Task 2 and never redefined; `StatusBadge`'s `{ status: string }` prop is unchanged from the original component, so `Results.tsx`/`History.tsx` usages in Tasks 5/6 don't need to change their call sites.

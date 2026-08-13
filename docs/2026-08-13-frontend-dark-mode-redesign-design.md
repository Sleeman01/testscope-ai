# TestScope AI — Frontend Dark-Mode Redesign

## 1. Goal

Restyle the existing `frontend/` (React 18 + Vite + TS) into a high-contrast,
dark-mode-only dashboard aesthetic inspired by Linear/Vercel/Stripe, using
Tailwind CSS, `lucide-react`, `framer-motion`, `clsx`, and `tailwind-merge`.

This is a visual/architectural restyle, not a feature change. No new routes,
no new backend calls, no change to what data is shown or how it's fetched.

## 2. Context

The frontend already has three working, tested routes matching
`docs/2026-07-30-testscope-ai-design.md` §8 exactly:

- **Home** (`/`) — repository + issue number + notes form → `POST /api/analyses`
- **Results** (`/analyses/:id`) — polls `GET /api/analyses/{id}`, renders the
  report from `GET /api/analyses/{id}/report` once `status=completed`,
  "Create GitHub issue" button → `POST /api/analyses/{id}/github-issue`
- **History** (`/history`) — table of past analyses via `GET /api/analyses`

Styling today is a hand-rolled CSS custom-property system
(`src/styles/tokens.css` + `src/styles/base.css`): light content area, dark
header/nav chrome, indigo accent. No component library, no Tailwind.

The 9-test Vitest suite (`Home.test.tsx`, `Results.test.tsx`,
`History.test.tsx`, `App.test.tsx`, `client.test.ts`) queries exclusively by
role/label/text (Testing Library conventions) — none assert on CSS classes or
colors. This is confirmed, not assumed (read all five files directly).

**Approved in chat before this spec was written:**
- New npm dependencies: Tailwind CSS, `lucide-react`, `framer-motion`,
  `clsx`, `tailwind-merge`.
- Scope stays to the existing 3 routes — no new pages (no Settings/Control
  Center/command palette; there's no backend surface for them).
- Dark-only (no light mode, no theme toggle) — simplest option, consistent
  with having no Settings page to host a toggle.
- Tailwind v4 (CSS-first `@theme`, `@tailwindcss/vite` plugin) over v3.

## 3. Tooling & Architecture

- Add `tailwindcss` + `@tailwindcss/vite` (v4), `lucide-react`,
  `framer-motion`, `clsx`, `tailwind-merge` to `frontend/package.json`.
- Wire `@tailwindcss/vite` into `vite.config.ts`.
- `src/styles/tokens.css` is rewritten as a Tailwind `@theme` block — same
  custom-property *names* (`--color-bg`, `--color-accent`,
  `--color-success`, etc.), new dark values, so the token *contract* other
  files reference doesn't silently drift.
- `src/styles/base.css`'s hand-rolled component classes (`.card`, `.btn`,
  `.btn-primary`, `.badge`, `.data-table`, `.form`, `.field`, `.spinner`,
  `.state-panel`, etc.) are removed; their usages in JSX are replaced with
  Tailwind utility classes composed inline.
- New `src/lib/cn.ts`: a `cn(...)` helper (`clsx` + `tailwind-merge`) for
  conditional/variant class composition — used first in `StatusBadge`
  (variant → color mapping) and anywhere else a component's class list
  branches on props/state.
- No other new files/directories. No change to `src/api/client.ts`,
  `src/api/types.ts`, or any routing/data logic.

## 4. Palette & Design Tokens

Values below become the new `@theme` block, keyed to the existing
custom-property names so nothing else needs to change its variable
references — only what those variables resolve to.

| Token | Old (light) | New (dark) |
|---|---|---|
| `--color-bg` | `#f6f6fb` | `#0B0F17` |
| `--color-surface` | `#ffffff` | `#0F172A` @ ~60% + `backdrop-blur-md` (glass card) |
| `--color-border` | `#e4e4ee` | `slate-800` |
| `--color-text` | `#14141f` | `#F8FAFC` |
| `--color-text-secondary` | `#5b5b6b` | `#94A3B8` |
| `--color-text-muted` | `#8a8a9a` | `slate-500` |
| `--color-accent` | `#6d5ef8` solid | `indigo-500 → violet-600` gradient, `shadow-indigo-500/20` hover glow |
| `--color-success` | `#16a34a` | `#10B981` |
| `--color-warning` | `#b45309` | `#F59E0B` |
| `--color-danger` | `#dc2626` | `#EF4444` |
| `--color-progress` | `#6d5ef8` | `#3B82F6` |
| `--color-neutral` | `#6b7280` | `slate-500` |
| `--radius-*`, `--space-*`, `--font-*` | as-is | unchanged (already reasonable) |

`StatusBadge`'s existing `classify()` logic (string → variant) is unchanged;
only the variant → color mapping changes.

## 5. Component-Level Changes

- **`Layout`**: sticky glass header (`backdrop-blur-md bg-slate-900/60`,
  `border-b border-slate-800`), nav active-state gets an underline/glow
  instead of the current `.active` class swap. Same `NavLink`/`Outlet`
  structure — no markup semantics change.
- **Cards** (`.card` usages in Home, Results, History): glass surface,
  `border-slate-800`, `rounded-2xl`. No `hover:scale` on static
  (non-interactive) cards — only on genuinely clickable elements (buttons,
  History row links), matching the "don't animate things that don't
  respond to interaction" principle.
- **Buttons**: primary = indigo→violet gradient fill + hover glow;
  secondary/outline = same tonal relationship as today, restyled dark.
  Same `<button>` elements, same `type`/`disabled`/`onClick` props, same
  visible text — `getByRole("button", { name: ... })` queries unaffected.
- **Forms** (Home): dark inputs, `focus:ring-2 focus:ring-indigo-500/50`.
  Same `<label htmlFor>`/`<input id>` pairing — `getByLabelText` queries
  unaffected.
- **Tables** (History, Results' coverage matrix): dark header row, row
  hover highlight. Same `<table>/<thead>/<th>/<tbody>/<td>` semantics —
  `getByRole("columnheader")` etc. unaffected.
- **Loading states**: History's table-loading row becomes a Tailwind
  `animate-pulse` skeleton instead of a bare spinner; Results/Home keep
  the existing spinner (already using inline SVG/CSS animation, restyled
  to the new palette only).
- **`StatusBadge`** icons: swap the current inline hand-drawn SVGs for the
  equivalent `lucide-react` icons (`CheckCircle2`, `XCircle`,
  `AlertTriangle`, `Clock`, `Circle`), same semantic variant mapping.

## 6. Motion (`framer-motion`)

Deliberately minimal for a 3-page app — no drag, no complex orchestration:

- Page-level fade/slide-in on route change, via `AnimatePresence` wrapping
  `<Outlet />` in `Layout` (or in `App.tsx` around `<Routes>`).
- `whileHover`/`whileTap` scale on buttons and History's clickable rows.
- Results page: coverage-matrix rows and missing-scenario list items
  stagger in once data loads.

## 7. Non-Goals

- No new pages, routes, or backend endpoints.
- No light mode / theme toggle.
- No change to polling behavior, error handling, or data shapes.
- No visual regression/snapshot testing added (out of scope; existing
  role/text-based tests are the safety net).

## 8. Testing & Verification

- No test files are expected to need changes — all 9 existing tests query
  by role/label/text, not by class name or color. Full suite (`npm test`
  from `frontend/`) must remain 9/9 passing after the restyle.
- If the skeleton-loading change to History alters what text is present
  during the loading state, `History.test.tsx`'s existing loading-state
  assertion will be re-checked and updated only if it actually breaks —
  not preemptively.
- `npm run build` (`tsc -b && vite build`) must stay green.
- Manual verification: run `npm run dev`, walk through Home → submit →
  Results (polling + completed states) → History, in a real browser,
  before calling this done.

## 9. Risks

- Tailwind v4's `@theme`-based token system is newer; if `@tailwindcss/vite`
  has friction with this project's existing `vite.config.ts` (e.g. plugin
  ordering with `@vitejs/plugin-react`), that's a real risk to budget time
  for — mitigated by testing the dev server and build immediately after
  wiring it in, before doing any component restyling.
- Removing `base.css`'s component classes wholesale is a larger diff than a
  purely additive change; mitigated by doing it one page/component at a
  time and running the test suite after each.

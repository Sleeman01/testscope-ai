import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { AlertCircle, AlertTriangle, CheckCircle2, Loader2, MinusCircle, XCircle } from "lucide-react";
import { motion } from "framer-motion";
import { getAnalysis, getReport, createGithubIssue } from "../api/client";
import type { AnalysisStatus, Report } from "../api/types";
import { StatusBadge, classify, type Variant } from "../components/StatusBadge";
import { cn } from "../lib/cn";

// report's fields are loosely typed as Record<string, unknown> in ../api/types (the
// backend's coverage_matrix/missing_tests/tool_call_trace are open-ended JSON, not a
// fixed schema) — these narrow just the fields this page actually renders.
type CoverageRow = { criterion_id: string; status: string; explanation: string };
type MissingTestRow = { behavior: string };
type ToolCallRow = { node: string; tool: string; duration_ms: number };

const RING_RADIUS = 40;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

// Icon + tint per row-badge variant, matching the mockup's explicit check/minus/x set.
// progress/neutral aren't expected for a per-criterion status (those variants describe an
// analysis-level state), but are covered for completeness rather than assuming they can't occur.
const ROW_ICONS: Record<Variant, { Icon: typeof CheckCircle2; classes: string }> = {
  success: { Icon: CheckCircle2, classes: "bg-success/15 text-success" },
  warning: { Icon: MinusCircle, classes: "bg-warning/15 text-warning" },
  danger: { Icon: XCircle, classes: "bg-danger/15 text-danger" },
  progress: { Icon: MinusCircle, classes: "bg-neutral/15 text-neutral" },
  neutral: { Icon: MinusCircle, classes: "bg-neutral/15 text-neutral" },
};

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}

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
      <div className="mx-auto flex max-w-2xl flex-col gap-6 px-5 py-6 pb-12">
        <div className="flex flex-col items-center justify-center gap-4 py-12 text-center text-text-secondary">
          <Loader2 className="h-8 w-8 animate-spin text-accent" aria-hidden="true" />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (status.status === "failed") {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-6 px-5 py-6 pb-12">
        <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-border bg-surface p-8 text-center text-danger">
          <AlertCircle className="h-8 w-8" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-danger">Analysis failed</h2>
          <p>{status.error_message}</p>
        </div>
      </div>
    );
  }

  if (status.status !== "completed" || !report) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-6 px-5 py-6 pb-12">
        <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-border bg-surface p-8 text-center text-text-secondary">
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

  const counts = { success: 0, warning: 0, danger: 0 };
  for (const row of coverageMatrix) {
    const variant = classify(row.status);
    if (variant === "success" || variant === "warning" || variant === "danger") {
      counts[variant] += 1;
    }
  }

  const pct = status.coverage_summary?.percent_covered;
  const ringOffset = RING_CIRCUMFERENCE - ((pct ?? 0) / 100) * RING_CIRCUMFERENCE;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-5 py-6 pb-12">
      {/* Hero */}
      <div className="rounded-2xl border border-border bg-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-3">
              <StatusBadge status={status.status} />
              <span className="text-xs text-text-muted">{formatDate(status.updated_at)}</span>
            </div>
            <h1 className="mt-3 text-2xl font-bold tracking-tight text-text">
              {status.repository}
              <span className="mt-1 block text-sm font-medium text-text-muted">
                #{status.issue_number}
              </span>
            </h1>
            {status.requirement_summary && (
              <p className="mt-2 text-sm text-text-secondary">{status.requirement_summary}</p>
            )}
          </div>
          <div className="relative h-24 w-24 flex-shrink-0">
            <svg viewBox="0 0 96 96" className="h-24 w-24 -rotate-90" aria-hidden="true">
              <circle cx="48" cy="48" r={RING_RADIUS} fill="none" strokeWidth="8" className="stroke-border" />
              <circle
                cx="48"
                cy="48"
                r={RING_RADIUS}
                fill="none"
                strokeWidth="8"
                strokeLinecap="round"
                className="stroke-accent"
                strokeDasharray={RING_CIRCUMFERENCE}
                strokeDashoffset={pct == null ? RING_CIRCUMFERENCE : ringOffset}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center text-xl font-bold text-text">
              {pct ?? "-"}%
            </div>
          </div>
        </div>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl bg-success/10 p-5">
          <div className="flex items-center gap-2 text-success">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            <span className="text-xs font-semibold uppercase tracking-wide">Covered</span>
          </div>
          <div className="mt-2 text-3xl font-bold text-text">{counts.success}</div>
        </div>
        <div className="rounded-xl bg-warning/10 p-5">
          <div className="flex items-center gap-2 text-warning">
            <MinusCircle className="h-4 w-4" aria-hidden="true" />
            <span className="text-xs font-semibold uppercase tracking-wide">Partial</span>
          </div>
          <div className="mt-2 text-3xl font-bold text-text">{counts.warning}</div>
        </div>
        <div className="rounded-xl bg-danger/10 p-5">
          <div className="flex items-center gap-2 text-danger">
            <XCircle className="h-4 w-4" aria-hidden="true" />
            <span className="text-xs font-semibold uppercase tracking-wide">Missing</span>
          </div>
          <div className="mt-2 text-3xl font-bold text-text">{counts.danger}</div>
        </div>
      </div>

      {/* Coverage matrix */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-text">Coverage Matrix</h2>
        <div className="flex flex-col gap-3">
          {coverageMatrix.map((row, i) => {
            const variant = classify(row.status);
            const { Icon, classes } = ROW_ICONS[variant];
            return (
              <motion.div
                key={row.criterion_id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-start gap-4 rounded-xl bg-surface p-4"
              >
                <span
                  className={cn(
                    "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-[7px]",
                    classes
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  <span className="sr-only">{row.status}</span>
                </span>
                <div>
                  <p className="font-mono text-sm font-bold text-text">{row.criterion_id}</p>
                  <p className="mt-1 text-sm text-text-secondary">{row.explanation}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-surface p-6">
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

      <section className="rounded-2xl border border-border bg-surface p-6">
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
          className="inline-flex items-center justify-center gap-2 rounded-md border border-border bg-surface px-4 py-3 text-sm font-semibold text-text transition-colors hover:bg-bg disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!!status.github_issue_url || !!issueUrl}
        >
          Create GitHub issue
        </motion.button>
      </div>
      {finalIssueUrl && (
        <p className="text-text-secondary">
          Issue: <a href={finalIssueUrl} className="text-text underline hover:no-underline">{finalIssueUrl}</a>
        </p>
      )}
    </div>
  );
}

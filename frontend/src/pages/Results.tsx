import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  MinusCircle,
  XCircle,
} from "lucide-react";
import { motion } from "framer-motion";
import { getAnalysis, getReport, createGithubIssue } from "../api/client";
import type { AnalysisStatus, Report } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { classifyStatus, type StatusBadgeVariant } from "../components/statusBadgeUtils";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { PageContainer } from "../components/ui/PageContainer";
import { SectionHeader } from "../components/ui/SectionHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { Spinner } from "../components/ui/Spinner";
import { StatTile } from "../components/ui/StatTile";
import { cn } from "../lib/cn";

type CoverageRow = { criterion_id: string; status: string; explanation: string };
type MissingTestRow = { behavior: string };
type ToolCallRow = { node: string; tool: string; duration_ms: number };

const MotionButton = motion.create(Button);

const RING_RADIUS = 40;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

const ROW_ICONS: Record<StatusBadgeVariant, { Icon: typeof CheckCircle2; classes: string }> = {
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

function ResultsSkeleton() {
  return (
    <>
      <Card variant="elevated" className="flex flex-wrap items-start justify-between gap-6">
        <div className="flex flex-1 flex-col gap-3">
          <Skeleton className="h-6 w-24 rounded-full" />
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-full max-w-md" />
        </div>
        <Skeleton className="h-24 w-24 rounded-full" />
      </Card>
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <div className="flex flex-col gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    </>
  );
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
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function handleCreateIssue() {
    if (!id) return;
    if (!window.confirm("Create a GitHub issue for the missing tests?")) return;
    const result = await createGithubIssue(id);
    setIssueUrl(result.github_issue_url);
  }

  if (!status) {
    return (
      <PageContainer maxWidth="4xl">
        <ResultsSkeleton />
      </PageContainer>
    );
  }

  if (status.status === "failed") {
    return (
      <PageContainer maxWidth="4xl">
        <Card variant="elevated" className="flex flex-col items-center gap-4 p-8 text-center text-danger">
          <AlertCircle className="h-8 w-8" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-danger">Analysis failed</h2>
          <p className="text-text-secondary">{status.error_message}</p>
        </Card>
      </PageContainer>
    );
  }

  if (status.status !== "completed" || !report) {
    return (
      <PageContainer maxWidth="4xl">
        <Card variant="elevated" className="p-8">
          <Spinner message={`Analyzing... (${status.status})`} />
        </Card>
      </PageContainer>
    );
  }

  const missingTests = report.missing_tests as MissingTestRow[];
  const coverageMatrix = report.coverage_matrix as CoverageRow[];
  const toolCallTrace = report.tool_call_trace as ToolCallRow[];
  const finalIssueUrl = issueUrl ?? status.github_issue_url;

  const counts = { success: 0, warning: 0, danger: 0 };
  for (const row of coverageMatrix) {
    const variant = classifyStatus(row.status);
    if (variant === "success" || variant === "warning" || variant === "danger") {
      counts[variant] += 1;
    }
  }

  const pct = status.coverage_summary?.percent_covered;
  const ringOffset = RING_CIRCUMFERENCE - ((pct ?? 0) / 100) * RING_CIRCUMFERENCE;
  const coverageLabel =
    pct == null ? "Coverage unavailable" : `Coverage: ${pct} percent`;

  return (
    <PageContainer maxWidth="4xl">
      <Card variant="elevated">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-3">
              <StatusBadge status={status.status} />
              <span className="text-xs text-text-muted">{formatDate(status.updated_at)}</span>
            </div>
            <h1 className="mt-3 text-title font-bold tracking-tight text-text">
              {status.repository}
              <span className="mt-1 block text-sm font-medium text-text-muted">
                #{status.issue_number}
              </span>
            </h1>
            {status.requirement_summary && (
              <p className="mt-2 text-sm text-text-secondary">{status.requirement_summary}</p>
            )}
          </div>
          <div
            className="relative h-24 w-24 flex-shrink-0"
            role="img"
            aria-label={coverageLabel}
          >
            <svg viewBox="0 0 96 96" className="h-24 w-24 -rotate-90" aria-hidden="true">
              <circle
                cx="48"
                cy="48"
                r={RING_RADIUS}
                fill="none"
                strokeWidth="8"
                className="stroke-border"
              />
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
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatTile
          label="Covered"
          value={counts.success}
          tone="success"
          icon={<CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
        />
        <StatTile
          label="Partial"
          value={counts.warning}
          tone="warning"
          icon={<MinusCircle className="h-4 w-4" aria-hidden="true" />}
        />
        <StatTile
          label="Missing"
          value={counts.danger}
          tone="danger"
          icon={<XCircle className="h-4 w-4" aria-hidden="true" />}
        />
      </div>

      <section>
        <SectionHeader title="Coverage Matrix" />
        <div className="flex flex-col gap-3">
          {coverageMatrix.map((row, i) => {
            const variant = classifyStatus(row.status);
            const { Icon, classes } = ROW_ICONS[variant];
            return (
              <motion.div
                key={row.criterion_id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-start gap-4 rounded-xl border border-border bg-surface p-4 transition-colors duration-[var(--duration-fast)] hover:bg-surface-elevated"
              >
                <span
                  className={cn(
                    "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md",
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

      <Card variant="bordered">
        <SectionHeader title="Missing Scenarios" className="mb-0" />
        {missingTests.length === 0 ? (
          <p className="text-text-secondary">No missing scenarios detected.</p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {missingTests.map((m, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-start gap-2 text-text"
              >
                <AlertTriangle
                  className="mt-0.5 h-4 w-4 flex-shrink-0 text-warning"
                  aria-hidden="true"
                />
                {m.behavior}
              </motion.li>
            ))}
          </ul>
        )}
      </Card>

      <Card variant="bordered">
        <SectionHeader title="Tool Call History" className="mb-0" />
        <ul className="mt-4 flex flex-col gap-3">
          {toolCallTrace.map((t, i) => (
            <li
              key={i}
              className="flex items-start justify-between gap-4 border-b border-dashed border-border pb-2 font-mono text-xs text-text-secondary last:border-b-0 last:pb-0"
            >
              <span>
                <span className="font-semibold text-text">{t.node}</span> → {t.tool}
              </span>
              <span className="flex-shrink-0 text-text-muted">{t.duration_ms}ms</span>
            </li>
          ))}
        </ul>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <MotionButton
          variant="secondary"
          onClick={handleCreateIssue}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          disabled={!!status.github_issue_url || !!issueUrl}
        >
          Create GitHub issue
        </MotionButton>
      </div>
      {finalIssueUrl && (
        <p className="text-text-secondary">
          Issue:{" "}
          <a
            href={finalIssueUrl}
            className="text-accent underline transition-colors duration-[var(--duration-fast)] hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
          >
            {finalIssueUrl}
          </a>
        </p>
      )}
    </PageContainer>
  );
}

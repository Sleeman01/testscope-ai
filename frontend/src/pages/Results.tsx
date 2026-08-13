import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { AlertCircle, AlertTriangle, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { getAnalysis, getReport, createGithubIssue } from "../api/client";
import type { AnalysisStatus, Report } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

// report's fields are loosely typed as Record<string, unknown> in ../api/types (the
// backend's coverage_matrix/missing_tests/tool_call_trace are open-ended JSON, not a
// fixed schema) — these narrow just the fields this page actually renders.
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

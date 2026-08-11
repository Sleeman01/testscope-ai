import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
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
      <div className="page-narrow">
        <div className="state-panel">
          <span className="spinner spinner-lg" aria-hidden="true" />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (status.status === "failed") {
    return (
      <div className="page-narrow">
        <div className="card state-panel state-panel-error">
          <svg className="state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="9" />
            <path d="M9 9l6 6M15 9l-6 6" />
          </svg>
          <h2>Analysis failed</h2>
          <p>{status.error_message}</p>
        </div>
      </div>
    );
  }

  if (status.status !== "completed" || !report) {
    return (
      <div className="page-narrow">
        <div className="card state-panel">
          <span className="spinner spinner-lg" aria-hidden="true" />
          <p>Analyzing... ({status.status})</p>
        </div>
      </div>
    );
  }

  const missingTests = report.missing_tests as MissingTestRow[];
  const finalIssueUrl = issueUrl ?? status.github_issue_url;

  return (
    <div className="page-narrow">
      <div className="card results-header">
        <div>
          <h1>{status.repository}#{status.issue_number}</h1>
          {status.requirement_summary && <p className="card-subtitle">{status.requirement_summary}</p>}
        </div>
        <div className="coverage-stat">
          <span className="coverage-stat-value">{status.coverage_summary?.percent_covered}%</span>
          <span className="coverage-stat-label">Coverage</span>
        </div>
      </div>

      <section className="card">
        <h2>Coverage Matrix</h2>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Criterion</th>
                <th>Status</th>
                <th>Explanation</th>
              </tr>
            </thead>
            <tbody>
              {(report.coverage_matrix as CoverageRow[]).map((row) => (
                <tr key={row.criterion_id}>
                  <td className="mono">{row.criterion_id}</td>
                  <td><StatusBadge status={row.status} /></td>
                  <td>{row.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Missing Scenarios</h2>
        {missingTests.length === 0 ? (
          <p className="empty-inline">No missing scenarios detected.</p>
        ) : (
          <ul className="scenario-list">
            {missingTests.map((m, i) => (
              <li key={i}>
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M8 2 14.5 13.5H1.5L8 2Z" />
                  <path d="M8 6.5v3M8 11.5h.01" />
                </svg>
                {m.behavior}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>Tool Call History</h2>
        <ul className="trace-list">
          {(report.tool_call_trace as ToolCallRow[]).map((t, i) => (
            <li key={i}>
              <span className="trace-duration">{t.duration_ms}ms</span>
              <span className="trace-node">{t.node}</span> → {t.tool}
            </li>
          ))}
        </ul>
      </section>

      <div className="actions-row">
        <button
          onClick={handleCreateIssue}
          className="btn btn-secondary"
          disabled={!!status.github_issue_url || !!issueUrl}
        >
          Create GitHub issue
        </button>
        <a href={report.download_url} className="btn btn-outline">Download report</a>
      </div>
      {finalIssueUrl && (
        <p className="issue-link">
          Issue: <a href={finalIssueUrl}>{finalIssueUrl}</a>
        </p>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getAnalysis, getReport, createGithubIssue } from "../api/client";
import type { AnalysisStatus, Report } from "../api/types";

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

  if (!status) return <p>Loading...</p>;
  if (status.status === "failed") return <p>Analysis failed: {status.error_message}</p>;
  if (status.status !== "completed" || !report) return <p>Analyzing... ({status.status})</p>;

  return (
    <div>
      <h1>{status.repository}#{status.issue_number}</h1>
      <p>Coverage: {status.coverage_summary?.percent_covered}%</p>

      <h2>Coverage Matrix</h2>
      <table>
        <tbody>
          {report.coverage_matrix.map((row: any) => (
            <tr key={row.criterion_id}>
              <td>{row.criterion_id}</td>
              <td>{row.status}</td>
              <td>{row.explanation}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Missing Scenarios</h2>
      <ul>{report.missing_tests.map((m: any, i: number) => <li key={i}>{m.behavior}</li>)}</ul>

      <h2>Tool Call History</h2>
      <ul>{report.tool_call_trace.map((t: any, i: number) => <li key={i}>{t.node} → {t.tool} ({t.duration_ms}ms)</li>)}</ul>

      <button onClick={handleCreateIssue} disabled={!!status.github_issue_url || !!issueUrl}>
        Create GitHub issue
      </button>
      {(issueUrl || status.github_issue_url) && <p>Issue: {issueUrl ?? status.github_issue_url}</p>}
      <a href={report.download_url}>Download report</a>
    </div>
  );
}

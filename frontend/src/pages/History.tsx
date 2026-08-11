import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAnalyses } from "../api/client";
import type { AnalysisStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
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
    <div className="page-wide">
      <div className="page-header">
        <h1>Analysis History</h1>
      </div>
      <div className="card table-card">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Repository</th>
                <th>Issue</th>
                <th>Date</th>
                <th>Status</th>
                <th>Coverage</th>
              </tr>
            </thead>
            <tbody>
              {!loaded && (
                <tr>
                  <td colSpan={5} className="table-loading">
                    <span className="spinner" aria-hidden="true" /> Loading history...
                  </td>
                </tr>
              )}
              {loaded && analyses.length === 0 && (
                <tr>
                  <td colSpan={5} className="empty-state">
                    <div className="empty-state-title">No analyses yet</div>
                    <div>Run one from the New analysis page to see it here.</div>
                  </td>
                </tr>
              )}
              {analyses.map((a) => (
                <tr key={a.analysis_id}>
                  <td>{a.repository}</td>
                  <td><Link to={`/analyses/${a.analysis_id}`}>{a.issue_number}</Link></td>
                  <td>{formatDate(a.created_at)}</td>
                  <td><StatusBadge status={a.status} /></td>
                  <td>{a.coverage_summary?.percent_covered ?? "-"}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

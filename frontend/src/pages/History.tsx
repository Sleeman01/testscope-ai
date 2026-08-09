import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAnalyses } from "../api/client";
import type { AnalysisStatus } from "../api/types";

export function History() {
  const [analyses, setAnalyses] = useState<AnalysisStatus[]>([]);

  useEffect(() => {
    listAnalyses().then((result) => setAnalyses(result.analyses));
  }, []);

  return (
    <table>
      <thead><tr><th>Repository</th><th>Issue</th><th>Date</th><th>Status</th><th>Coverage</th></tr></thead>
      <tbody>
        {analyses.map((a) => (
          <tr key={a.analysis_id}>
            <td>{a.repository}</td>
            <td><Link to={`/analyses/${a.analysis_id}`}>{a.issue_number}</Link></td>
            <td>{a.created_at}</td>
            <td>{a.status}</td>
            <td>{a.coverage_summary?.percent_covered ?? "-"}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

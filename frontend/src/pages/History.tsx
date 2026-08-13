import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { listAnalyses } from "../api/client";
import type { AnalysisStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

const MotionLink = motion.create(Link);

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

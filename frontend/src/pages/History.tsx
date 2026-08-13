import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { listAnalyses } from "../api/client";
import type { AnalysisStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { cn } from "../lib/cn";

const MotionLink = motion.create(Link);

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}

// Same success/warning/danger scale used for status pills and Results' stat tiles.
// Thresholds are this page's own convention — not defined anywhere else in the app.
function coverageColorClass(pct: number | null | undefined): string {
  if (pct == null) return "text-text-muted";
  if (pct >= 80) return "text-success";
  if (pct >= 50) return "text-warning";
  return "text-danger";
}

function SkeletonCard() {
  return (
    <div className="flex animate-pulse items-center justify-between gap-4 rounded-xl bg-surface p-4">
      <div className="flex flex-col gap-2">
        <div className="h-4 w-32 rounded bg-border" />
        <div className="h-3 w-10 rounded bg-border" />
      </div>
      <div className="flex flex-col items-end gap-2">
        <div className="h-5 w-24 rounded-full bg-border" />
        <div className="h-6 w-12 rounded bg-border" />
      </div>
    </div>
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
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-5 py-6 pb-12">
      <h1 className="text-2xl font-bold tracking-tight text-text">Analysis History</h1>

      <div className="flex flex-col gap-3">
        {!loaded && Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}

        {loaded && analyses.length === 0 && (
          <div className="rounded-2xl bg-surface p-8 text-center text-text-secondary">
            <p className="font-semibold text-text">No analyses yet</p>
            <p className="mt-1">Run one from the New analysis page to see it here.</p>
          </div>
        )}

        {analyses.map((a, i) => {
          const pct = a.coverage_summary?.percent_covered;
          return (
            <MotionLink
              key={a.analysis_id}
              to={`/analyses/${a.analysis_id}`}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              className="flex items-center justify-between gap-4 rounded-xl bg-surface p-4 no-underline hover:bg-bg hover:no-underline"
            >
              <div>
                <p className="font-bold text-text">{a.repository}</p>
                <p className="mt-1 text-sm text-text-muted">#{a.issue_number}</p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <div className="flex items-center gap-2">
                  <StatusBadge status={a.status} />
                  <span className="text-xs text-text-muted">{formatDate(a.created_at)}</span>
                </div>
                <span className={cn("text-2xl font-bold", coverageColorClass(pct))}>
                  {pct ?? "-"}%
                </span>
              </div>
            </MotionLink>
          );
        })}
      </div>
    </div>
  );
}

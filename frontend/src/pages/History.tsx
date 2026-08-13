import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { History as HistoryIcon } from "lucide-react";
import { motion } from "framer-motion";
import { listAnalyses } from "../api/client";
import type { AnalysisStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageContainer } from "../components/ui/PageContainer";
import { Skeleton } from "../components/ui/Skeleton";
import { cn } from "../lib/cn";

const MotionLink = motion.create(Link);

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}

function coverageColorClass(pct: number | null | undefined): string {
  if (pct == null) return "text-text-muted";
  if (pct >= 80) return "text-success";
  if (pct >= 50) return "text-warning";
  return "text-danger";
}

function HistorySkeletonRow() {
  return (
    <Card variant="bordered" className="flex items-center justify-between gap-4 p-4">
      <div className="flex flex-1 flex-col gap-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-10" />
      </div>
      <div className="flex flex-col items-end gap-2">
        <Skeleton className="h-5 w-24 rounded-full" />
        <Skeleton className="h-6 w-12" />
      </div>
    </Card>
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
    <PageContainer maxWidth="4xl">
      <h1 className="text-title font-bold tracking-tight text-text">Analysis History</h1>

      <div className="flex flex-col gap-3">
        {!loaded && Array.from({ length: 3 }).map((_, i) => <HistorySkeletonRow key={i} />)}

        {loaded && analyses.length === 0 && (
          <EmptyState
            icon={<HistoryIcon className="h-5 w-5" aria-hidden="true" />}
            title="No analyses yet"
            description="Run one from the New analysis page to see it here."
          />
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
              className={cn(
                "flex items-center justify-between gap-4 rounded-xl border border-border bg-surface p-4 no-underline",
                "transition-colors duration-[var(--duration-fast)]",
                "hover:border-border hover:bg-surface-elevated hover:shadow-card hover:no-underline",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
              )}
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
    </PageContainer>
  );
}

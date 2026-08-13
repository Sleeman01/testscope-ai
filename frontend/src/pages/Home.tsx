import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CircleDot, ClipboardList, FlaskConical, Loader2, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { createAnalysis } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Textarea } from "../components/ui/Textarea";
import { cn } from "../lib/cn";

const MotionButton = motion.create(Button);

const HOW_IT_WORKS = [
  {
    Icon: CircleDot,
    label: "Reads the issue",
    description: "Pulls the GitHub issue and its acceptance criteria.",
    accent: "text-accent-strong",
    ring: "ring-accent/30",
  },
  {
    Icon: FlaskConical,
    label: "Inspects the tests",
    description: "Scans the repo's test suite for relevant coverage.",
    accent: "text-progress",
    ring: "ring-progress/30",
  },
  {
    Icon: ClipboardList,
    label: "Reports the gaps",
    description: "Flags missing scenarios and generates a test plan.",
    accent: "text-success",
    ring: "ring-success/30",
  },
];

export function Home() {
  const [repository, setRepository] = useState("");
  const [issueNumber, setIssueNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const result = await createAnalysis(repository, Number(issueNumber), notes);
      navigate(`/analyses/${result.analysis_id}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="home-backdrop relative min-h-[calc(100dvh-4.25rem)] w-full">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "linear-gradient(rgb(148 163 184 / 0.06) 1px, transparent 1px), linear-gradient(90deg, rgb(148 163 184 / 0.06) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse 80% 70% at 50% 30%, black 20%, transparent 75%)",
        }}
      />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-10 px-5 py-10 sm:px-8 lg:gap-12 lg:py-14">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:items-start lg:gap-12">
          <div className="flex flex-col gap-8">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent-muted/50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-accent-strong">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                Test coverage intelligence
              </span>
              <h1 className="mt-4 text-display font-bold tracking-tight text-text sm:text-4xl lg:text-5xl">
                TestScope AI
              </h1>
              <p className="mt-4 max-w-xl text-base leading-relaxed text-text-secondary lg:text-lg">
                Point this at a GitHub issue and get back a test coverage matrix, missing scenarios,
                and a ready-to-file follow-up issue.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              {HOW_IT_WORKS.map(({ Icon, label, description, accent, ring }) => (
                <div
                  key={label}
                  className={cn(
                    "rounded-xl border border-border/70 bg-surface/70 p-5 ring-1 backdrop-blur-sm",
                    ring
                  )}
                >
                  <span
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg bg-surface-elevated",
                      accent
                    )}
                  >
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <p className="mt-4 text-sm font-semibold text-text">{label}</p>
                  <p className="mt-1 text-sm text-text-secondary">{description}</p>
                </div>
              ))}
            </div>
          </div>

          <Card
            variant="elevated"
            className="border-accent/20 bg-surface/85 shadow-card backdrop-blur-md lg:sticky lg:top-24"
          >
            <div className="mb-6 border-b border-border/70 pb-5">
              <h2 className="text-heading font-semibold text-text">Start an analysis</h2>
              <p className="mt-1 text-sm text-text-secondary">
                Enter a repository and issue number to begin.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <Input
                id="repository"
                label="Repository (owner/repo)"
                placeholder="acme/widgets"
                value={repository}
                onChange={(e) => setRepository(e.target.value)}
                required
              />

              <Input
                id="issue-number"
                label="Issue number"
                type="number"
                placeholder="42"
                value={issueNumber}
                onChange={(e) => setIssueNumber(e.target.value)}
                required
              />

              <Textarea
                id="notes"
                label="Notes (optional)"
                rows={4}
                placeholder="Anything extra the analysis should take into account..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />

              <MotionButton
                type="submit"
                disabled={submitting}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full bg-accent-glow hover:bg-accent-strong"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Analyzing...
                  </>
                ) : (
                  "Analyze test coverage"
                )}
              </MotionButton>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}

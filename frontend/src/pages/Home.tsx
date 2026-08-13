import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { createAnalysis } from "../api/client";

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
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-5 py-6 pb-12">
      <div className="rounded-2xl border border-border bg-surface/60 p-5 shadow-sm backdrop-blur-md">
        <h1 className="text-2xl font-bold tracking-tight text-text">TestScope AI</h1>
        <p className="mt-1 text-text-secondary">
          Point this at a GitHub issue and get back a test coverage matrix, missing scenarios, and a
          ready-to-file follow-up issue.
        </p>
        <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="repository" className="text-sm font-semibold text-text-secondary">
              Repository (owner/repo)
            </label>
            <input
              id="repository"
              placeholder="acme/widgets"
              value={repository}
              onChange={(e) => setRepository(e.target.value)}
              required
              className="rounded-md border border-border bg-bg px-3 py-3 text-text placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="issue-number" className="text-sm font-semibold text-text-secondary">
              Issue number
            </label>
            <input
              id="issue-number"
              type="number"
              placeholder="42"
              value={issueNumber}
              onChange={(e) => setIssueNumber(e.target.value)}
              required
              className="rounded-md border border-border bg-bg px-3 py-3 text-text placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="notes" className="text-sm font-semibold text-text-secondary">
              Notes (optional)
            </label>
            <textarea
              id="notes"
              rows={4}
              placeholder="Anything extra the analysis should take into account..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="min-h-22 resize-y rounded-md border border-border bg-bg px-3 py-3 text-text placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </div>

          <motion.button
            type="submit"
            disabled={submitting}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-gradient-to-r from-indigo-500 to-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-shadow hover:shadow-lg hover:shadow-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Analyzing...
              </>
            ) : (
              "Analyze test coverage"
            )}
          </motion.button>
        </form>
      </div>
    </div>
  );
}

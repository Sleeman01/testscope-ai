import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CircleDot, ClipboardList, FlaskConical, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { createAnalysis } from "../api/client";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { PageContainer } from "../components/ui/PageContainer";
import { Textarea } from "../components/ui/Textarea";

const MotionButton = motion.create(Button);

const HOW_IT_WORKS = [
  {
    Icon: CircleDot,
    label: "Reads the issue",
    description: "Pulls the GitHub issue and its acceptance criteria.",
  },
  {
    Icon: FlaskConical,
    label: "Inspects the tests",
    description: "Scans the repo's test suite for relevant coverage.",
  },
  {
    Icon: ClipboardList,
    label: "Reports the gaps",
    description: "Flags missing scenarios and generates a test plan.",
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
    <PageContainer maxWidth="2xl">
      <div>
        <h1 className="text-display font-bold tracking-tight text-text">TestScope AI</h1>
        <p className="mt-2 text-text-secondary">
          Point this at a GitHub issue and get back a test coverage matrix, missing scenarios, and a
          ready-to-file follow-up issue.
        </p>
      </div>

      <Card variant="elevated">
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
            className="w-full sm:w-auto"
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {HOW_IT_WORKS.map(({ Icon, label, description }) => (
          <Card key={label} variant="bordered" className="p-5">
            <Icon className="h-5 w-5 text-text-secondary" aria-hidden="true" />
            <p className="mt-3 text-sm font-semibold text-text">{label}</p>
            <p className="mt-1 text-sm text-text-secondary">{description}</p>
          </Card>
        ))}
      </div>
    </PageContainer>
  );
}

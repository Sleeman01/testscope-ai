import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
    <div className="page-narrow">
      <div className="card">
        <h1>TestScope AI</h1>
        <p className="card-subtitle">
          Point this at a GitHub issue and get back a test coverage matrix, missing scenarios, and a
          ready-to-file follow-up issue.
        </p>
        <form onSubmit={handleSubmit} className="form">
          <div className="field">
            <label htmlFor="repository">Repository (owner/repo)</label>
            <input
              id="repository"
              placeholder="acme/widgets"
              value={repository}
              onChange={(e) => setRepository(e.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="issue-number">Issue number</label>
            <input
              id="issue-number"
              type="number"
              placeholder="42"
              value={issueNumber}
              onChange={(e) => setIssueNumber(e.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="notes">Notes (optional)</label>
            <textarea
              id="notes"
              rows={4}
              placeholder="Anything extra the analysis should take into account..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? (
              <>
                <span className="spinner" aria-hidden="true" />
                Analyzing...
              </>
            ) : (
              "Analyze test coverage"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

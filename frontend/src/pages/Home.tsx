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
    <form onSubmit={handleSubmit}>
      <h1>TestScope AI</h1>
      <label htmlFor="repository">Repository (owner/repo)</label>
      <input id="repository" value={repository} onChange={(e) => setRepository(e.target.value)} required />

      <label htmlFor="issue-number">Issue number</label>
      <input id="issue-number" type="number" value={issueNumber} onChange={(e) => setIssueNumber(e.target.value)} required />

      <label htmlFor="notes">Notes (optional)</label>
      <textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />

      <button type="submit" disabled={submitting}>Analyze test coverage</button>
    </form>
  );
}

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Results } from "./Results";
import * as client from "../api/client";

function renderAt(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/analyses/${id}`]}>
      <Routes><Route path="/analyses/:id" element={<Results />} /></Routes>
    </MemoryRouter>
  );
}

describe("Results", () => {
  it("shows the coverage matrix once analysis completes", async () => {
    vi.spyOn(client, "getAnalysis").mockResolvedValue({
      analysis_id: "a1", repository: "acme/widgets", issue_number: 42, status: "completed",
      created_at: "", updated_at: "", requirement_summary: "Login",
      coverage_summary: { percent_covered: 50 }, missing_tests_count: 1,
      error_message: null, github_issue_url: null,
    });
    vi.spyOn(client, "getReport").mockResolvedValue({
      analysis_id: "a1", requirement: { feature_name: "Login" },
      coverage_matrix: [{ criterion_id: "AC1", status: "Not covered", explanation: "no test" }],
      test_plan: [], missing_tests: [{ behavior: "401 on bad password" }],
      tool_call_trace: [], download_url: "https://example.com/report.md",
    });
    renderAt("a1");
    await waitFor(() => expect(screen.getByText(/not covered/i)).toBeInTheDocument());
    expect(screen.getByText(/401 on bad password/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /download report/i })).not.toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  it("renders a dash instead of a bare '%' when coverage_summary is null", async () => {
    vi.spyOn(client, "getAnalysis").mockResolvedValue({
      analysis_id: "a2", repository: "acme/widgets", issue_number: 42, status: "completed",
      created_at: "", updated_at: "", requirement_summary: "Login",
      coverage_summary: null, missing_tests_count: 0,
      error_message: null, github_issue_url: null,
    });
    vi.spyOn(client, "getReport").mockResolvedValue({
      analysis_id: "a2", requirement: { feature_name: "Login" },
      coverage_matrix: [], test_plan: [], missing_tests: [],
      tool_call_trace: [], download_url: "https://example.com/report.md",
    });
    renderAt("a2");
    await waitFor(() => expect(screen.getByText("acme/widgets#42")).toBeInTheDocument());
    expect(screen.getByText("-%")).toBeInTheDocument();
  });
});

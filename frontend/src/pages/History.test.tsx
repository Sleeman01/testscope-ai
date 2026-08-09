import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { History } from "./History";
import * as client from "../api/client";

describe("History", () => {
  it("lists past analyses with a link to each", async () => {
    vi.spyOn(client, "listAnalyses").mockResolvedValue({
      analyses: [{
        analysis_id: "a1", repository: "acme/widgets", issue_number: 42, status: "completed",
        created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
        requirement_summary: "Login", coverage_summary: { percent_covered: 80 },
        missing_tests_count: 1, error_message: null, github_issue_url: null,
      }],
    });
    render(<MemoryRouter><History /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText("acme/widgets")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /42/ })).toHaveAttribute("href", "/analyses/a1");
  });
});

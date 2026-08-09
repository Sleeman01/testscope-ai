import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";
import * as client from "./api/client";

function renderAt(path: string) {
  window.history.pushState({}, "", path);
  return render(<App />);
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App routing", () => {
  it("mounts without error and renders Home at the root route", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: /testscope ai/i })).toBeInTheDocument();
  });

  it("renders Results at /analyses/:id, passing the id param through", async () => {
    vi.spyOn(client, "getAnalysis").mockResolvedValue({
      analysis_id: "a1", repository: "acme/widgets", issue_number: 42, status: "pending",
      created_at: "", updated_at: "", requirement_summary: null,
      coverage_summary: null, missing_tests_count: 0,
      error_message: null, github_issue_url: null,
    });
    renderAt("/analyses/a1");
    await waitFor(() => expect(client.getAnalysis).toHaveBeenCalledWith("a1"));
    expect(screen.getByText(/analyzing/i)).toBeInTheDocument();
  });

  it("renders History at /history", async () => {
    vi.spyOn(client, "listAnalyses").mockResolvedValue({ analyses: [] });
    renderAt("/history");
    await waitFor(() => expect(client.listAnalyses).toHaveBeenCalled());
    expect(screen.getByRole("columnheader", { name: /repository/i })).toBeInTheDocument();
  });
});

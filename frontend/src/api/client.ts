import type { AnalysisStatus, Report } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, options);
  if (!response.ok) throw new Error(`Request to ${path} failed: ${response.status}`);
  return response.json();
}

export function createAnalysis(repository: string, issueNumber: number, notes?: string) {
  return request<{ analysis_id: string; status: string }>("/api/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repository, issue_number: issueNumber, notes }),
  });
}

export function getAnalysis(id: string) {
  return request<AnalysisStatus>(`/api/analyses/${id}`);
}

export function listAnalyses() {
  return request<{ analyses: AnalysisStatus[] }>("/api/analyses");
}

export function getReport(id: string) {
  return request<Report>(`/api/analyses/${id}/report`);
}

export function createGithubIssue(id: string) {
  return request<{ github_issue_url: string }>(`/api/analyses/${id}/github-issue`, { method: "POST" });
}

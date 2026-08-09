export interface AnalysisStatus {
  analysis_id: string;
  repository: string;
  issue_number: number;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  requirement_summary: string | null;
  coverage_summary: { percent_covered: number } | null;
  missing_tests_count: number;
  error_message: string | null;
  github_issue_url: string | null;
}

export interface Report {
  analysis_id: string;
  requirement: Record<string, unknown>;
  coverage_matrix: Array<Record<string, unknown>>;
  test_plan: Array<Record<string, unknown>>;
  missing_tests: Array<Record<string, unknown>>;
  tool_call_trace: Array<Record<string, unknown>>;
  download_url: string;
}

import { describe, it, expect, vi, beforeEach } from "vitest";
import { createAnalysis, getAnalysis } from "./client";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

describe("createAnalysis", () => {
  it("POSTs to /api/analyses and returns the parsed body", async () => {
    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ analysis_id: "a1", status: "pending" }),
    });
    const result = await createAnalysis("acme/widgets", 42);
    expect(fetch).toHaveBeenCalledWith(
      "/api/analyses",
      expect.objectContaining({ method: "POST" })
    );
    expect(result.analysis_id).toBe("a1");
  });
});

describe("getAnalysis", () => {
  it("GETs /api/analyses/{id}", async () => {
    (fetch as any).mockResolvedValue({ ok: true, json: async () => ({ analysis_id: "a1", status: "completed" }) });
    const result = await getAnalysis("a1");
    expect(fetch).toHaveBeenCalledWith("/api/analyses/a1", expect.anything());
    expect(result.status).toBe("completed");
  });
});

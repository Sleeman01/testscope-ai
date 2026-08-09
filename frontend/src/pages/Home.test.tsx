import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Home } from "./Home";
import * as client from "../api/client";

describe("Home", () => {
  it("submits repository and issue number, then navigates to the results page", async () => {
    vi.spyOn(client, "createAnalysis").mockResolvedValue({ analysis_id: "a1", status: "pending" });
    render(<MemoryRouter><Home /></MemoryRouter>);

    fireEvent.change(screen.getByLabelText(/repository/i), { target: { value: "acme/widgets" } });
    fireEvent.change(screen.getByLabelText(/issue number/i), { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /analyze test coverage/i }));

    await waitFor(() => expect(client.createAnalysis).toHaveBeenCalledWith("acme/widgets", 42, ""));
  });
});

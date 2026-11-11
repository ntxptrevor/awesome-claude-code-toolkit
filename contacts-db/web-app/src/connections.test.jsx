import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("./lib/auth", () => ({
  currentUser: () => ({ email: "a@ntxpllc.com" }),
  apiJson: async () => ({ connections: [
    { system: "lightfield", label: "Lightfield", linked: 4200, last_synced_at: null, pending: 0, connected: true },
    { system: "jobtread", label: "JobTread", linked: 300, last_synced_at: null, pending: 3, connected: true },
    { system: "gcontacts", label: "Google Workspace", linked: 0, last_synced_at: null, pending: 0, connected: false },
  ] }),
}));
import { ConnectionStrip } from "./components/ConnectionStrip";

describe("ConnectionStrip", () => {
  it("shows connected / active / off states with accessible names", async () => {
    render(<ConnectionStrip />);
    await waitFor(() => expect(screen.getAllByRole("img")).toHaveLength(3));
    const [lf, jt, g] = screen.getAllByRole("img");
    expect(lf).toHaveAttribute("data-state", "on");
    expect(jt).toHaveAttribute("data-state", "active");
    expect(jt.getAttribute("aria-label")).toMatch(/3 edits waiting/);
    expect(g).toHaveAttribute("data-state", "off");
    expect(g.getAttribute("aria-label")).toMatch(/not connected/);
  });
});

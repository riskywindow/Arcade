import React from "react";
import { render, screen } from "@testing-library/react";

import HomePage from "@/app/page";
import { AppShell } from "@/components/app-shell";

describe("console shell", () => {
  it("renders the home shell copy", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", { name: "Operator console shell" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/typed api boundary/i)).toBeInTheDocument();
  });

  it("keeps the internal phase three app links visible", () => {
    render(
      <AppShell>
        <div>child</div>
      </AppShell>,
    );

    expect(screen.getByRole("link", { name: /helpdesk/i })).toHaveAttribute(
      "href",
      "/internal/helpdesk",
    );
    expect(screen.getByRole("link", { name: /directory/i })).toHaveAttribute(
      "href",
      "/internal/directory",
    );
    expect(screen.getByRole("link", { name: /wiki/i })).toHaveAttribute(
      "href",
      "/internal/wiki",
    );
    expect(screen.getByRole("link", { name: /inbox/i })).toHaveAttribute(
      "href",
      "/internal/inbox",
    );
  });
});

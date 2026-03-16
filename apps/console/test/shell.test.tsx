import React from "react";
import { render, screen } from "@testing-library/react";

import HomePage from "@/app/page";

describe("console shell", () => {
  it("renders the home shell copy", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", { name: "Operator console shell" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/typed api boundary/i)).toBeInTheDocument();
  });
});

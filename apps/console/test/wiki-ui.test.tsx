import React from "react";
import { render, screen } from "@testing-library/react";

import type { WikiDocument, WikiSearchResult } from "@atlas/shared-types";

import { WikiDocumentList } from "@/components/wiki/wiki-document-list";
import { WikiDocumentView } from "@/components/wiki/wiki-document-view";

const baseDocument: WikiDocument = {
  pageId: "wiki_001",
  slug: "travel-lockout-recovery",
  title: "Travel Lockout Recovery SOP",
  category: "access",
  summary:
    "Operators must verify account state, consult travel context, and avoid broad MFA bypasses.",
  body: "Travel Lockout Recovery SOP. Operators must verify account state, consult travel context, and avoid broad MFA bypasses.",
  updatedAt: "2026-01-05T09:00:00Z",
};

const searchResult: WikiSearchResult = {
  document: baseDocument,
  score: 25,
  matchedTerms: ["travel", "mfa"],
};

describe("wiki UI", () => {
  it("renders the seeded wiki document list", () => {
    render(<WikiDocumentList documents={[baseDocument]} />);

    expect(
      screen.getByRole("link", { name: /travel lockout recovery sop/i }),
    ).toHaveAttribute("href", "/internal/wiki/travel-lockout-recovery");
    expect(screen.getByText(/avoid broad MFA bypasses/i)).toBeInTheDocument();
  });

  it("renders wiki search results and document detail", () => {
    render(
      <>
        <WikiDocumentList query="travel mfa" results={[searchResult]} />
        <WikiDocumentView document={baseDocument} />
      </>,
    );

    expect(screen.getByText(/search results for/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Travel Lockout Recovery SOP" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("access")[0]).toBeInTheDocument();
  });
});

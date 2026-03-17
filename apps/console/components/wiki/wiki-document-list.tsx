import Link from "next/link";
import React, { type CSSProperties } from "react";

import type { WikiDocument, WikiSearchResult } from "@atlas/shared-types";

type WikiDocumentListProps = {
  documents?: WikiDocument[];
  query?: string;
  results?: WikiSearchResult[];
};

export function WikiDocumentList({
  documents = [],
  query,
  results = [],
}: WikiDocumentListProps) {
  const items = results.length
    ? results.map((result) => ({
        document: result.document,
        subtitle: `Matched ${result.matchedTerms.join(", ")}`,
      }))
    : documents.map((document) => ({
        document,
        subtitle: document.summary,
      }));

  return (
    <div style={styles.stack}>
      {query ? (
        <p style={styles.meta}>
          Search results for <strong>{query}</strong>
        </p>
      ) : null}
      {items.length ? (
        items.map(({ document, subtitle }) => (
          <Link
            href={`/internal/wiki/${document.slug}`}
            key={document.slug}
            style={styles.card}
            data-testid={`wiki-link-${document.slug}`}
          >
            <strong>{document.title}</strong>
            <span style={styles.category}>{document.category}</span>
            <span style={styles.subtitle}>{subtitle}</span>
          </Link>
        ))
      ) : (
        <p style={styles.empty}>No wiki documents matched this query.</p>
      )}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  stack: { display: "grid", gap: "12px" },
  meta: { margin: 0, color: "var(--muted)" },
  card: {
    display: "grid",
    gap: "6px",
    padding: "14px",
    borderRadius: "14px",
    background: "#fffaf1",
    border: "1px solid rgba(217, 210, 194, 0.7)",
  },
  category: {
    fontSize: "0.82rem",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: "var(--accent)",
  },
  subtitle: { color: "var(--muted)", lineHeight: 1.4 },
  empty: { margin: 0, color: "var(--muted)" },
};

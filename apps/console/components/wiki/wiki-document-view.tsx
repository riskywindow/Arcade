import Link from "next/link";
import React, { type CSSProperties } from "react";

import type { WikiDocument } from "@atlas/shared-types";

import { SectionCard } from "@/components/section-card";

type WikiDocumentViewProps = {
  document: WikiDocument;
};

export function WikiDocumentView({ document }: WikiDocumentViewProps) {
  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <p style={styles.kicker}>Internal Wiki</p>
          <h1 style={styles.title}>{document.title}</h1>
          <p style={styles.summary}>{document.summary}</p>
        </div>
      </div>

      <div style={styles.links}>
        <Link href="/internal/wiki">Back to Wiki</Link>
        <Link href="/internal/helpdesk">Helpdesk Queue</Link>
        <Link href="/internal/directory">Directory</Link>
      </div>

      <SectionCard
        title="Document Body"
        description="The seeded wiki corpus is intentionally small, deterministic, and tuned for helpdesk and policy lookup workflows."
      >
        <div style={styles.metaRow}>
          <strong>Category</strong>
          <span>{document.category}</span>
        </div>
        <div style={styles.metaRow}>
          <strong>Slug</strong>
          <span>{document.slug}</span>
        </div>
        <article style={styles.body}>{document.body}</article>
      </SectionCard>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: { display: "grid", gap: "20px" },
  header: { display: "grid", gap: "8px" },
  kicker: {
    margin: 0,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: "var(--accent)",
    fontSize: "0.82rem",
  },
  title: { margin: 0, fontSize: "2rem" },
  summary: { margin: 0, color: "var(--muted)", lineHeight: 1.5, maxWidth: "70ch" },
  links: { display: "flex", gap: "14px", flexWrap: "wrap", color: "var(--accent)" },
  metaRow: {
    display: "grid",
    gridTemplateColumns: "120px 1fr",
    gap: "12px",
    padding: "8px 0",
  },
  body: {
    marginTop: "18px",
    padding: "16px",
    borderRadius: "14px",
    background: "#fffaf1",
    border: "1px solid rgba(217, 210, 194, 0.7)",
    lineHeight: 1.6,
  },
};

import Link from "next/link";
import React, { type CSSProperties } from "react";

import type { InboxThread } from "@atlas/shared-types";

import { SectionCard } from "@/components/section-card";

type InboxThreadViewProps = {
  thread: InboxThread;
};

export function InboxThreadView({ thread }: InboxThreadViewProps) {
  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <p style={styles.kicker}>Internal Inbox</p>
          <h1 style={styles.title}>{thread.subject}</h1>
          <p style={styles.summary}>
            {thread.participantEmails.join(", ")}
          </p>
        </div>
      </div>

      <div style={styles.links}>
        <Link href="/internal/inbox">Back to Inbox</Link>
        <Link href="/internal/helpdesk">Helpdesk Queue</Link>
        <Link href="/internal/wiki">Wiki</Link>
      </div>

      <SectionCard
        title="Thread Messages"
        description="This inbox is seeded, local, and read-only in Phase 3. Hidden scenario-only communications stay out of this surface."
      >
        <div style={styles.stack}>
          {thread.messages.map((message) => (
            <article key={message.messageId} style={styles.message}>
              <div style={styles.messageHeader}>
                <strong>{message.sender}</strong>
                <span>{message.channel}</span>
              </div>
              <p style={styles.subject}>{message.subject}</p>
              <p style={styles.body}>{message.body}</p>
            </article>
          ))}
        </div>
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
  summary: { margin: 0, color: "var(--muted)", lineHeight: 1.5 },
  links: { display: "flex", gap: "14px", flexWrap: "wrap", color: "var(--accent)" },
  stack: { display: "grid", gap: "12px" },
  message: {
    display: "grid",
    gap: "8px",
    padding: "14px",
    borderRadius: "14px",
    background: "#fffaf1",
    border: "1px solid rgba(217, 210, 194, 0.7)",
  },
  messageHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
    color: "var(--muted)",
  },
  subject: { margin: 0, fontWeight: 600 },
  body: { margin: 0, lineHeight: 1.5 },
};

import Link from "next/link";
import React, { type CSSProperties } from "react";

import type { InboxThread } from "@atlas/shared-types";

type InboxThreadListProps = {
  threads: InboxThread[];
};

export function InboxThreadList({ threads }: InboxThreadListProps) {
  return (
    <div style={styles.stack}>
      {threads.map((thread) => (
        <Link
          href={`/internal/inbox/${thread.threadId}`}
          key={thread.threadId}
          style={styles.card}
          data-testid={`thread-link-${thread.threadId}`}
        >
          <strong>{thread.subject}</strong>
          <span style={styles.meta}>{thread.participantEmails.join(", ")}</span>
          <span style={styles.meta}>
            {thread.messageCount} messages
          </span>
        </Link>
      ))}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  stack: { display: "grid", gap: "12px" },
  card: {
    display: "grid",
    gap: "6px",
    padding: "14px",
    borderRadius: "14px",
    background: "#fffaf1",
    border: "1px solid rgba(217, 210, 194, 0.7)",
  },
  meta: { color: "var(--muted)", lineHeight: 1.4 },
};

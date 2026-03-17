import Link from "next/link";
import React, { type CSSProperties } from "react";

import type { HelpdeskTicket } from "@atlas/shared-types";

import { StatusBadge } from "@/components/helpdesk/status-badge";

type TicketQueueTableProps = {
  tickets: HelpdeskTicket[];
};

export function TicketQueueTable({ tickets }: TicketQueueTableProps) {
  return (
    <div style={styles.shell}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.header}>Ticket</th>
            <th style={styles.header}>Status</th>
            <th style={styles.header}>Assignee</th>
            <th style={styles.header}>Tags</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr key={ticket.ticketId} style={styles.row}>
              <td style={styles.cell}>
                <Link
                  href={`/internal/helpdesk/tickets/${ticket.ticketId}`}
                  style={styles.ticketLink}
                  data-testid={`ticket-link-${ticket.ticketId}`}
                >
                  <strong>{ticket.title}</strong>
                  <span style={styles.summary}>{ticket.summary}</span>
                </Link>
              </td>
              <td style={styles.cell}>
                <StatusBadge priority={ticket.priority} status={ticket.status} />
              </td>
              <td style={styles.cell}>{ticket.assignedTo ?? "Unassigned"}</td>
              <td style={styles.cell}>{ticket.tags.join(", ") || "None"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  shell: {
    overflowX: "auto",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  header: {
    textAlign: "left",
    fontSize: "0.82rem",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: "var(--muted)",
    borderBottom: "1px solid var(--border)",
    padding: "0 0 12px",
  },
  row: {
    borderBottom: "1px solid rgba(217, 210, 194, 0.5)",
  },
  cell: {
    padding: "16px 0",
    verticalAlign: "top",
  },
  ticketLink: {
    display: "grid",
    gap: "6px",
  },
  summary: {
    color: "var(--muted)",
    lineHeight: 1.45,
  },
};

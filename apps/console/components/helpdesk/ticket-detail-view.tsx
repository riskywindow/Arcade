import Link from "next/link";
import React, { type CSSProperties } from "react";

import type { HelpdeskTicketDetail } from "@atlas/shared-types";

import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/helpdesk/status-badge";
import { TicketActions } from "@/components/helpdesk/ticket-actions";

type TicketDetailViewProps = {
  detail: HelpdeskTicketDetail;
};

export function TicketDetailView({ detail }: TicketDetailViewProps) {
  const { ticket, requester, relatedEmployee, relatedDevice } = detail;

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <p style={styles.kicker}>Internal Helpdesk</p>
          <h1 style={styles.title}>{ticket.title}</h1>
          <p style={styles.summary}>{ticket.summary}</p>
        </div>
        <StatusBadge priority={ticket.priority} status={ticket.status} />
      </div>

      <div style={styles.links}>
        <Link href="/internal/helpdesk">Back to Queue</Link>
        <a href="#requester">Requester</a>
        {relatedEmployee ? <a href="#related-employee">Related Employee</a> : null}
        {relatedDevice ? <a href="#related-device">Related Device</a> : null}
      </div>

      <div style={styles.grid}>
        <SectionCard
          description="Assignment, status, and note actions are intentionally narrow and map directly to the seeded helpdesk backend."
          title="Ticket Actions"
        >
          <TicketActions
            currentAssignee={ticket.assignedTo}
            currentStatus={ticket.status}
            ticketId={ticket.ticketId}
          />
        </SectionCard>

        <SectionCard
          description="Requester and related context stay visible on the same page to keep common helpdesk flows fast."
          title="Context"
        >
          <div id="requester" style={styles.contextBlock}>
            <strong>Requester</strong>
            <Link href={`/internal/directory/employees/${requester.employeeId}`}>
              {requester.displayName}
            </Link>
            <a href={`mailto:${requester.email}`}>{requester.email}</a>
            <span>{requester.title}</span>
          </div>

          {relatedEmployee ? (
            <div id="related-employee" style={styles.contextBlock}>
              <strong>Related Employee</strong>
              <Link href={`/internal/directory/employees/${relatedEmployee.employeeId}`}>
                {relatedEmployee.displayName}
              </Link>
              <a href={`mailto:${relatedEmployee.email}`}>{relatedEmployee.email}</a>
              <span>{relatedEmployee.title}</span>
            </div>
          ) : null}

          {relatedDevice ? (
            <div id="related-device" style={styles.contextBlock}>
              <strong>Related Device</strong>
              <span>{relatedDevice.hostname}</span>
              <span>{relatedDevice.platform}</span>
              <span>{relatedDevice.healthState}</span>
            </div>
          ) : null}
        </SectionCard>
      </div>

      <SectionCard
        description="Notes and tags provide the operator-visible history for this seeded ticket."
        title="Notes And Metadata"
      >
        <div style={styles.metaRow}>
          <strong>Assigned team</strong>
          <span>{ticket.assignedTeam}</span>
        </div>
        <div style={styles.metaRow}>
          <strong>Assigned to</strong>
          <span>{ticket.assignedTo ?? "Unassigned"}</span>
        </div>
        <div style={styles.metaRow}>
          <strong>Tags</strong>
          <span>{ticket.tags.join(", ") || "None"}</span>
        </div>
        <div style={styles.notes}>
          {ticket.notes.length ? (
            ticket.notes.map((note) => (
              <article key={note.noteId} style={styles.note}>
                <div style={styles.noteHeader}>
                  <strong>{note.author}</strong>
                  <span>{note.kind}</span>
                </div>
                <p style={styles.noteBody}>{note.body}</p>
              </article>
            ))
          ) : (
            <p style={styles.empty}>No notes yet.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    display: "grid",
    gap: "20px",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: "16px",
    alignItems: "start",
    flexWrap: "wrap",
  },
  kicker: {
    margin: "0 0 8px",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: "var(--accent)",
    fontSize: "0.82rem",
  },
  title: {
    margin: 0,
    fontSize: "2rem",
  },
  summary: {
    margin: "10px 0 0",
    maxWidth: "70ch",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  links: {
    display: "flex",
    gap: "14px",
    flexWrap: "wrap",
    color: "var(--accent)",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "minmax(300px, 1fr) minmax(280px, 0.8fr)",
    gap: "20px",
  },
  contextBlock: {
    display: "grid",
    gap: "4px",
    marginBottom: "16px",
  },
  metaRow: {
    display: "grid",
    gridTemplateColumns: "150px 1fr",
    gap: "12px",
    padding: "8px 0",
  },
  notes: {
    display: "grid",
    gap: "12px",
    marginTop: "18px",
  },
  note: {
    padding: "14px",
    borderRadius: "14px",
    background: "#fffaf1",
    border: "1px solid rgba(217, 210, 194, 0.7)",
  },
  noteHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
    marginBottom: "8px",
    color: "var(--muted)",
  },
  noteBody: {
    margin: 0,
    lineHeight: 1.5,
  },
  empty: {
    margin: 0,
    color: "var(--muted)",
  },
};

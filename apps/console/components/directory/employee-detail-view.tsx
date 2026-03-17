import Link from "next/link";
import React, { type CSSProperties } from "react";

import type { DirectoryEmployeeDetail } from "@atlas/shared-types";

import { SectionCard } from "@/components/section-card";

type EmployeeDetailViewProps = {
  detail: DirectoryEmployeeDetail;
};

export function EmployeeDetailView({ detail }: EmployeeDetailViewProps) {
  const { employee, manager, devices, accountAccess, relatedTickets, suspiciousEvents } = detail;

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <p style={styles.kicker}>Internal Directory</p>
          <h1 style={styles.title}>{employee.displayName}</h1>
          <p style={styles.summary}>
            {employee.title} in {employee.departmentSlug} based in {employee.location}.
          </p>
        </div>
      </div>

      <div style={styles.links}>
        <Link href="/internal/directory">Back to Directory</Link>
        <Link href="/internal/helpdesk">Helpdesk Queue</Link>
      </div>

      <div style={styles.grid}>
        <SectionCard
          title="Identity Context"
          description="Account and manager context for helpdesk and incident triage work."
        >
          <div style={styles.metaRow}><strong>Email</strong><span>{employee.email}</span></div>
          <div style={styles.metaRow}><strong>Employment</strong><span>{employee.employmentStatus}</span></div>
          <div style={styles.metaRow}><strong>Manager</strong><span>{manager ? manager.displayName : "None"}</span></div>
          <div style={styles.metaRow}><strong>Account Locked</strong><span>{accountAccess.accountLocked ? "Yes" : "No"}</span></div>
          <div style={styles.metaRow}><strong>MFA</strong><span>{accountAccess.mfaEnrolled ? "Enrolled" : "Not enrolled"}</span></div>
          <div style={styles.metaRow}><strong>Groups</strong><span>{accountAccess.groups.join(", ")}</span></div>
        </SectionCard>

        <SectionCard
          title="Devices"
          description="Seeded device posture and assignment context."
        >
          <div style={styles.stack}>
            {devices.map((device) => (
              <article key={device.deviceId} style={styles.itemCard}>
                <strong>{device.hostname}</strong>
                <span>{device.platform}</span>
                <span>{device.healthState}</span>
                <span>Serial {device.serialNumber}</span>
              </article>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Related Tickets"
        description="Ticket history tied to this employee in the seeded environment."
      >
        <div style={styles.stack}>
          {relatedTickets.map((ticket) => (
            <Link
              href={`/internal/helpdesk/tickets/${ticket.ticketId}`}
              key={ticket.ticketId}
              style={styles.itemCard}
            >
              <strong>{ticket.title}</strong>
              <span>{ticket.status}</span>
              <span>{ticket.summary}</span>
            </Link>
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="Signals"
        description="Suspicious or triage-relevant signals associated with this employee."
      >
        <div style={styles.stack}>
          {suspiciousEvents.length ? (
            suspiciousEvents.map((event) => (
              <article key={event.eventId} style={styles.itemCard}>
                <strong>{event.signalType}</strong>
                <span>{event.severity}</span>
                <span>{event.summary}</span>
              </article>
            ))
          ) : (
            <p style={styles.empty}>No active seeded signals.</p>
          )}
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
  grid: {
    display: "grid",
    gridTemplateColumns: "minmax(300px, 1fr) minmax(280px, 0.9fr)",
    gap: "20px",
  },
  metaRow: {
    display: "grid",
    gridTemplateColumns: "150px 1fr",
    gap: "12px",
    padding: "8px 0",
  },
  stack: { display: "grid", gap: "12px" },
  itemCard: {
    display: "grid",
    gap: "6px",
    padding: "14px",
    borderRadius: "14px",
    background: "#fffaf1",
    border: "1px solid rgba(217, 210, 194, 0.7)",
  },
  empty: { margin: 0, color: "var(--muted)" },
};

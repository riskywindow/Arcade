import React, { type CSSProperties } from "react";

import { requestRunStopAction, resolveApprovalAction } from "@/app/runs/actions";
import { ApprovalQueuePanel } from "@/components/runs/approval-queue-panel";
import {
  RunDashboard,
  RunDashboardError,
} from "@/components/runs/run-dashboard";
import { RunInterruptPanel } from "@/components/runs/run-interrupt-panel";
import { SectionCard } from "@/components/section-card";
import {
  getInterruptibleRuns,
  getPendingApprovalQueue,
  getRuns,
} from "@/lib/api/runs";

export default async function RunsPage() {
  let runsError: string | null = null;
  let queueError: string | null = null;
  let interruptError: string | null = null;
  let runs = [] as Awaited<ReturnType<typeof getRuns>>;
  let pendingApprovals = [] as Awaited<ReturnType<typeof getPendingApprovalQueue>>;
  let interruptibleRuns = [] as Awaited<ReturnType<typeof getInterruptibleRuns>>;

  try {
    runs = await getRuns();
  } catch (error) {
    runsError = error instanceof Error ? error.message : "unknown error";
  }

  try {
    pendingApprovals = await getPendingApprovalQueue();
  } catch (error) {
    queueError = error instanceof Error ? error.message : "unknown error";
  }

  try {
    interruptibleRuns = await getInterruptibleRuns();
  } catch (error) {
    interruptError = error instanceof Error ? error.message : "unknown error";
  }

  return (
    <div style={styles.page}>
      <SectionCard
        eyebrow="Runs"
        title="Operator dashboard"
        description="Browse live and historical runs, filter to the seeded demo path, and open a run detail page for replay inspection."
      >
        {runsError ? <RunDashboardError message={runsError} /> : <RunDashboard runs={runs} />}
      </SectionCard>
      <div style={styles.grid}>
        <SectionCard
          eyebrow="Operator Controls"
          title="Pending approvals"
          description="Approval-gated actions stay visible here so paused runs can be triaged without leaving the dashboard."
        >
          {queueError ? (
            <p style={styles.error}>
              Could not load pending approvals: {queueError}
            </p>
          ) : (
            <ApprovalQueuePanel
              items={pendingApprovals}
              resolveAction={resolveApprovalAction}
            />
          )}
        </SectionCard>
        <SectionCard
          eyebrow="Operator Controls"
          title="Interrupt active runs"
          description="Use the kill switch for a running, ready, or paused run when the local demo flow needs intervention."
        >
          {interruptError ? (
            <p style={styles.error}>
              Could not load interruptible runs: {interruptError}
            </p>
          ) : (
            <RunInterruptPanel
              runs={interruptibleRuns}
              requestStopAction={requestRunStopAction}
            />
          )}
        </SectionCard>
      </div>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    display: "grid",
    gap: "20px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
    gap: "20px",
  },
  error: {
    margin: 0,
    color: "#8a4b3a",
    lineHeight: 1.6,
  },
};

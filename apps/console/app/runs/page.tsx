import React, { type CSSProperties } from "react";

import { requestRunStopAction, resolveApprovalAction } from "@/app/runs/actions";
import { ApprovalQueuePanel } from "@/components/runs/approval-queue-panel";
import { RunInterruptPanel } from "@/components/runs/run-interrupt-panel";
import { SectionCard } from "@/components/section-card";
import { getInterruptibleRuns, getPendingApprovalQueue } from "@/lib/api/runs";

export default async function RunsPage() {
  let queueError: string | null = null;
  let interruptError: string | null = null;
  let pendingApprovals = [] as Awaited<ReturnType<typeof getPendingApprovalQueue>>;
  let interruptibleRuns = [] as Awaited<ReturnType<typeof getInterruptibleRuns>>;

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
        eyebrow="Operator Controls"
        title="Interrupt active runs"
        description="Request a local kill switch for a running or paused run. Running runs stop at the next safe worker checkpoint."
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
      <SectionCard
        eyebrow="Operator Controls"
        title="Pending approvals"
        description="Inspect local approval-gated actions and decide whether the paused run should resume or terminate."
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
        eyebrow="Runs"
        title="Replay entrypoint remains narrow"
        description="This page only exposes the approval and interruption controls needed for the V1 demo. Rich replay and filtering stay deferred."
      >
        <ul style={styles.list}>
          <li>Approval cards are populated from explicit API records.</li>
          <li>Decision buttons append replay-visible approval events.</li>
          <li>Stop requests append replay-visible kill-switch events.</li>
          <li>Run state changes remain derived from stored events.</li>
        </ul>
      </SectionCard>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    display: "grid",
    gap: "20px",
  },
  list: {
    margin: 0,
    paddingLeft: "20px",
    lineHeight: 1.7,
  },
  error: {
    margin: 0,
    color: "#8a4b3a",
    lineHeight: 1.6,
  },
};

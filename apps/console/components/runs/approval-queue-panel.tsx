import React, { type CSSProperties } from "react";

import type { ApprovalRequestRef, Run } from "@atlas/shared-types";

type ApprovalQueuePanelProps = {
  items: Array<{
    run: Run;
    approval: ApprovalRequestRef;
  }>;
  resolveAction: (formData: FormData) => Promise<void>;
};

export function ApprovalQueuePanel({
  items,
  resolveAction,
}: ApprovalQueuePanelProps) {
  if (items.length === 0) {
    return (
      <div style={styles.emptyState}>
        <strong>No pending approvals.</strong>
        <p style={styles.emptyCopy}>
          Approval-gated actions will appear here when a run enters
          <code style={styles.inlineCode}> waiting_approval </code>.
        </p>
      </div>
    );
  }

  return (
    <div style={styles.list}>
      {items.map(({ run, approval }) => (
        <article key={approval.approvalRequestId} style={styles.card}>
          <div style={styles.header}>
            <div>
              <p style={styles.kicker}>Pending Approval</p>
              <h3 style={styles.title}>{approval.requestedActionType}</h3>
            </div>
            <span style={styles.statusPill}>{run.status}</span>
          </div>

          <dl style={styles.metaGrid}>
            <div>
              <dt style={styles.term}>Run</dt>
              <dd style={styles.value}>{run.runId}</dd>
            </div>
            <div>
              <dt style={styles.term}>Task</dt>
              <dd style={styles.value}>{run.task.taskTitle}</dd>
            </div>
            <div>
              <dt style={styles.term}>Tool</dt>
              <dd style={styles.value}>{approval.toolName ?? "unknown_tool"}</dd>
            </div>
            <div>
              <dt style={styles.term}>Reason</dt>
              <dd style={styles.value}>{approval.reasonCode ?? "approval_required"}</dd>
            </div>
            <div>
              <dt style={styles.term}>Target</dt>
              <dd style={styles.value}>
                {approval.targetResourceType ?? "resource"}
                {approval.targetResourceId ? `:${approval.targetResourceId}` : ""}
              </dd>
            </div>
            <div>
              <dt style={styles.term}>Requested By</dt>
              <dd style={styles.value}>{approval.requesterRole}</dd>
            </div>
          </dl>

          <p style={styles.summary}>
            {approval.summary ?? "This action requires operator approval before execution."}
          </p>

          <pre style={styles.argumentsBlock}>
            {JSON.stringify(approval.requestedArguments, null, 2)}
          </pre>

          <form action={resolveAction} style={styles.form}>
            <input type="hidden" name="runId" value={run.runId} />
            <input
              type="hidden"
              name="approvalRequestId"
              value={approval.approvalRequestId}
            />
            <label style={styles.field}>
              <span style={styles.label}>Operator ID</span>
              <input
                defaultValue="local-operator"
                name="operatorId"
                style={styles.input}
                type="text"
              />
            </label>
            <label style={styles.field}>
              <span style={styles.label}>Decision Notes</span>
              <textarea
                name="resolutionSummary"
                rows={3}
                style={styles.textarea}
                placeholder="Optional local operator note."
              />
            </label>
            <div style={styles.actions}>
              <button name="decision" value="approve" style={styles.approveButton}>
                Approve
              </button>
              <button name="decision" value="deny" style={styles.denyButton}>
                Deny
              </button>
            </div>
          </form>
        </article>
      ))}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  list: {
    display: "grid",
    gap: "18px",
  },
  card: {
    border: "1px solid var(--border)",
    borderRadius: "16px",
    padding: "18px",
    background: "#fffaf0",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
    alignItems: "flex-start",
  },
  kicker: {
    margin: "0 0 6px",
    color: "var(--accent)",
    fontSize: "0.76rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  title: {
    margin: 0,
    fontSize: "1.2rem",
  },
  statusPill: {
    display: "inline-flex",
    padding: "6px 10px",
    borderRadius: "999px",
    border: "1px solid #d0b879",
    background: "#f8edc8",
    fontSize: "0.85rem",
    textTransform: "lowercase",
  },
  metaGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "12px",
    margin: "16px 0",
  },
  term: {
    fontSize: "0.78rem",
    color: "var(--muted)",
    marginBottom: "4px",
  },
  value: {
    margin: 0,
    fontSize: "0.96rem",
  },
  summary: {
    margin: "0 0 12px",
    lineHeight: 1.5,
    color: "var(--muted)",
  },
  argumentsBlock: {
    margin: "0 0 14px",
    padding: "12px",
    borderRadius: "12px",
    background: "#f4efe1",
    border: "1px solid #e3dbc6",
    overflowX: "auto",
    fontSize: "0.84rem",
  },
  form: {
    display: "grid",
    gap: "12px",
  },
  field: {
    display: "grid",
    gap: "6px",
  },
  label: {
    fontSize: "0.84rem",
    color: "var(--muted)",
  },
  input: {
    padding: "10px 12px",
    borderRadius: "10px",
    border: "1px solid var(--border)",
    background: "var(--panel)",
    fontFamily: "inherit",
    fontSize: "0.95rem",
  },
  textarea: {
    padding: "10px 12px",
    borderRadius: "10px",
    border: "1px solid var(--border)",
    background: "var(--panel)",
    fontFamily: "inherit",
    fontSize: "0.95rem",
    resize: "vertical",
  },
  actions: {
    display: "flex",
    gap: "10px",
  },
  approveButton: {
    padding: "10px 16px",
    borderRadius: "999px",
    border: "1px solid #1f5f4a",
    background: "#1f5f4a",
    color: "#fff",
    fontFamily: "inherit",
    cursor: "pointer",
  },
  denyButton: {
    padding: "10px 16px",
    borderRadius: "999px",
    border: "1px solid #8a4b3a",
    background: "#fff2ef",
    color: "#8a4b3a",
    fontFamily: "inherit",
    cursor: "pointer",
  },
  emptyState: {
    padding: "10px 4px 0",
  },
  emptyCopy: {
    margin: "8px 0 0",
    color: "var(--muted)",
    lineHeight: 1.6,
  },
  inlineCode: {
    fontFamily: "monospace",
  },
};

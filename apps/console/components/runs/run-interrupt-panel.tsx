import React, { type CSSProperties } from "react";

import type { Run } from "@atlas/shared-types";

type RunInterruptPanelProps = {
  runs: Run[];
  requestStopAction: (formData: FormData) => Promise<void>;
};

export function RunInterruptPanel({
  runs,
  requestStopAction,
}: RunInterruptPanelProps) {
  if (runs.length === 0) {
    return (
      <div style={styles.emptyState}>
        <strong>No interruptible runs.</strong>
        <p style={styles.emptyCopy}>
          Active runs in <code style={styles.inlineCode}>running</code>,
          <code style={styles.inlineCode}> waiting_approval</code>, or
          <code style={styles.inlineCode}> ready</code> will appear here.
        </p>
      </div>
    );
  }

  return (
    <div style={styles.list}>
      {runs.map((run) => (
        <article key={run.runId} style={styles.card}>
          <div style={styles.header}>
            <div>
              <p style={styles.kicker}>Kill Switch</p>
              <h3 style={styles.title}>{run.task.taskTitle}</h3>
            </div>
            <span style={styles.statusPill}>{run.status}</span>
          </div>

          <dl style={styles.metaGrid}>
            <div>
              <dt style={styles.term}>Run</dt>
              <dd style={styles.value}>{run.runId}</dd>
            </div>
            <div>
              <dt style={styles.term}>Scenario</dt>
              <dd style={styles.value}>{run.scenario.scenarioName}</dd>
            </div>
            <div>
              <dt style={styles.term}>Agent</dt>
              <dd style={styles.value}>{run.activeAgentId ?? "unassigned"}</dd>
            </div>
            <div>
              <dt style={styles.term}>State</dt>
              <dd style={styles.value}>{run.status}</dd>
            </div>
          </dl>

          <form action={requestStopAction} style={styles.form}>
            <input type="hidden" name="runId" value={run.runId} />
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
              <span style={styles.label}>Stop Reason</span>
              <textarea
                name="reason"
                rows={3}
                style={styles.textarea}
                placeholder="Optional note explaining why the run was interrupted."
              />
            </label>
            <div style={styles.actions}>
              <button style={styles.stopButton} type="submit">
                Stop run
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
    border: "1px solid #d7c3bb",
    borderRadius: "16px",
    padding: "18px",
    background: "#fff4f0",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
    alignItems: "flex-start",
  },
  kicker: {
    margin: "0 0 6px",
    color: "#8a4b3a",
    fontSize: "0.76rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  title: {
    margin: 0,
    fontSize: "1.1rem",
  },
  statusPill: {
    display: "inline-flex",
    padding: "6px 10px",
    borderRadius: "999px",
    border: "1px solid #cf9f90",
    background: "#ffe2d9",
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
  },
  stopButton: {
    padding: "10px 16px",
    borderRadius: "999px",
    border: "1px solid #8a4b3a",
    background: "#8a4b3a",
    color: "#fff",
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

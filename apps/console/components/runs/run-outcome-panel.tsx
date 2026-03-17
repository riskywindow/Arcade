"use client";

import React, { type CSSProperties } from "react";

import type {
  ReplayObjectiveStatus,
  RunReplay,
} from "@atlas/shared-types";

type RunOutcomePanelProps = {
  replay: RunReplay;
};

export function RunOutcomePanel({ replay }: RunOutcomePanelProps) {
  const explanation = replay.outcomeExplanation;

  if (!explanation) {
    return (
      <div style={styles.emptyState} data-testid="run-outcome-empty">
        <strong>No outcome explanation is available yet.</strong>
        <p style={styles.emptyCopy}>
          Deterministic state checks and task objective summaries will appear here
          when replay metadata includes them.
        </p>
      </div>
    );
  }

  return (
    <div style={styles.layout} data-testid="run-outcome-panel">
      <div style={styles.header}>
        <div>
          <p style={styles.kicker}>Outcome</p>
          <h3 style={styles.title}>Objective and state summary</h3>
          <p style={styles.description}>{explanation.summary}</p>
        </div>
        <span style={statusBadge(explanation.objectiveStatus)}>
          {labelize(explanation.objectiveStatus)}
        </span>
      </div>

      <dl style={styles.metaGrid}>
        <div>
          <dt style={styles.term}>Task objective</dt>
          <dd style={styles.value}>
            {explanation.objective ?? "No task objective summary was attached."}
          </dd>
        </div>
        <div>
          <dt style={styles.term}>Final run status</dt>
          <dd style={styles.value}>{replay.outcome.finalStatus}</dd>
        </div>
        <div>
          <dt style={styles.term}>Grade outcome</dt>
          <dd style={styles.value}>
            {replay.outcome.gradeResult?.outcome ?? "not graded"}
          </dd>
        </div>
      </dl>

      {explanation.highlights.length > 0 ? (
        <OutcomeList
          title="What changed"
          items={explanation.highlights}
          tone="highlight"
        />
      ) : null}

      {explanation.blockers.length > 0 ? (
        <OutcomeList
          title="What remains blocked"
          items={explanation.blockers}
          tone="blocker"
        />
      ) : null}

      <div style={styles.checkSection}>
        <h4 style={styles.sectionTitle}>Deterministic state checks</h4>
        {explanation.stateChecks.length === 0 ? (
          <p style={styles.emptyCopy}>
            No normalized state checks were attached to this run.
          </p>
        ) : (
          <div style={styles.checkList}>
            {explanation.stateChecks.map((check) => (
              <article key={check.checkKey} style={styles.checkCard}>
                <div style={styles.checkHeader}>
                  <strong style={styles.checkTitle}>{check.label}</strong>
                  <span style={statusBadge(check.status)}>{labelize(check.status)}</span>
                </div>
                <p style={styles.checkDetail}>{check.detail}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function OutcomeList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "highlight" | "blocker";
}) {
  return (
    <div style={styles.listSection}>
      <h4 style={styles.sectionTitle}>{title}</h4>
      <ul style={styles.list}>
        {items.map((item) => (
          <li key={item} style={tone === "blocker" ? styles.blockerItem : styles.highlightItem}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function statusBadge(status: ReplayObjectiveStatus): CSSProperties {
  if (status === "met") {
    return {
      ...styles.baseBadge,
      borderColor: "#a8d3ab",
      background: "#ebf7ec",
      color: "#27532f",
    };
  }
  if (status === "not_met") {
    return {
      ...styles.baseBadge,
      borderColor: "#d9a0a0",
      background: "#fff0ef",
      color: "#7b2922",
    };
  }
  return {
    ...styles.baseBadge,
    borderColor: "#d0b879",
    background: "#f8edc8",
    color: "#6e5100",
  };
}

function labelize(value: string): string {
  return value.replaceAll("_", " ");
}

const styles: Record<string, CSSProperties> = {
  layout: {
    display: "grid",
    gap: "16px",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: "16px",
    alignItems: "flex-start",
  },
  kicker: {
    margin: "0 0 6px",
    color: "var(--accent)",
    fontSize: "0.74rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  title: {
    margin: 0,
    fontSize: "1.05rem",
  },
  description: {
    margin: "10px 0 0",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  baseBadge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "5px 10px",
    borderRadius: "999px",
    border: "1px solid transparent",
    fontSize: "0.78rem",
    textTransform: "lowercase",
    whiteSpace: "nowrap",
  },
  metaGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "12px",
    margin: 0,
  },
  term: {
    marginBottom: "4px",
    color: "var(--muted)",
    fontSize: "0.78rem",
  },
  value: {
    margin: 0,
    lineHeight: 1.5,
  },
  listSection: {
    display: "grid",
    gap: "8px",
  },
  sectionTitle: {
    margin: 0,
    fontSize: "0.95rem",
  },
  list: {
    margin: 0,
    paddingLeft: "18px",
    display: "grid",
    gap: "8px",
  },
  highlightItem: {
    lineHeight: 1.5,
  },
  blockerItem: {
    lineHeight: 1.5,
    color: "#7b2922",
  },
  checkSection: {
    display: "grid",
    gap: "10px",
  },
  checkList: {
    display: "grid",
    gap: "10px",
  },
  checkCard: {
    border: "1px solid #eadfca",
    borderRadius: "14px",
    padding: "12px",
    background: "#fffaf0",
  },
  checkHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
    alignItems: "flex-start",
  },
  checkTitle: {
    lineHeight: 1.4,
  },
  checkDetail: {
    margin: "10px 0 0",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  emptyState: {
    display: "grid",
    gap: "8px",
  },
  emptyCopy: {
    margin: 0,
    color: "var(--muted)",
    lineHeight: 1.5,
  },
};

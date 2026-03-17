import React, { type CSSProperties } from "react";

import type {
  ReplayApproval,
  ReplayArtifactRef,
  ReplayAuditRecord,
  ReplayPolicyDecision,
  ReplayTimelineEntry,
  ReplayToolAction,
  RunReplay,
} from "@atlas/shared-types";

import { formatTimestamp } from "@/lib/runs";

type RunDetailTimelineProps = {
  replay: RunReplay;
};

export function RunDetailTimeline({ replay }: RunDetailTimelineProps) {
  const toolActionsById = new Map<string, ReplayToolAction>(
    replay.toolActions.map((item) => [item.toolActionId, item]),
  );
  const approvalsById = new Map<string, ReplayApproval>(
    replay.approvals.map((item) => [item.approvalRequestId, item]),
  );
  const auditsById = new Map<string, ReplayAuditRecord>(
    replay.auditRecords.map((item) => [item.auditId, item]),
  );
  const artifactsById = new Map<string, ReplayArtifactRef>(
    replay.artifacts.map((item) => [item.artifactId, item]),
  );
  const policyByToolActionId = new Map<string, ReplayPolicyDecision>();
  for (const decision of replay.policyDecisions) {
    if (decision.toolActionId) {
      policyByToolActionId.set(decision.toolActionId, decision);
    }
  }

  return (
    <ol style={styles.timeline} data-testid="run-detail-timeline">
      {replay.timelineEntries.map((entry) => (
        <li key={entry.entryId} style={styles.timelineItem}>
          <div style={styles.rail}>
            <span style={dotStyle(entry.status)} />
            <span style={styles.line} />
          </div>
          <article style={styles.card}>
            <div style={styles.header}>
              <div>
                <div style={styles.badgeRow}>
                  <span style={kindBadge(entry.kind)}>{labelize(entry.kind)}</span>
                  <span style={statusBadge(entry.status)}>{labelize(entry.status)}</span>
                </div>
                <h3 style={styles.title}>{entry.title}</h3>
              </div>
              <div style={styles.meta}>
                <span>#{entry.sequence}</span>
                <span>{formatTimestamp(entry.occurredAt)}</span>
              </div>
            </div>

            <p style={styles.summary}>{entry.summary}</p>

            <dl style={styles.metaGrid}>
              {entry.eventType ? (
                <div>
                  <dt style={styles.term}>Event</dt>
                  <dd style={styles.value}>{entry.eventType}</dd>
                </div>
              ) : null}
              {entry.stepId ? (
                <div>
                  <dt style={styles.term}>Step</dt>
                  <dd style={styles.value}>{entry.stepId}</dd>
                </div>
              ) : null}
              {entry.artifactId ? (
                <div>
                  <dt style={styles.term}>Artifact</dt>
                  <dd style={styles.value}>{entry.artifactId}</dd>
                </div>
              ) : null}
              {entry.approvalRequestId ? (
                <div>
                  <dt style={styles.term}>Approval</dt>
                  <dd style={styles.value}>{entry.approvalRequestId}</dd>
                </div>
              ) : null}
            </dl>

            {entry.toolActionId ? (
              <ToolActionDetail
                toolAction={toolActionsById.get(entry.toolActionId) ?? null}
                policyDecision={policyByToolActionId.get(entry.toolActionId) ?? null}
                artifacts={entry.relatedArtifactIds
                  .map((artifactId) => artifactsById.get(artifactId) ?? null)
                  .filter((artifact): artifact is ReplayArtifactRef => artifact !== null)}
              />
            ) : null}

            {entry.approvalRequestId ? (
              <ApprovalDetail
                approval={approvalsById.get(entry.approvalRequestId) ?? null}
              />
            ) : null}

            {entry.auditId ? (
              <AuditDetail audit={auditsById.get(entry.auditId) ?? null} />
            ) : null}

            {entry.artifactId ? (
              <ArtifactDetail artifact={artifactsById.get(entry.artifactId) ?? null} />
            ) : null}
          </article>
        </li>
      ))}
    </ol>
  );
}

function ToolActionDetail({
  toolAction,
  policyDecision,
  artifacts,
}: {
  toolAction: ReplayToolAction | null;
  policyDecision: ReplayPolicyDecision | null;
  artifacts: ReplayArtifactRef[];
}) {
  if (!toolAction) {
    return null;
  }

  return (
    <div style={styles.detailBlock}>
      <p style={styles.detailLabel}>Tool action</p>
      <dl style={styles.metaGrid}>
        <div>
          <dt style={styles.term}>Tool</dt>
          <dd style={styles.value}>
            {toolAction.toolCall.toolName}.{toolAction.toolCall.action}
          </dd>
        </div>
        <div>
          <dt style={styles.term}>Outcome</dt>
          <dd style={styles.value}>{toolAction.toolCall.status}</dd>
        </div>
        {policyDecision ? (
          <div>
            <dt style={styles.term}>Policy</dt>
            <dd style={styles.value}>{policyDecision.decision.outcome}</dd>
          </div>
        ) : null}
      </dl>
      {toolAction.toolCall.errorMessage ? (
        <p style={styles.callout}>{toolAction.toolCall.errorMessage}</p>
      ) : null}
      {artifacts.length > 0 ? (
        <div style={styles.relatedList}>
          {artifacts.map((artifact) => (
            <span key={artifact.artifactId} style={styles.relatedPill}>
              {artifact.kind}: {artifact.artifactId}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ApprovalDetail({ approval }: { approval: ReplayApproval | null }) {
  if (!approval) {
    return null;
  }

  return (
    <div style={styles.detailBlock}>
      <p style={styles.detailLabel}>Approval flow</p>
      <dl style={styles.metaGrid}>
        <div>
          <dt style={styles.term}>Status</dt>
          <dd style={styles.value}>{approval.request.status}</dd>
        </div>
        <div>
          <dt style={styles.term}>Requested action</dt>
          <dd style={styles.value}>{approval.request.requestedActionType}</dd>
        </div>
        {approval.operatorId ? (
          <div>
            <dt style={styles.term}>Operator</dt>
            <dd style={styles.value}>{approval.operatorId}</dd>
          </div>
        ) : null}
      </dl>
      {approval.request.summary ? (
        <p style={styles.callout}>{approval.request.summary}</p>
      ) : null}
    </div>
  );
}

function AuditDetail({ audit }: { audit: ReplayAuditRecord | null }) {
  if (!audit) {
    return null;
  }

  return (
    <div style={styles.detailBlock}>
      <p style={styles.detailLabel}>Audit evidence</p>
      <dl style={styles.metaGrid}>
        <div>
          <dt style={styles.term}>Kind</dt>
          <dd style={styles.value}>{audit.eventKind}</dd>
        </div>
        <div>
          <dt style={styles.term}>Actor</dt>
          <dd style={styles.value}>{audit.actorType}</dd>
        </div>
        {audit.requestId ? (
          <div>
            <dt style={styles.term}>Request</dt>
            <dd style={styles.value}>{audit.requestId}</dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}

function ArtifactDetail({ artifact }: { artifact: ReplayArtifactRef | null }) {
  if (!artifact) {
    return null;
  }

  return (
    <div style={styles.detailBlock}>
      <p style={styles.detailLabel}>Artifact</p>
      <dl style={styles.metaGrid}>
        <div>
          <dt style={styles.term}>Kind</dt>
          <dd style={styles.value}>{artifact.kind}</dd>
        </div>
        <div>
          <dt style={styles.term}>URI</dt>
          <dd style={styles.value}>
            <code style={styles.inlineCode}>{artifact.uri}</code>
          </dd>
        </div>
      </dl>
      {artifact.displayName || artifact.description ? (
        <p style={styles.callout}>
          {artifact.displayName ?? artifact.description}
        </p>
      ) : null}
    </div>
  );
}

function labelize(value: string): string {
  return value.replaceAll("_", " ");
}

function dotStyle(status: ReplayTimelineEntry["status"]): CSSProperties {
  if (status === "success") {
    return { ...styles.dot, background: "#1f5f4a" };
  }
  if (status === "failed") {
    return { ...styles.dot, background: "#8a4b3a" };
  }
  if (status === "blocked") {
    return { ...styles.dot, background: "#915b1f" };
  }
  if (status === "waiting") {
    return { ...styles.dot, background: "#b48d27" };
  }
  if (status === "warning") {
    return { ...styles.dot, background: "#7f6f62" };
  }
  return { ...styles.dot, background: "#305a79" };
}

function kindBadge(kind: ReplayTimelineEntry["kind"]): CSSProperties {
  return {
    ...styles.badge,
    background: "#f4efe1",
    borderColor: "#ddd2b8",
    color: "#5d4d1d",
  };
}

function statusBadge(status: ReplayTimelineEntry["status"]): CSSProperties {
  if (status === "success") {
    return { ...styles.badge, background: "#e7f5ee", borderColor: "#9bc5ad", color: "#1f5f4a" };
  }
  if (status === "failed") {
    return { ...styles.badge, background: "#fff0ec", borderColor: "#d6a698", color: "#8a4b3a" };
  }
  if (status === "blocked") {
    return { ...styles.badge, background: "#fbefe3", borderColor: "#d6b087", color: "#915b1f" };
  }
  if (status === "waiting") {
    return { ...styles.badge, background: "#fbf1d9", borderColor: "#d4be83", color: "#7a6118" };
  }
  if (status === "warning") {
    return { ...styles.badge, background: "#f0efef", borderColor: "#c7c3c3", color: "#5e5b5b" };
  }
  return { ...styles.badge, background: "#eef5fb", borderColor: "#a7bfd7", color: "#305a79" };
}

const styles: Record<string, CSSProperties> = {
  timeline: {
    listStyle: "none",
    margin: 0,
    padding: 0,
    display: "grid",
    gap: "14px",
  },
  timelineItem: {
    display: "grid",
    gridTemplateColumns: "24px 1fr",
    gap: "14px",
  },
  rail: {
    display: "grid",
    justifyItems: "center",
    gridTemplateRows: "18px 1fr",
  },
  dot: {
    width: "12px",
    height: "12px",
    borderRadius: "999px",
    marginTop: "4px",
  },
  line: {
    width: "2px",
    background: "#ddd5c4",
    minHeight: "100%",
  },
  card: {
    padding: "16px 18px",
    borderRadius: "16px",
    border: "1px solid var(--border)",
    background: "#fffdf8",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
    alignItems: "flex-start",
  },
  badgeRow: {
    display: "flex",
    gap: "8px",
    marginBottom: "8px",
    flexWrap: "wrap",
  },
  badge: {
    display: "inline-flex",
    padding: "4px 9px",
    borderRadius: "999px",
    border: "1px solid var(--border)",
    fontSize: "0.78rem",
    textTransform: "lowercase",
  },
  title: {
    margin: 0,
    fontSize: "1.06rem",
  },
  meta: {
    display: "grid",
    gap: "4px",
    color: "var(--muted)",
    fontSize: "0.82rem",
    textAlign: "right",
    whiteSpace: "nowrap",
  },
  summary: {
    margin: "10px 0 0",
    lineHeight: 1.55,
  },
  metaGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
    gap: "10px",
    margin: "14px 0 0",
  },
  term: {
    fontSize: "0.76rem",
    color: "var(--muted)",
    marginBottom: "4px",
  },
  value: {
    margin: 0,
    lineHeight: 1.45,
  },
  detailBlock: {
    marginTop: "14px",
    paddingTop: "14px",
    borderTop: "1px solid #ece6d8",
  },
  detailLabel: {
    margin: "0 0 8px",
    color: "var(--accent)",
    fontSize: "0.8rem",
    letterSpacing: "0.05em",
    textTransform: "uppercase",
  },
  callout: {
    margin: "10px 0 0",
    padding: "10px 12px",
    borderRadius: "12px",
    background: "#f7f3e8",
    border: "1px solid #e2d8c3",
    lineHeight: 1.5,
  },
  relatedList: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap",
    marginTop: "10px",
  },
  relatedPill: {
    display: "inline-flex",
    padding: "4px 9px",
    borderRadius: "999px",
    background: "#f4efe1",
    border: "1px solid #ddd2b8",
    fontSize: "0.8rem",
  },
  inlineCode: {
    fontFamily: "monospace",
    fontSize: "0.84rem",
    wordBreak: "break-all",
  },
};

import React, { type CSSProperties } from "react";

import type {
  JsonValue,
  ReplayApproval,
  ReplayAuditRecord,
  ReplayPolicyDecision,
  ReplayToolAction,
  RunReplay,
} from "@atlas/shared-types";

import { formatTimestamp } from "@/lib/runs";

type RunSecurityPanelsProps = {
  replay: RunReplay;
};

export function RunSecurityPanels({ replay }: RunSecurityPanelsProps) {
  const toolActionsById = new Map<string, ReplayToolAction>(
    replay.toolActions.map((item) => [item.toolActionId, item]),
  );

  return (
    <div style={styles.container} data-testid="run-security-panels">
      <section style={styles.panel}>
        <div style={styles.panelHeader}>
          <div>
            <p style={styles.kicker}>Bastion Policy</p>
            <h3 style={styles.title}>Policy decisions</h3>
          </div>
          <span style={styles.countPill}>{replay.policyDecisions.length}</span>
        </div>
        <p style={styles.description}>
          Each decision explains whether Bastion allowed the action, blocked it,
          or paused it for operator approval.
        </p>
        {replay.policyDecisions.length === 0 ? (
          <EmptyState copy="No Bastion policy decisions were recorded for this run." />
        ) : (
          <div style={styles.list}>
            {replay.policyDecisions.map((decision) => {
              const toolAction = decision.toolActionId
                ? toolActionsById.get(decision.toolActionId) ?? null
                : null;
              const reasonCode = stringFromMetadata(
                decision.decision.metadata,
                "reason_code",
              );

              return (
                <article key={decision.policyDecisionId} style={styles.item}>
                  <div style={styles.itemHeader}>
                    <div style={styles.badges}>
                      <span style={outcomeBadge(decision.decision.outcome)}>
                        {decision.decision.outcome.replaceAll("_", " ")}
                      </span>
                      {reasonCode ? (
                        <span style={styles.reasonBadge}>{reasonCode}</span>
                      ) : null}
                    </div>
                    <span style={styles.timestamp}>
                      {formatTimestamp(decision.occurredAt)}
                    </span>
                  </div>
                  <h4 style={styles.itemTitle}>{decision.decision.actionType}</h4>
                  <dl style={styles.metaGrid}>
                    <div>
                      <dt style={styles.term}>Affected action</dt>
                      <dd style={styles.value}>
                        {toolAction
                          ? `${toolAction.toolCall.toolName}.${toolAction.toolCall.action}`
                          : decision.decision.actionType}
                      </dd>
                    </div>
                    <div>
                      <dt style={styles.term}>Decision type</dt>
                      <dd style={styles.value}>{decision.decision.outcome}</dd>
                    </div>
                    <div>
                      <dt style={styles.term}>Reason code</dt>
                      <dd style={styles.value}>{reasonCode ?? "not recorded"}</dd>
                    </div>
                  </dl>
                  <p style={styles.callout}>{decision.decision.rationale}</p>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section style={styles.panel}>
        <div style={styles.panelHeader}>
          <div>
            <p style={styles.kicker}>Operator Approval</p>
            <h3 style={styles.title}>Approval events</h3>
          </div>
          <span style={styles.countPill}>{replay.approvals.length}</span>
        </div>
        <p style={styles.description}>
          Approval-required actions stay visible here until they are approved,
          denied, or expire.
        </p>
        {replay.approvals.length === 0 ? (
          <EmptyState copy="No approval-gated actions were recorded for this run." />
        ) : (
          <div style={styles.list}>
            {replay.approvals.map((approval) => (
              <article key={approval.approvalRequestId} style={styles.item}>
                <div style={styles.itemHeader}>
                  <div style={styles.badges}>
                    <span style={approvalStatusBadge(approval.request.status)}>
                      {approval.request.status}
                    </span>
                    {approval.request.reasonCode ? (
                      <span style={styles.reasonBadge}>
                        {approval.request.reasonCode}
                      </span>
                    ) : null}
                  </div>
                  <span style={styles.timestamp}>
                    {formatTimestamp(approval.requestedAt)}
                  </span>
                </div>
                <h4 style={styles.itemTitle}>
                  {approval.request.toolName
                    ? `${approval.request.toolName}.${approval.request.requestedActionType}`
                    : approval.request.requestedActionType}
                </h4>
                <dl style={styles.metaGrid}>
                  <div>
                    <dt style={styles.term}>Requested action</dt>
                    <dd style={styles.value}>{approval.request.requestedActionType}</dd>
                  </div>
                  <div>
                    <dt style={styles.term}>Decision</dt>
                    <dd style={styles.value}>{approval.request.status}</dd>
                  </div>
                  <div>
                    <dt style={styles.term}>Operator</dt>
                    <dd style={styles.value}>{approval.operatorId ?? "pending"}</dd>
                  </div>
                  <div>
                    <dt style={styles.term}>Resolved</dt>
                    <dd style={styles.value}>
                      {formatTimestamp(approval.decidedAt ?? approval.request.resolvedAt)}
                    </dd>
                  </div>
                </dl>
                <p style={styles.callout}>
                  {approval.request.summary ??
                    "This action required an operator decision before Bastion would continue."}
                </p>
                {approval.request.resolutionSummary ? (
                  <p style={styles.secondaryCallout}>
                    Resolution: {approval.request.resolutionSummary}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>

      <section style={styles.panel}>
        <div style={styles.panelHeader}>
          <div>
            <p style={styles.kicker}>Audit Trail</p>
            <h3 style={styles.title}>Audit highlights</h3>
          </div>
          <span style={styles.countPill}>{replay.auditRecords.length}</span>
        </div>
        <p style={styles.description}>
          Structured audit records confirm what Bastion observed and who
          initiated or resolved the sensitive moments in the run.
        </p>
        {replay.auditRecords.length === 0 ? (
          <EmptyState copy="No structured audit records were attached to this run." />
        ) : (
          <div style={styles.list}>
            {replay.auditRecords.map((audit) => (
              <article key={audit.auditId} style={styles.item}>
                <div style={styles.itemHeader}>
                  <div style={styles.badges}>
                    <span style={auditKindBadge(audit.eventKind)}>
                      {audit.eventKind.replaceAll("_", " ")}
                    </span>
                    <span style={styles.actorBadge}>{audit.actorType}</span>
                  </div>
                  <span style={styles.timestamp}>
                    {formatTimestamp(audit.occurredAt)}
                  </span>
                </div>
                <h4 style={styles.itemTitle}>{auditTitle(audit)}</h4>
                <dl style={styles.metaGrid}>
                  <div>
                    <dt style={styles.term}>Audit kind</dt>
                    <dd style={styles.value}>{audit.eventKind}</dd>
                  </div>
                  <div>
                    <dt style={styles.term}>Actor</dt>
                    <dd style={styles.value}>{audit.actorType}</dd>
                  </div>
                  <div>
                    <dt style={styles.term}>Request</dt>
                    <dd style={styles.value}>{audit.requestId ?? "not linked"}</dd>
                  </div>
                </dl>
                {auditSummary(audit) ? (
                  <p style={styles.callout}>{auditSummary(audit)}</p>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function EmptyState({ copy }: { copy: string }) {
  return <p style={styles.emptyState}>{copy}</p>;
}

function stringFromMetadata(
  metadata: Record<string, JsonValue>,
  key: string,
): string | null {
  const value = metadata[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function auditTitle(audit: ReplayAuditRecord): string {
  if (audit.eventKind === "kill_switch_triggered") {
    return "Operator interrupted the run";
  }
  if (audit.eventKind === "approval_requested") {
    return "Approval request entered the audit trail";
  }
  if (audit.eventKind === "approval_resolved") {
    return "Operator resolved an approval request";
  }
  return `Audit event: ${audit.eventKind.replaceAll("_", " ")}`;
}

function auditSummary(audit: ReplayAuditRecord): string | null {
  if (audit.eventKind === "kill_switch_triggered") {
    const reason = stringFromMetadata(audit.payload, "reason");
    return reason
      ? `Bastion recorded a run interruption with reason: ${reason}.`
      : "Bastion recorded that an operator interrupted this run.";
  }
  if (audit.eventKind === "approval_requested") {
    return "Bastion recorded the approval gate before the sensitive action was allowed to continue.";
  }
  if (audit.eventKind === "approval_resolved") {
    const resolution = stringFromMetadata(audit.payload, "resolution");
    return resolution
      ? `The approval request was resolved with outcome: ${resolution}.`
      : "The approval request reached a terminal operator decision.";
  }
  return null;
}

function outcomeBadge(outcome: "allow" | "deny" | "require_approval"): CSSProperties {
  if (outcome === "allow") {
    return {
      ...styles.baseBadge,
      borderColor: "#a8d3ab",
      background: "#ebf7ec",
      color: "#27532f",
    };
  }

  if (outcome === "deny") {
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

function approvalStatusBadge(status: ReplayApproval["request"]["status"]): CSSProperties {
  if (status === "approved") {
    return outcomeBadge("allow");
  }
  if (status === "rejected" || status === "cancelled" || status === "expired") {
    return outcomeBadge("deny");
  }
  return outcomeBadge("require_approval");
}

function auditKindBadge(kind: string): CSSProperties {
  if (kind === "kill_switch_triggered") {
    return outcomeBadge("deny");
  }
  if (kind === "approval_requested" || kind === "approval_resolved") {
    return outcomeBadge("require_approval");
  }
  return outcomeBadge("allow");
}

const styles: Record<string, CSSProperties> = {
  container: {
    display: "grid",
    gap: "16px",
  },
  panel: {
    border: "1px solid var(--border)",
    borderRadius: "16px",
    padding: "16px",
    background: "#fffdf9",
  },
  panelHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "12px",
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
  countPill: {
    display: "inline-flex",
    minWidth: "32px",
    justifyContent: "center",
    alignItems: "center",
    padding: "6px 10px",
    borderRadius: "999px",
    border: "1px solid var(--border)",
    background: "var(--panel)",
    fontSize: "0.84rem",
  },
  list: {
    display: "grid",
    gap: "12px",
    marginTop: "14px",
  },
  item: {
    border: "1px solid #eadfca",
    borderRadius: "14px",
    padding: "14px",
    background: "#fffaf0",
  },
  itemHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "12px",
  },
  badges: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
  },
  baseBadge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "4px 9px",
    borderRadius: "999px",
    border: "1px solid transparent",
    fontSize: "0.76rem",
    textTransform: "lowercase",
  },
  reasonBadge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "4px 9px",
    borderRadius: "999px",
    border: "1px solid #d5ccb8",
    background: "#f5f0e5",
    color: "#5b4d31",
    fontSize: "0.76rem",
  },
  actorBadge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "4px 9px",
    borderRadius: "999px",
    border: "1px solid #cfc4ae",
    background: "#f8f4ea",
    color: "#564b36",
    fontSize: "0.76rem",
    textTransform: "lowercase",
  },
  timestamp: {
    color: "var(--muted)",
    fontSize: "0.84rem",
    whiteSpace: "nowrap",
  },
  itemTitle: {
    margin: "10px 0 0",
    fontSize: "1rem",
  },
  metaGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
    gap: "12px",
    margin: "14px 0 0",
  },
  term: {
    marginBottom: "4px",
    color: "var(--muted)",
    fontSize: "0.78rem",
  },
  value: {
    margin: 0,
    lineHeight: 1.4,
  },
  callout: {
    margin: "12px 0 0",
    padding: "10px 12px",
    borderRadius: "12px",
    background: "#f5efe1",
    border: "1px solid #e3dbc6",
    lineHeight: 1.5,
  },
  secondaryCallout: {
    margin: "8px 0 0",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  emptyState: {
    margin: "14px 0 0",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
};

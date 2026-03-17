import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import type { ApprovalRequestRef, Run, RunReplay } from "@atlas/shared-types";

import { ApprovalQueuePanel } from "@/components/runs/approval-queue-panel";
import { RunArtifactViewer } from "@/components/runs/run-artifact-viewer";
import { RunDetailTimeline } from "@/components/runs/run-detail-timeline";
import {
  RunDashboard,
  RunDashboardError,
  RunDashboardLoading,
} from "@/components/runs/run-dashboard";
import { RunInterruptPanel } from "@/components/runs/run-interrupt-panel";
import { RunOutcomePanel } from "@/components/runs/run-outcome-panel";
import { RunSecurityPanels } from "@/components/runs/run-security-panels";

function makeRun(overrides: Partial<Run> = {}): Run {
  return {
    runId: "run_standard_001",
    environment: {
      environmentId: "env_helpdesk",
      environmentName: "Northstar Helpdesk",
      environmentVersion: "v1",
    },
    scenario: {
      scenarioId: "mfa-reenrollment-device-loss",
      environmentId: "env_helpdesk",
      scenarioName: "MFA Re-enrollment Device Loss",
      scenarioSeed: "seed-phase3-demo",
    },
    task: {
      taskId: "task_001",
      scenarioId: "mfa-reenrollment-device-loss",
      taskKind: "access_restoration",
      taskTitle: "Restore employee access after device loss",
    },
    status: "running",
    createdAt: "2026-03-17T12:00:00Z",
    updatedAt: "2026-03-17T12:05:00Z",
    startedAt: "2026-03-17T12:00:05Z",
    completedAt: null,
    currentStepIndex: 1,
    activeAgentId: "agent_phase6",
    gradeResult: null,
    ...overrides,
  };
}

function makeReplay(): RunReplay {
  const run = makeRun({
    runId: "phase5-policy-demo-001",
    scenario: {
      scenarioId: "travel-lockout-recovery",
      environmentId: "env_helpdesk",
      scenarioName: "Travel Lockout Recovery",
      scenarioSeed: "seed-phase3-demo",
    },
    task: {
      taskId: "task_demo",
      scenarioId: "travel-lockout-recovery",
      taskKind: "access_restoration",
      taskTitle: "Restore employee access after travel lockout",
    },
    status: "succeeded",
    completedAt: "2026-03-17T12:12:00Z",
    gradeResult: {
      outcome: "passed",
      score: 1,
      summary: "Scenario passed.",
      details: {},
      evidenceArtifactIds: ["artifact_001"],
      gradeId: "grade_001",
      rubricVersion: null,
    },
  });

  return {
    schemaVersion: 1,
    run,
    rawEventCount: 8,
    timelineEntries: [
      {
        entryId: "timeline-evt-created",
        eventId: "evt-created",
        sequence: 0,
        occurredAt: "2026-03-17T12:00:00Z",
        kind: "lifecycle",
        status: "info",
        title: "Run created",
        summary: "Created run for Restore employee access after travel lockout.",
        eventType: "run.created",
        stepId: null,
        toolActionId: null,
        approvalRequestId: null,
        auditId: null,
        artifactId: null,
        relatedArtifactIds: [],
      },
      {
        entryId: "timeline-evt-tool",
        eventId: "evt-tool",
        sequence: 4,
        occurredAt: "2026-03-17T12:03:00Z",
        kind: "tool_action",
        status: "blocked",
        title: "identity_api.limited_mfa_recovery",
        summary: "Approval required: Sensitive account recovery requires approval..",
        eventType: "tool_call.recorded",
        stepId: "step_001",
        toolActionId: "tool_001",
        approvalRequestId: null,
        auditId: null,
        artifactId: null,
        relatedArtifactIds: ["artifact_001"],
      },
      {
        entryId: "timeline-evt-approval",
        eventId: "evt-approval",
        sequence: 5,
        occurredAt: "2026-03-17T12:04:00Z",
        kind: "approval",
        status: "waiting",
        title: "Approval requested: identity.limited_mfa_recovery",
        summary: "Approve the limited recovery path.",
        eventType: "approval.requested",
        stepId: "step_001",
        toolActionId: null,
        approvalRequestId: "approval_001",
        auditId: null,
        artifactId: null,
        relatedArtifactIds: [],
      },
      {
        entryId: "timeline-evt-audit",
        eventId: "evt-audit",
        sequence: 6,
        occurredAt: "2026-03-17T12:04:30Z",
        kind: "audit",
        status: "info",
        title: "Audit: approval_requested",
        summary: "Audit record for request req_123.",
        eventType: "audit.recorded",
        stepId: "step_001",
        toolActionId: null,
        approvalRequestId: null,
        auditId: "audit_001",
        artifactId: null,
        relatedArtifactIds: [],
      },
      {
        entryId: "timeline-evt-artifact",
        eventId: "evt-artifact",
        sequence: 7,
        occurredAt: "2026-03-17T12:05:00Z",
        kind: "artifact",
        status: "info",
        title: "Artifact attached: screenshot",
        summary: "minio://atlas-artifacts/run_123/screenshot.png",
        eventType: "artifact.attached",
        stepId: "step_001",
        toolActionId: null,
        approvalRequestId: null,
        auditId: null,
        artifactId: "artifact_001",
        relatedArtifactIds: [],
      },
      {
        entryId: "timeline-evt-artifact-2",
        eventId: "evt-artifact-2",
        sequence: 7,
        occurredAt: "2026-03-17T12:05:20Z",
        kind: "artifact",
        status: "info",
        title: "Artifact attached: screenshot",
        summary: "minio://atlas-artifacts/run_123/screenshot-2.png",
        eventType: "artifact.attached",
        stepId: "step_002",
        toolActionId: null,
        approvalRequestId: null,
        auditId: null,
        artifactId: "artifact_002",
        relatedArtifactIds: [],
      },
      {
        entryId: "timeline-evt-outcome",
        eventId: "evt-outcome",
        sequence: 8,
        occurredAt: "2026-03-17T12:12:00Z",
        kind: "outcome",
        status: "success",
        title: "Run succeeded",
        summary: "Scenario passed.",
        eventType: "run.completed",
        stepId: null,
        toolActionId: null,
        approvalRequestId: null,
        auditId: null,
        artifactId: null,
        relatedArtifactIds: [],
      },
    ],
    artifacts: [
      {
        artifactId: "artifact_001",
        eventId: "evt-artifact",
        timelineEntryId: "timeline-evt-artifact",
        stepId: "step_001",
        createdAt: "2026-03-17T12:05:00Z",
        kind: "screenshot",
        uri: "minio://atlas-artifacts/run_123/screenshot.png",
        contentType: "image/png",
        displayName: "Account recovery screenshot",
        description: null,
        metadata: {
          pageTitle: "Helpdesk Queue",
          currentUrl: "http://127.0.0.1:3000/internal/helpdesk",
        },
      },
      {
        artifactId: "artifact_002",
        eventId: "evt-artifact-2",
        timelineEntryId: "timeline-evt-artifact-2",
        stepId: "step_002",
        createdAt: "2026-03-17T12:05:20Z",
        kind: "screenshot",
        uri: "minio://atlas-artifacts/run_123/screenshot-2.png",
        contentType: "image/png",
        displayName: "Resolved ticket screenshot",
        description: null,
        metadata: {
          pageTitle: "Resolved Ticket",
          currentUrl: "http://127.0.0.1:3000/internal/helpdesk/tickets/hd-1002",
        },
      },
    ],
    toolActions: [
      {
        toolActionId: "tool_001",
        eventId: "evt-tool",
        sequence: 4,
        occurredAt: "2026-03-17T12:03:00Z",
        stepId: "step_001",
        requestId: "req_123",
        toolCall: {
          toolCallId: "tool_001",
          toolName: "identity_api",
          action: "limited_mfa_recovery",
          arguments: { employee_id: "emp_123" },
          status: "blocked",
          result: null,
          errorMessage: "tool execution paused pending approval",
        },
        policyDecision: {
          decisionId: "policy_001",
          outcome: "require_approval",
          actionType: "identity.limited_mfa_recovery",
          rationale: "Sensitive account recovery requires approval.",
          approvalRequestId: "approval_001",
          metadata: {
            reason_code: "approval_required",
          },
        },
        artifactIds: ["artifact_001"],
      },
      {
        toolActionId: "tool_002",
        eventId: "evt-tool-deny",
        sequence: 3,
        occurredAt: "2026-03-17T12:02:00Z",
        stepId: "step_001",
        requestId: "req_122",
        toolCall: {
          toolCallId: "tool_002",
          toolName: "identity_api",
          action: "reset_password",
          arguments: { employee_id: "emp_123" },
          status: "blocked",
          result: null,
          errorMessage: "tool execution blocked by Bastion policy",
        },
        policyDecision: {
          decisionId: "policy_002",
          outcome: "deny",
          actionType: "identity.reset_password",
          rationale: "Direct password resets are blocked in the seeded demo path.",
          approvalRequestId: null,
          metadata: {
            reason_code: "forbidden_shortcut",
          },
        },
        artifactIds: [],
      },
    ],
    policyDecisions: [
      {
        policyDecisionId: "policy_002",
        eventId: "evt-tool-deny",
        sequence: 3,
        occurredAt: "2026-03-17T12:02:00Z",
        toolActionId: "tool_002",
        decision: {
          decisionId: "policy_002",
          outcome: "deny",
          actionType: "identity.reset_password",
          rationale: "Direct password resets are blocked in the seeded demo path.",
          approvalRequestId: null,
          metadata: {
            reason_code: "forbidden_shortcut",
          },
        },
      },
      {
        policyDecisionId: "policy_001",
        eventId: "evt-tool",
        sequence: 4,
        occurredAt: "2026-03-17T12:03:00Z",
        toolActionId: "tool_001",
        decision: {
          decisionId: "policy_001",
          outcome: "require_approval",
          actionType: "identity.limited_mfa_recovery",
          rationale: "Sensitive account recovery requires approval.",
          approvalRequestId: "approval_001",
          metadata: {
            reason_code: "approval_required",
          },
        },
      },
    ],
    approvals: [
      {
        approvalRequestId: "approval_001",
        request: {
          approvalRequestId: "approval_001",
          runId: "phase5-policy-demo-001",
          stepId: "step_001",
          status: "approved",
          requestedActionType: "identity.limited_mfa_recovery",
          toolName: "identity_api",
          requestedArguments: { employee_id: "emp_123" },
          requesterRole: "helpdesk_agent",
          reasonCode: "approval_required",
          summary: "Approve the limited recovery path.",
          targetResourceType: "employee",
          targetResourceId: "emp_123",
          requestedAt: "2026-03-17T12:04:00Z",
          expiresAt: null,
          resolvedAt: "2026-03-17T12:06:00Z",
          resolutionSummary: "Approved for the seeded demo path.",
          metadata: {},
        },
        requestedEventId: "evt-approval",
        waitingEventId: "evt-waiting",
        resolvedEventId: "evt-resolved",
        resumedEventId: "evt-resumed",
        requestedAt: "2026-03-17T12:04:00Z",
        waitingAt: "2026-03-17T12:04:05Z",
        decidedAt: "2026-03-17T12:06:00Z",
        resumedAt: "2026-03-17T12:06:03Z",
        operatorId: "operator_001",
      },
    ],
    auditRecords: [
      {
        auditId: "audit_001",
        eventId: "evt-audit",
        sequence: 6,
        occurredAt: "2026-03-17T12:04:30Z",
        stepId: "step_001",
        requestId: "req_123",
        eventKind: "approval_requested",
        actorType: "bastion",
        payload: {},
      },
      {
        auditId: "audit_002",
        eventId: "evt-audit-stop",
        sequence: 9,
        occurredAt: "2026-03-17T12:07:00Z",
        stepId: "step_002",
        requestId: "req_stop_001",
        eventKind: "kill_switch_triggered",
        actorType: "operator",
        payload: {
          reason: "Operator interruption smoke check",
        },
      },
    ],
    outcome: {
      eventId: "evt-outcome",
      sequence: 8,
      finalStatus: "succeeded",
      completedAt: "2026-03-17T12:12:00Z",
      gradeResult: run.gradeResult,
      summary: "Scenario passed.",
    },
    outcomeExplanation: {
      objective:
        "Restore access using the approved recovery path and leave a correct ticket record.",
      objectiveStatus: "met",
      summary: "The task objective was met and the deterministic state checks passed.",
      highlights: [
        "Bastion blocked identity.reset_password.",
        "Bastion paused identity.limited_mfa_recovery for operator approval.",
        "Operator approved identity.limited_mfa_recovery.",
      ],
      blockers: [],
      stateChecks: [
        {
          checkKey: "ticket_status",
          label: "Ticket status updated",
          status: "met",
          detail: "ticket status resolved in ('resolved',)",
        },
        {
          checkKey: "account_locked",
          label: "Account lock state",
          status: "met",
          detail: "account_locked == False",
        },
        {
          checkKey: "approval_actions",
          label: "Approval-gated action completed",
          status: "met",
          detail: "approval actions include ('identity.limited_mfa_recovery',)",
        },
      ],
    },
  };
}

describe("runs dashboard UI", () => {
  it("renders a loading state", () => {
    render(<RunDashboardLoading />);

    expect(screen.getByText(/loading runs/i)).toBeInTheDocument();
  });

  it("renders an error state", () => {
    render(<RunDashboardError message="API returned 500" />);

    expect(screen.getByText(/could not load runs/i)).toBeInTheDocument();
    expect(screen.getByText(/api returned 500/i)).toBeInTheDocument();
  });

  it("renders an empty state when no runs exist", () => {
    render(<RunDashboard runs={[]} />);

    expect(screen.getByText(/no runs recorded yet/i)).toBeInTheDocument();
  });

  it("renders curated demo cards with flagship and attention paths", () => {
    render(
      <RunDashboard
        runs={[
          makeRun({
            runId: "phase5-policy-demo-001",
            scenario: {
              scenarioId: "travel-lockout-recovery",
              environmentId: "env_helpdesk",
              scenarioName: "Travel Lockout Recovery",
              scenarioSeed: "seed-phase3-demo",
            },
            task: {
              taskId: "task_demo",
              scenarioId: "travel-lockout-recovery",
              taskKind: "access_restoration",
              taskTitle: "Restore employee access after travel lockout",
            },
            status: "waiting_approval",
          }),
          makeRun({
            runId: "phase5-policy-demo-approved-001",
            scenario: {
              scenarioId: "travel-lockout-recovery",
              environmentId: "env_helpdesk",
              scenarioName: "Travel Lockout Recovery",
              scenarioSeed: "seed-phase3-demo",
            },
            task: {
              taskId: "task_demo_success",
              scenarioId: "travel-lockout-recovery",
              taskKind: "access_restoration",
              taskTitle: "Restore employee access after travel lockout",
            },
            status: "succeeded",
          }),
          makeRun({
            runId: "benchmark-smoke-001",
            status: "failed",
            scenario: {
              scenarioId: "suspicious-login-triage",
              environmentId: "env_helpdesk",
              scenarioName: "Suspicious Login Triage",
              scenarioSeed: "seed-phase3-demo",
            },
            task: {
              taskId: "task_bench",
              scenarioId: "suspicious-login-triage",
              taskKind: "incident_triage",
              taskTitle: "Review suspicious login alert",
            },
          }),
        ]}
      />,
    );

    expect(
      screen.getByText("Flagship Replay", { selector: "p" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Operator Script", { selector: "p" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open flagship replay" }),
    ).toHaveAttribute("href", "/runs/phase5-policy-demo-001");
    expect(
      screen.getByRole("link", { name: "Open approval or attention run" }),
    ).toHaveAttribute("href", "/runs/phase5-policy-demo-approved-001");
    expect(screen.getByText("Flagship")).toBeInTheDocument();
    expect(screen.getByText("phase5-policy-demo-001")).toBeInTheDocument();
    expect(screen.getByText("benchmark-smoke-001")).toBeInTheDocument();
  });

  it("filters runs by status and run type", () => {
    render(
      <RunDashboard
        runs={[
          makeRun({
            runId: "phase5-policy-demo-001",
            scenario: {
              scenarioId: "travel-lockout-recovery",
              environmentId: "env_helpdesk",
              scenarioName: "Travel Lockout Recovery",
              scenarioSeed: "seed-phase3-demo",
            },
            task: {
              taskId: "task_demo",
              scenarioId: "travel-lockout-recovery",
              taskKind: "access_restoration",
              taskTitle: "Restore employee access after travel lockout",
            },
            status: "waiting_approval",
          }),
          makeRun({
            runId: "benchmark-smoke-001",
            status: "failed",
          }),
        ]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Filter by run type"), {
      target: { value: "benchmark" },
    });

    expect(screen.getByText("benchmark-smoke-001")).toBeInTheDocument();
    expect(screen.queryByText("phase5-policy-demo-001")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Filter by status"), {
      target: { value: "waiting_approval" },
    });

    expect(screen.getByText(/no runs match the current filters/i)).toBeInTheDocument();
  });
});

describe("runs approval UI", () => {
  it("renders pending approval context and decision controls", () => {
    const run = makeRun({
      runId: "run_approval_001",
      scenario: {
        scenarioId: "travel-lockout-recovery",
        environmentId: "env_helpdesk",
        scenarioName: "Travel Lockout Recovery",
        scenarioSeed: "seed-123",
      },
      task: {
        taskId: "task_123",
        scenarioId: "travel-lockout-recovery",
        taskKind: "access_restoration",
        taskTitle: "Restore employee access after travel lockout",
      },
      status: "waiting_approval",
      activeAgentId: "agent_phase5",
    });

    const approval: ApprovalRequestRef = {
      approvalRequestId: "approval_001",
      runId: run.runId,
      stepId: "run_approval_001-step-001",
      status: "pending",
      requestedActionType: "limited_mfa_recovery",
      toolName: "identity_api",
      requestedArguments: {
        action: "limited_mfa_recovery",
        employee_id: "emp_123",
      },
      requesterRole: "helpdesk_agent",
      reasonCode: "limited_mfa_recovery_requires_approval",
      summary: "Limited MFA recovery requires operator approval before execution.",
      targetResourceType: "employee",
      targetResourceId: "emp_123",
      requestedAt: "2026-03-17T12:01:00Z",
      expiresAt: null,
      resolvedAt: null,
      resolutionSummary: null,
      metadata: {},
    };

    render(
      <ApprovalQueuePanel
        items={[{ run, approval }]}
        resolveAction={vi.fn(async () => undefined)}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "limited_mfa_recovery" }),
    ).toBeInTheDocument();
    expect(screen.getByText("run_approval_001")).toBeInTheDocument();
    expect(
      screen.getByText("limited_mfa_recovery_requires_approval"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deny" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("local-operator")).toBeInTheDocument();
  });

  it("renders an empty state when no approvals are pending", () => {
    render(
      <ApprovalQueuePanel
        items={[]}
        resolveAction={vi.fn(async () => undefined)}
      />,
    );

    expect(screen.getByText(/no pending approvals/i)).toBeInTheDocument();
  });

  it("renders an interrupt control for active runs", () => {
    const run = makeRun({
      runId: "run_interrupt_001",
      scenario: {
        scenarioId: "travel-lockout-recovery",
        environmentId: "env_helpdesk",
        scenarioName: "Travel Lockout Recovery",
        scenarioSeed: "seed-123",
      },
      task: {
        taskId: "task_987",
        scenarioId: "travel-lockout-recovery",
        taskKind: "access_restoration",
        taskTitle: "Review suspicious MFA recovery attempt",
      },
      status: "running",
      currentStepIndex: 2,
      activeAgentId: "agent_phase5",
    });

    render(
      <RunInterruptPanel
        runs={[run]}
        requestStopAction={vi.fn(async () => undefined)}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Review suspicious MFA recovery attempt" }),
    ).toBeInTheDocument();
    expect(screen.getByText("run_interrupt_001")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop run" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("local-operator")).toBeInTheDocument();
  });
});

describe("run detail timeline UI", () => {
  it("renders grouped replay entries for the main event types", () => {
    render(<RunDetailTimeline replay={makeReplay()} />);

    expect(screen.getByRole("heading", { name: "Run created" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "identity_api.limited_mfa_recovery" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Approval requested: identity.limited_mfa_recovery",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Audit: approval_requested" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { name: "Artifact attached: screenshot" }),
    ).toHaveLength(2);
    expect(
      screen.getByRole("heading", { name: "Run succeeded" }),
    ).toBeInTheDocument();
  });

  it("renders detail blocks for tool, approval, audit, and artifact entries", () => {
    render(<RunDetailTimeline replay={makeReplay()} />);

    expect(screen.getByText(/tool execution paused pending approval/i)).toBeInTheDocument();
    expect(screen.getByText(/approval flow/i)).toBeInTheDocument();
    expect(screen.getByText(/audit evidence/i)).toBeInTheDocument();
    expect(screen.getByText(/account recovery screenshot/i)).toBeInTheDocument();
    expect(screen.getByText("artifact_001")).toBeInTheDocument();
  });
});

describe("artifact viewer UI", () => {
  it("renders an empty state when no artifacts are attached", () => {
    const replay = makeReplay();
    render(
      <RunArtifactViewer
        replay={{ ...replay, artifacts: [], timelineEntries: replay.timelineEntries.filter((entry) => entry.kind !== "artifact") }}
      />,
    );

    expect(screen.getByText(/no artifacts attached/i)).toBeInTheDocument();
  });

  it("renders artifact metadata and switches selected screenshots", () => {
    render(<RunArtifactViewer replay={makeReplay()} />);

    expect(screen.getByText(/selected artifact/i)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Account recovery screenshot" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/helpdesk queue/i).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /resolved ticket screenshot/i }));

    expect(
      screen.getByRole("heading", { name: "Resolved ticket screenshot" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/resolved ticket/i).length).toBeGreaterThan(0);
    expect(
      screen.getByText("http://127.0.0.1:3000/internal/helpdesk/tickets/hd-1002"),
    ).toBeInTheDocument();
  });
});

describe("security panels UI", () => {
  it("renders policy decisions, approval events, and audit highlights", () => {
    render(<RunSecurityPanels replay={makeReplay()} />);

    expect(
      screen.getByRole("heading", { name: "Policy decisions" }),
    ).toBeInTheDocument();
    expect(screen.getByText("identity.reset_password")).toBeInTheDocument();
    expect(screen.getAllByText("forbidden_shortcut").length).toBeGreaterThan(0);
    expect(screen.getByText("identity_api.limited_mfa_recovery")).toBeInTheDocument();
    expect(screen.getAllByText("approval_required").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", { name: "Approval events" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("approved").length).toBeGreaterThan(0);
    expect(screen.getByText("operator_001")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Audit highlights" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Operator interrupted the run" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/operator interruption smoke check/i),
    ).toBeInTheDocument();
  });

  it("renders empty states when the replay has no security evidence", () => {
    const replay = makeReplay();
    render(
      <RunSecurityPanels
        replay={{
          ...replay,
          policyDecisions: [],
          approvals: [],
          auditRecords: [],
        }}
      />,
    );

    expect(
      screen.getByText(/no bastion policy decisions were recorded/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no approval-gated actions were recorded/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no structured audit records were attached/i),
    ).toBeInTheDocument();
  });
});

describe("outcome panel UI", () => {
  it("renders the task objective, highlights, and deterministic state checks", () => {
    render(<RunOutcomePanel replay={makeReplay()} />);

    expect(
      screen.getByRole("heading", { name: "Objective and state summary" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Restore access using the approved recovery path and leave a correct ticket record.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/bastion blocked identity\.reset_password/i)).toBeInTheDocument();
    expect(screen.getByText("Ticket status updated")).toBeInTheDocument();
    expect(screen.getByText("account_locked == False")).toBeInTheDocument();
    expect(screen.getAllByText("met").length).toBeGreaterThan(0);
  });

  it("renders an empty state when no outcome explanation is attached", () => {
    const replay = makeReplay();
    render(
      <RunOutcomePanel
        replay={{
          ...replay,
          outcomeExplanation: null,
        }}
      />,
    );

    expect(
      screen.getByText(/no outcome explanation is available yet/i),
    ).toBeInTheDocument();
  });
});

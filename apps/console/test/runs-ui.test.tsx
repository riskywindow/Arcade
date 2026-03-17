import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import type { ApprovalRequestRef, Run } from "@atlas/shared-types";

import { ApprovalQueuePanel } from "@/components/runs/approval-queue-panel";
import {
  RunDashboard,
  RunDashboardError,
  RunDashboardLoading,
} from "@/components/runs/run-dashboard";
import { RunInterruptPanel } from "@/components/runs/run-interrupt-panel";

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

  it("renders a populated run list with flagship demo entry and detail links", () => {
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

    expect(screen.getByText(/recommended demo path/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open run detail" }),
    ).toHaveAttribute("href", "/runs/phase5-policy-demo-001");
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

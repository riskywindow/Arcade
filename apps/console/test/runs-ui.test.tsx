import React from "react";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import type { ApprovalRequestRef, Run } from "@atlas/shared-types";

import { ApprovalQueuePanel } from "@/components/runs/approval-queue-panel";
import { RunInterruptPanel } from "@/components/runs/run-interrupt-panel";

describe("runs approval UI", () => {
  it("renders pending approval context and decision controls", () => {
    const run: Run = {
      runId: "run_approval_001",
      environment: {
        environmentId: "env_helpdesk",
        environmentName: "Northstar Helpdesk",
        environmentVersion: "v1",
      },
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
      createdAt: "2026-03-17T12:00:00Z",
      updatedAt: "2026-03-17T12:05:00Z",
      startedAt: "2026-03-17T12:00:05Z",
      completedAt: null,
      currentStepIndex: 1,
      activeAgentId: "agent_phase5",
      gradeResult: null,
    };

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
    const run: Run = {
      runId: "run_interrupt_001",
      environment: {
        environmentId: "env_helpdesk",
        environmentName: "Northstar Helpdesk",
        environmentVersion: "v1",
      },
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
      createdAt: "2026-03-17T12:00:00Z",
      updatedAt: "2026-03-17T12:06:00Z",
      startedAt: "2026-03-17T12:00:05Z",
      completedAt: null,
      currentStepIndex: 2,
      activeAgentId: "agent_phase5",
      gradeResult: null,
    };

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

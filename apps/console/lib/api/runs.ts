import type {
  ApprovalDecisionRequest,
  ApprovalListResponse,
  ApprovalRequestRef,
  ApprovalResponse,
  Run,
  RunListResponse,
  StopRunRequest,
  StopRunResponse,
} from "@atlas/shared-types";

const apiBaseUrl =
  process.env.ATLAS_CONSOLE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type PendingApprovalQueueItem = {
  run: Run;
  approval: ApprovalRequestRef;
};

export type InterruptibleRun = Run;

export async function getRuns(
  fetchImpl: typeof fetch = fetch,
): Promise<Run[]> {
  const response = await fetchImpl(`${apiBaseUrl}/runs`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`failed to load runs: ${response.status}`);
  }

  const payload = (await response.json()) as RunListResponse;
  return payload.runs;
}

export async function getRunApprovals(
  runId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<ApprovalRequestRef[]> {
  const response = await fetchImpl(`${apiBaseUrl}/runs/${runId}/approvals`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`failed to load approvals for ${runId}: ${response.status}`);
  }

  const payload = (await response.json()) as ApprovalListResponse;
  return payload.approvals;
}

export async function getPendingApprovalQueue(
  fetchImpl: typeof fetch = fetch,
): Promise<PendingApprovalQueueItem[]> {
  const runs = await getRuns(fetchImpl);
  const waitingRuns = runs.filter((run) => run.status === "waiting_approval");
  const approvalsByRun = await Promise.all(
    waitingRuns.map(async (run) => ({
      run,
      approvals: await getRunApprovals(run.runId, fetchImpl),
    })),
  );

  return approvalsByRun.flatMap(({ run, approvals }) =>
    approvals
      .filter((approval) => approval.status === "pending")
      .map((approval) => ({ run, approval })),
  );
}

export async function getInterruptibleRuns(
  fetchImpl: typeof fetch = fetch,
): Promise<InterruptibleRun[]> {
  const runs = await getRuns(fetchImpl);
  return runs.filter(
    (run) =>
      run.status === "running" ||
      run.status === "waiting_approval" ||
      run.status === "ready",
  );
}

async function resolveApproval(
  {
    runId,
    approvalRequestId,
    decision,
    payload,
    fetchImpl = fetch,
  }: {
    runId: string;
    approvalRequestId: string;
    decision: "approve" | "deny";
    payload: ApprovalDecisionRequest;
    fetchImpl?: typeof fetch;
  },
): Promise<ApprovalRequestRef> {
  const response = await fetchImpl(
    `${apiBaseUrl}/runs/${runId}/approvals/${approvalRequestId}/${decision}`,
    {
      method: "POST",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  if (!response.ok) {
    throw new Error(`failed to ${decision} ${approvalRequestId}: ${response.status}`);
  }

  const resolved = (await response.json()) as ApprovalResponse;
  return resolved.approval;
}

export async function approveRunApproval(
  runId: string,
  approvalRequestId: string,
  payload: ApprovalDecisionRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<ApprovalRequestRef> {
  return resolveApproval({
    runId,
    approvalRequestId,
    decision: "approve",
    payload,
    fetchImpl,
  });
}

export async function denyRunApproval(
  runId: string,
  approvalRequestId: string,
  payload: ApprovalDecisionRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<ApprovalRequestRef> {
  return resolveApproval({
    runId,
    approvalRequestId,
    decision: "deny",
    payload,
    fetchImpl,
  });
}

export async function requestRunStop(
  runId: string,
  payload: StopRunRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<StopRunResponse> {
  const response = await fetchImpl(`${apiBaseUrl}/runs/${runId}/stop`, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`failed to stop ${runId}: ${response.status}`);
  }

  return (await response.json()) as StopRunResponse;
}

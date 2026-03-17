import type {
  ApprovalDecisionRequest,
  ApprovalListResponse,
  ApprovalRequestRef,
  ApprovalResponse,
  BenchmarkRunComparison,
  BenchmarkRunComparisonResponse,
  BenchmarkRunResult,
  BenchmarkRunResultResponse,
  Run,
  RunListResponse,
  RunReplay,
  RunReplayResponse,
  RunResponse,
  StopRunRequest,
  StopRunResponse,
} from "@atlas/shared-types";

import { apiBaseUrl } from "@/lib/api/base-url";

export type PendingApprovalQueueItem = {
  run: Run;
  approval: ApprovalRequestRef;
};

export type InterruptibleRun = Run;

export async function getRuns(fetchImpl: typeof fetch = fetch): Promise<Run[]> {
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

export async function getRun(
  runId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Run> {
  const response = await fetchImpl(`${apiBaseUrl}/runs/${runId}`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`failed to load run ${runId}: ${response.status}`);
  }

  const payload = (await response.json()) as RunResponse;
  return payload.run;
}

export async function getRunReplay(
  runId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<RunReplay> {
  const response = await fetchImpl(`${apiBaseUrl}/runs/${runId}/replay`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`failed to load replay for ${runId}: ${response.status}`);
  }

  const payload = (await response.json()) as RunReplayResponse;
  return payload.replay;
}

export async function getBenchmarkRunResult(
  catalogId: string,
  benchmarkRunId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<BenchmarkRunResult> {
  const response = await fetchImpl(
    `${apiBaseUrl}/benchmarks/catalogs/${catalogId}/runs/${benchmarkRunId}`,
    {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(
      `failed to load benchmark ${benchmarkRunId}: ${response.status}`,
    );
  }

  const payload = (await response.json()) as BenchmarkRunResultResponse;
  return payload.result;
}

export async function getBenchmarkRunComparison(
  catalogId: string,
  baselineBenchmarkRunId: string,
  candidateBenchmarkRunId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<BenchmarkRunComparison> {
  const params = new URLSearchParams({
    baseline_benchmark_run_id: baselineBenchmarkRunId,
    candidate_benchmark_run_id: candidateBenchmarkRunId,
  });
  const response = await fetchImpl(
    `${apiBaseUrl}/benchmarks/catalogs/${catalogId}/compare?${params.toString()}`,
    {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(
      `failed to compare benchmark ${candidateBenchmarkRunId} against ${baselineBenchmarkRunId}: ${response.status}`,
    );
  }

  const payload = (await response.json()) as BenchmarkRunComparisonResponse;
  return payload.comparison;
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
    throw new Error(
      `failed to load approvals for ${runId}: ${response.status}`,
    );
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

async function resolveApproval({
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
}): Promise<ApprovalRequestRef> {
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
    throw new Error(
      `failed to ${decision} ${approvalRequestId}: ${response.status}`,
    );
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

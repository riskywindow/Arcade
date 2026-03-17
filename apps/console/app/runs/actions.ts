"use server";

import { revalidatePath } from "next/cache";

import { approveRunApproval, denyRunApproval, requestRunStop } from "@/lib/api/runs";

function requiredString(formData: FormData, key: string): string {
  const value = formData.get(key);
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`${key} is required`);
  }
  return value.trim();
}

export async function resolveApprovalAction(formData: FormData): Promise<void> {
  const runId = requiredString(formData, "runId");
  const approvalRequestId = requiredString(formData, "approvalRequestId");
  const operatorId = requiredString(formData, "operatorId");
  const decision = requiredString(formData, "decision");
  const resolutionSummaryValue = formData.get("resolutionSummary");
  const resolutionSummary =
    typeof resolutionSummaryValue === "string" && resolutionSummaryValue.trim().length > 0
      ? resolutionSummaryValue.trim()
      : null;

  if (decision === "approve") {
    await approveRunApproval(runId, approvalRequestId, {
      operatorId,
      resolutionSummary,
    });
  } else if (decision === "deny") {
    await denyRunApproval(runId, approvalRequestId, {
      operatorId,
      resolutionSummary,
    });
  } else {
    throw new Error(`unsupported decision ${decision}`);
  }

  revalidatePath("/runs");
}

export async function requestRunStopAction(formData: FormData): Promise<void> {
  const runId = requiredString(formData, "runId");
  const operatorId = requiredString(formData, "operatorId");
  const reasonValue = formData.get("reason");
  const reason =
    typeof reasonValue === "string" && reasonValue.trim().length > 0
      ? reasonValue.trim()
      : null;

  await requestRunStop(runId, {
    operatorId,
    reason,
  });

  revalidatePath("/runs");
}

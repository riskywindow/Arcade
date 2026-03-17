import type { Run } from "@atlas/shared-types";

export type DerivedRunType = "seeded_demo" | "benchmark" | "standard";

export function deriveRunType(run: Run): DerivedRunType {
  const runId = run.runId.toLowerCase();
  const scenarioId = run.scenario.scenarioId.toLowerCase();

  if (
    runId.includes("demo") ||
    scenarioId === "travel-lockout-recovery"
  ) {
    return "seeded_demo";
  }

  if (
    runId.includes("benchmark") ||
    runId.includes("smoke") ||
    runId.includes("scripted")
  ) {
    return "benchmark";
  }

  return "standard";
}

export function isFlagshipDemoRun(run: Run): boolean {
  return run.runId === "phase5-policy-demo-001";
}

export function selectPrimaryDemoRun(runs: Run[]): Run | null {
  return (
    runs.find((run) => isFlagshipDemoRun(run)) ??
    runs.find(
      (run) => deriveRunType(run) === "seeded_demo" && run.status === "succeeded",
    ) ??
    runs.find((run) => deriveRunType(run) === "seeded_demo") ??
    runs[0] ??
    null
  );
}

export function selectAttentionDemoRun(
  runs: Run[],
  primaryRunId?: string | null,
): Run | null {
  return (
    runs.find(
      (run) =>
        run.runId !== primaryRunId &&
        deriveRunType(run) === "seeded_demo" &&
        run.status === "waiting_approval",
    ) ??
    runs.find(
      (run) =>
        run.runId !== primaryRunId &&
        deriveRunType(run) === "seeded_demo" &&
        (run.status === "failed" || run.status === "cancelled"),
    ) ??
    runs.find(
      (run) =>
        run.runId !== primaryRunId && deriveRunType(run) === "seeded_demo",
    ) ??
    runs.find(
      (run) =>
        run.runId !== primaryRunId && run.status === "waiting_approval",
    ) ??
    runs.find(
      (run) =>
        run.runId !== primaryRunId &&
        (run.status === "failed" || run.status === "cancelled"),
    ) ??
    null
  );
}

export function runTypeLabel(runType: DerivedRunType): string {
  if (runType === "seeded_demo") {
    return "Seeded demo";
  }
  if (runType === "benchmark") {
    return "Benchmark";
  }
  return "Standard";
}

export function runDateKey(run: Run): string {
  return run.createdAt.slice(0, 10);
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "Not recorded";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(date);
}

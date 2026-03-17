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

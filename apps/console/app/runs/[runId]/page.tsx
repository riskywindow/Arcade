import Link from "next/link";
import React, { type CSSProperties } from "react";

import { RunArtifactViewer } from "@/components/runs/run-artifact-viewer";
import { RunDetailTimeline } from "@/components/runs/run-detail-timeline";
import { RunOutcomePanel } from "@/components/runs/run-outcome-panel";
import { RunSecurityPanels } from "@/components/runs/run-security-panels";
import { SectionCard } from "@/components/section-card";
import { getRunReplay } from "@/lib/api/runs";
import {
  benchmarkRunIdFromRunId,
  deriveRunType,
  formatTimestamp,
  runTypeLabel,
} from "@/lib/runs";

type RunDetailPageProps = {
  params: Promise<{
    runId: string;
  }>;
};

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  const { runId } = await params;
  const replay = await getRunReplay(runId);
  const runType = deriveRunType(replay.run);
  const benchmarkRunId = benchmarkRunIdFromRunId(replay.run.runId);

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Run Detail</p>
          <h1 style={styles.title}>{replay.run.task.taskTitle}</h1>
          <p style={styles.subtitle}>
            {replay.run.runId} · {replay.run.scenario.scenarioName} ·{" "}
            {runTypeLabel(runType)}
          </p>
        </div>
        <div style={styles.linkRow}>
          {benchmarkRunId ? (
            <Link
              href={`/reports/benchmarks/helpdesk-v0/${benchmarkRunId}`}
              style={styles.link}
            >
              Open benchmark report
            </Link>
          ) : null}
          <Link href="/runs" style={styles.link}>
            Back to runs
          </Link>
        </div>
      </div>

      <div style={styles.grid}>
        <SectionCard
          title="Replay timeline"
          description="The main replay surface groups lifecycle, tool, policy, approval, audit, artifact, and terminal outcome events from the run replay contract."
        >
          <RunDetailTimeline replay={replay} />
        </SectionCard>
        <SectionCard
          title="Outcome and state"
          description="This summary ties the replay back to the task objective and the deterministic state checks that explain why the run succeeded, failed, or stayed incomplete."
        >
          <RunOutcomePanel replay={replay} />
        </SectionCard>
        <SectionCard
          title="Run summary"
          description="A compact summary of the selected run before the richer replay timeline lands."
        >
          <dl style={styles.metaGrid}>
            <div>
              <dt style={styles.term}>Status</dt>
              <dd style={styles.value}>{replay.run.status}</dd>
            </div>
            <div>
              <dt style={styles.term}>Created</dt>
              <dd style={styles.value}>
                {formatTimestamp(replay.run.createdAt)}
              </dd>
            </div>
            <div>
              <dt style={styles.term}>Completed</dt>
              <dd style={styles.value}>
                {formatTimestamp(replay.run.completedAt)}
              </dd>
            </div>
            <div>
              <dt style={styles.term}>Agent</dt>
              <dd style={styles.value}>
                {replay.run.activeAgentId ?? "unassigned"}
              </dd>
            </div>
            <div>
              <dt style={styles.term}>Timeline entries</dt>
              <dd style={styles.value}>{replay.timelineEntries.length}</dd>
            </div>
            <div>
              <dt style={styles.term}>Artifacts</dt>
              <dd style={styles.value}>{replay.artifacts.length}</dd>
            </div>
          </dl>
        </SectionCard>
        <SectionCard
          title="Bastion decisions"
          description="Policy outcomes, approval gates, and audit highlights stay visible here so operators can explain why a run was allowed, blocked, paused, or interrupted."
        >
          <RunSecurityPanels replay={replay} />
        </SectionCard>
        <SectionCard
          title="Artifact viewer"
          description="Browse screenshots and other evidence without leaving the run detail page."
        >
          <RunArtifactViewer replay={replay} />
        </SectionCard>
      </div>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    display: "grid",
    gap: "20px",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: "16px",
    alignItems: "flex-start",
  },
  eyebrow: {
    margin: "0 0 8px",
    color: "var(--accent)",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    fontSize: "0.8rem",
  },
  title: {
    margin: 0,
    fontSize: "2rem",
  },
  subtitle: {
    margin: "10px 0 0",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  link: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "10px 14px",
    borderRadius: "999px",
    border: "1px solid var(--border)",
    background: "var(--panel)",
  },
  linkRow: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap",
    justifyContent: "flex-end",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.8fr) minmax(280px, 1fr)",
    gap: "20px",
    alignItems: "start",
  },
  metaGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
    gap: "14px",
    margin: 0,
  },
  term: {
    fontSize: "0.8rem",
    color: "var(--muted)",
    marginBottom: "4px",
  },
  value: {
    margin: 0,
    lineHeight: 1.4,
  },
};

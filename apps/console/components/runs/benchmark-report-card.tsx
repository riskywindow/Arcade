"use client";

import Link from "next/link";
import React, { type CSSProperties } from "react";

import type {
  BenchmarkRunComparison,
  BenchmarkRunResult,
  ComparisonOutcome,
} from "@atlas/shared-types";

import { formatTimestamp } from "@/lib/runs";

type BenchmarkReportCardProps = {
  result: BenchmarkRunResult;
  comparison?: BenchmarkRunComparison | null;
};

export function BenchmarkReportCard({
  result,
  comparison,
}: BenchmarkReportCardProps) {
  const totals = result.items.reduce(
    (summary, item) => ({
      approvals: summary.approvals + item.scoreSummary.approvalCounts.total,
      denies: summary.denies + item.scoreSummary.policyCounts.deny,
      tools: summary.tools + item.scoreSummary.toolCallCount,
      artifacts: summary.artifacts + item.scoreSummary.artifactCount,
    }),
    { approvals: 0, denies: 0, tools: 0, artifacts: 0 },
  );
  const topRegressions = comparison?.regressions.slice(0, 3) ?? [];
  const topImprovements = comparison?.improvements.slice(0, 3) ?? [];

  return (
    <div style={styles.layout} data-testid="benchmark-report-card">
      <section style={styles.hero}>
        <div>
          <p style={styles.eyebrow}>Benchmark Report</p>
          <h2 style={styles.title}>{result.benchmarkRunId}</h2>
          <p style={styles.subtitle}>
            {result.catalogId} · started {formatTimestamp(result.startedAt)} ·
            completed {formatTimestamp(result.completedAt)}
          </p>
        </div>
        {comparison ? (
          <div style={comparisonBadge(comparison.outcome)}>
            <strong>{labelize(comparison.outcome)}</strong>
            <span style={styles.badgeCopy}>{comparison.summary}</span>
          </div>
        ) : (
          <div style={styles.heroNote}>
            <strong>No baseline comparison attached.</strong>
            <span style={styles.badgeCopy}>
              Add{" "}
              <code style={styles.inlineCode}>
                ?baseline=&lt;benchmark-run-id&gt;
              </code>{" "}
              to compare this report against a stored baseline.
            </span>
          </div>
        )}
      </section>

      <section style={styles.summaryGrid} aria-label="Benchmark summary">
        <MetricCard
          label="Passed runs"
          value={`${result.aggregate.passedRuns}/${result.aggregate.totalRuns}`}
        />
        <MetricCard
          label="Average score"
          value={formatScore(result.aggregate.averageScore)}
        />
        <MetricCard label="Approvals" value={String(totals.approvals)} />
        <MetricCard label="Denied actions" value={String(totals.denies)} />
        <MetricCard label="Tool calls" value={String(totals.tools)} />
        <MetricCard label="Artifacts" value={String(totals.artifacts)} />
      </section>

      {comparison ? (
        <section style={styles.comparisonPanel} aria-label="Comparison summary">
          <div style={styles.comparisonHeader}>
            <div>
              <p style={styles.sectionEyebrow}>Regression Readout</p>
              <h3 style={styles.sectionTitle}>
                What changed against the baseline
              </h3>
            </div>
            <Link
              href={`/reports/benchmarks/${result.catalogId}/${comparison.baseline.benchmarkRunId}`}
              style={styles.secondaryLink}
            >
              Open baseline report
            </Link>
          </div>
          <dl style={styles.deltaGrid}>
            <DeltaMetric
              label="Passed runs"
              current={`${result.aggregate.passedRuns}`}
              delta={comparison.passedRunDelta}
            />
            <DeltaMetric
              label="Failed runs"
              current={`${result.aggregate.failedRuns}`}
              delta={comparison.failedRunDelta}
            />
            <DeltaMetric
              label="Average score"
              current={formatScore(result.aggregate.averageScore)}
              delta={comparison.averageScoreDelta}
              precision={2}
            />
          </dl>
          <div style={styles.listGrid}>
            <InsightList
              title="Regression signals"
              emptyMessage="No tracked regressions were detected."
              items={topRegressions}
              tone="regression"
            />
            <InsightList
              title="Improvements"
              emptyMessage="No tracked improvements were detected."
              items={topImprovements}
              tone="improvement"
            />
          </div>
        </section>
      ) : null}

      <section style={styles.tableSection}>
        <div style={styles.comparisonHeader}>
          <div>
            <p style={styles.sectionEyebrow}>Scenario Scorecard</p>
            <h3 style={styles.sectionTitle}>
              Per-scenario outcomes and constraints
            </h3>
          </div>
        </div>
        <div style={styles.table}>
          <div style={styles.tableHeader}>
            <span>Scenario</span>
            <span>Outcome</span>
            <span>Score</span>
            <span>Approvals</span>
            <span>Denied</span>
            <span>Interpretation</span>
          </div>
          {result.items.map((item) => {
            const itemComparison = comparison?.itemComparisons.find(
              (entry) => entry.entryId === item.entryId,
            );
            return (
              <article key={item.entryId} style={styles.tableRow}>
                <div>
                  <strong style={styles.rowTitle}>{item.taskTitle}</strong>
                  <p style={styles.rowMeta}>
                    {item.entryId} ·{" "}
                    <Link
                      href={`/runs/${item.runId}`}
                      style={styles.inlineLink}
                    >
                      open run replay
                    </Link>
                  </p>
                </div>
                <span style={itemOutcomeBadge(item.scoreSummary.passed)}>
                  {item.scoreSummary.passed ? "passed" : "failed"}
                </span>
                <span>{formatScore(item.scoreSummary.score)}</span>
                <span>{item.scoreSummary.approvalCounts.total}</span>
                <span>{item.scoreSummary.policyCounts.deny}</span>
                <div>
                  <strong
                    style={itemComparisonTone(
                      itemComparison?.comparison.outcome,
                    )}
                  >
                    {itemComparison
                      ? labelize(itemComparison.comparison.outcome)
                      : "Standalone"}
                  </strong>
                  <p style={styles.rowMeta}>
                    {itemComparison?.comparison.summary ??
                      "No baseline comparison attached."}
                  </p>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <article style={styles.metricCard}>
      <p style={styles.metricLabel}>{label}</p>
      <h3 style={styles.metricValue}>{value}</h3>
    </article>
  );
}

function DeltaMetric({
  label,
  current,
  delta,
  precision,
}: {
  label: string;
  current: string;
  delta: number | null | undefined;
  precision?: number;
}) {
  return (
    <div>
      <dt style={styles.metricLabel}>{label}</dt>
      <dd style={styles.deltaValue}>
        {current}
        <span style={deltaBadge(delta)}>{formatDelta(delta, precision)}</span>
      </dd>
    </div>
  );
}

function InsightList({
  title,
  items,
  emptyMessage,
  tone,
}: {
  title: string;
  items: string[];
  emptyMessage: string;
  tone: "regression" | "improvement";
}) {
  return (
    <div style={styles.insightCard}>
      <h4 style={styles.insightTitle}>{title}</h4>
      {items.length === 0 ? (
        <p style={styles.emptyCopy}>{emptyMessage}</p>
      ) : (
        <ul style={styles.list}>
          {items.map((item) => (
            <li
              key={item}
              style={
                tone === "regression"
                  ? styles.regressionItem
                  : styles.improvementItem
              }
            >
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function formatScore(value: number | null | undefined): string {
  if (value == null) {
    return "n/a";
  }
  return value.toFixed(2);
}

function formatDelta(value: number | null | undefined, precision = 0): string {
  if (value == null) {
    return "unchanged";
  }
  if (value === 0) {
    return "unchanged";
  }
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(precision)}`;
}

function labelize(value: string): string {
  return value.replaceAll("_", " ");
}

function comparisonBadge(outcome: ComparisonOutcome): CSSProperties {
  if (outcome === "better") {
    return {
      ...styles.heroNote,
      borderColor: "#adc7a0",
      background: "#eef7e7",
      color: "#28522a",
    };
  }
  if (outcome === "worse") {
    return {
      ...styles.heroNote,
      borderColor: "#d4a4a4",
      background: "#fff1f0",
      color: "#7a2e29",
    };
  }
  return {
    ...styles.heroNote,
    borderColor: "#d8c59b",
    background: "#fbf4df",
    color: "#6a5311",
  };
}

function itemOutcomeBadge(passed: boolean): CSSProperties {
  return {
    ...styles.pill,
    background: passed ? "#ecf7ec" : "#fff0ef",
    color: passed ? "#29542e" : "#7b2922",
    borderColor: passed ? "#afd0af" : "#ddb0ae",
  };
}

function itemComparisonTone(
  outcome: ComparisonOutcome | undefined,
): CSSProperties {
  if (outcome === "better") {
    return { color: "#28522a" };
  }
  if (outcome === "worse") {
    return { color: "#7a2e29" };
  }
  return { color: "var(--text)" };
}

function deltaBadge(delta: number | null | undefined): CSSProperties {
  if (delta == null || delta === 0) {
    return {
      ...styles.deltaBadge,
      background: "#f5f0e6",
      color: "#6f6553",
    };
  }
  if (delta > 0) {
    return {
      ...styles.deltaBadge,
      background: "#fff0ef",
      color: "#7b2922",
    };
  }
  return {
    ...styles.deltaBadge,
    background: "#ecf7ec",
    color: "#29542e",
  };
}

const styles: Record<string, CSSProperties> = {
  layout: {
    display: "grid",
    gap: "20px",
  },
  hero: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.6fr) minmax(260px, 0.8fr)",
    gap: "16px",
    alignItems: "start",
  },
  eyebrow: {
    margin: "0 0 8px",
    color: "var(--accent)",
    fontSize: "0.8rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  title: {
    margin: 0,
    fontSize: "1.8rem",
  },
  subtitle: {
    margin: "10px 0 0",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  heroNote: {
    display: "grid",
    gap: "8px",
    padding: "16px",
    borderRadius: "18px",
    border: "1px solid var(--border)",
    background: "var(--panel)",
  },
  badgeCopy: {
    lineHeight: 1.5,
  },
  inlineCode: {
    fontSize: "0.85em",
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
    gap: "12px",
  },
  metricCard: {
    padding: "16px",
    borderRadius: "16px",
    border: "1px solid #eadfca",
    background: "#fffaf0",
  },
  metricLabel: {
    margin: 0,
    color: "var(--muted)",
    fontSize: "0.78rem",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  metricValue: {
    margin: "10px 0 0",
    fontSize: "1.5rem",
  },
  comparisonPanel: {
    display: "grid",
    gap: "16px",
    padding: "18px",
    borderRadius: "18px",
    border: "1px solid #ddcfb0",
    background: "linear-gradient(180deg, #fffaf1 0%, #fffdf8 100%)",
  },
  comparisonHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "16px",
    alignItems: "flex-start",
  },
  sectionEyebrow: {
    margin: "0 0 6px",
    color: "var(--accent)",
    fontSize: "0.74rem",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  sectionTitle: {
    margin: 0,
    fontSize: "1.05rem",
  },
  secondaryLink: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "10px 14px",
    borderRadius: "999px",
    border: "1px solid var(--border)",
    background: "var(--panel)",
  },
  deltaGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "12px",
    margin: 0,
  },
  deltaValue: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    margin: "8px 0 0",
    fontSize: "1.1rem",
  },
  deltaBadge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "4px 8px",
    borderRadius: "999px",
    fontSize: "0.76rem",
  },
  listGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: "14px",
  },
  insightCard: {
    borderRadius: "16px",
    border: "1px solid #eadfca",
    background: "rgba(255, 255, 255, 0.82)",
    padding: "14px",
  },
  insightTitle: {
    margin: 0,
    fontSize: "0.95rem",
  },
  emptyCopy: {
    margin: "10px 0 0",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  list: {
    margin: "10px 0 0",
    paddingLeft: "18px",
    display: "grid",
    gap: "8px",
  },
  regressionItem: {
    color: "#7a2e29",
    lineHeight: 1.5,
  },
  improvementItem: {
    color: "#28522a",
    lineHeight: 1.5,
  },
  tableSection: {
    display: "grid",
    gap: "14px",
  },
  table: {
    display: "grid",
    gap: "8px",
  },
  tableHeader: {
    display: "grid",
    gridTemplateColumns: "2.2fr 0.8fr 0.8fr 0.8fr 0.8fr 1.7fr",
    gap: "12px",
    padding: "0 4px",
    color: "var(--muted)",
    fontSize: "0.78rem",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  tableRow: {
    display: "grid",
    gridTemplateColumns: "2.2fr 0.8fr 0.8fr 0.8fr 0.8fr 1.7fr",
    gap: "12px",
    alignItems: "start",
    padding: "14px",
    borderRadius: "16px",
    border: "1px solid #eadfca",
    background: "#fffaf0",
  },
  rowTitle: {
    lineHeight: 1.4,
  },
  rowMeta: {
    margin: "6px 0 0",
    color: "var(--muted)",
    lineHeight: 1.45,
    fontSize: "0.92rem",
  },
  inlineLink: {
    color: "var(--accent)",
    textDecoration: "underline",
    textUnderlineOffset: "2px",
  },
  pill: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "30px",
    padding: "4px 10px",
    borderRadius: "999px",
    border: "1px solid transparent",
    textTransform: "lowercase",
    fontSize: "0.82rem",
  },
};

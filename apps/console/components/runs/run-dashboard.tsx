"use client";

import Link from "next/link";
import React, { useMemo, useState, type CSSProperties } from "react";

import type { Run } from "@atlas/shared-types";

import { deriveRunType, formatTimestamp, runDateKey, runTypeLabel } from "@/lib/runs";

type RunDashboardProps = {
  runs: Run[];
};

type FilterState = {
  status: string;
  scenario: string;
  date: string;
  runType: string;
  query: string;
};

const defaultFilters: FilterState = {
  status: "all",
  scenario: "all",
  date: "all",
  runType: "all",
  query: "",
};

export function RunDashboard({ runs }: RunDashboardProps) {
  const [filters, setFilters] = useState<FilterState>(defaultFilters);

  const scenarioOptions = useMemo(
    () =>
      Array.from(
        new Set(runs.map((run) => run.scenario.scenarioName)),
      ).sort((left, right) => left.localeCompare(right)),
    [runs],
  );
  const dateOptions = useMemo(
    () =>
      Array.from(new Set(runs.map((run) => runDateKey(run)))).sort((left, right) =>
        right.localeCompare(left),
      ),
    [runs],
  );

  const filteredRuns = useMemo(() => {
    const query = filters.query.trim().toLowerCase();
    return runs.filter((run) => {
      if (filters.status !== "all" && run.status !== filters.status) {
        return false;
      }

      if (
        filters.scenario !== "all" &&
        run.scenario.scenarioName !== filters.scenario
      ) {
        return false;
      }

      if (filters.date !== "all" && runDateKey(run) !== filters.date) {
        return false;
      }

      const runType = deriveRunType(run);
      if (filters.runType !== "all" && runType !== filters.runType) {
        return false;
      }

      if (query.length === 0) {
        return true;
      }

      const haystack = [
        run.runId,
        run.task.taskTitle,
        run.scenario.scenarioName,
        run.scenario.scenarioId,
        run.task.taskKind,
        run.activeAgentId ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [filters, runs]);

  const flagshipRun = useMemo(
    () =>
      runs.find((run) => deriveRunType(run) === "seeded_demo") ??
      runs[0] ??
      null,
    [runs],
  );

  const counts = useMemo(
    () => ({
      total: runs.length,
      paused: runs.filter((run) => run.status === "waiting_approval").length,
      failed: runs.filter((run) => run.status === "failed").length,
      demos: runs.filter((run) => deriveRunType(run) === "seeded_demo").length,
      benchmarks: runs.filter((run) => deriveRunType(run) === "benchmark").length,
    }),
    [runs],
  );

  if (runs.length === 0) {
    return (
      <div style={styles.emptyState} data-testid="run-dashboard-empty">
        <strong>No runs recorded yet.</strong>
        <p style={styles.emptyCopy}>
          Create or execute a seeded run to populate the operator dashboard.
        </p>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <section style={styles.summaryGrid}>
        <article style={styles.summaryCard}>
          <p style={styles.kicker}>Run Inventory</p>
          <h3 style={styles.summaryValue}>{counts.total}</h3>
          <p style={styles.summaryCopy}>Total recorded runs in the local store.</p>
        </article>
        <article style={styles.summaryCard}>
          <p style={styles.kicker}>Needs Attention</p>
          <h3 style={styles.summaryValue}>{counts.paused + counts.failed}</h3>
          <p style={styles.summaryCopy}>
            {counts.paused} paused and {counts.failed} failed runs.
          </p>
        </article>
        <article style={styles.summaryCard}>
          <p style={styles.kicker}>Flagship Demo</p>
          <h3 style={styles.summaryValue}>{counts.demos}</h3>
          <p style={styles.summaryCopy}>Seeded demo runs are labeled for quick access.</p>
        </article>
        <article style={styles.summaryCard}>
          <p style={styles.kicker}>Benchmark Slice</p>
          <h3 style={styles.summaryValue}>{counts.benchmarks}</h3>
          <p style={styles.summaryCopy}>Benchmark-like runs inferred from run naming today.</p>
        </article>
      </section>

      {flagshipRun ? (
        <article style={styles.featuredCard}>
          <div>
            <p style={styles.kicker}>Recommended Demo Path</p>
            <h3 style={styles.featuredTitle}>{flagshipRun.task.taskTitle}</h3>
            <p style={styles.featuredCopy}>
              {flagshipRun.scenario.scenarioName} · {flagshipRun.runId} ·{" "}
              {runTypeLabel(deriveRunType(flagshipRun))}
            </p>
          </div>
          <Link href={`/runs/${flagshipRun.runId}`} style={styles.primaryLink}>
            Open run detail
          </Link>
        </article>
      ) : null}

      <section style={styles.filterPanel} aria-label="Run filters">
        <label style={styles.field}>
          <span style={styles.label}>Search</span>
          <input
            aria-label="Search runs"
            type="text"
            value={filters.query}
            onChange={(event) =>
              setFilters((current) => ({ ...current, query: event.target.value }))
            }
            placeholder="Run ID, task, scenario, agent"
            style={styles.input}
          />
        </label>
        <label style={styles.field}>
          <span style={styles.label}>Status</span>
          <select
            aria-label="Filter by status"
            value={filters.status}
            onChange={(event) =>
              setFilters((current) => ({ ...current, status: event.target.value }))
            }
            style={styles.select}
          >
            <option value="all">All statuses</option>
            <option value="pending">Pending</option>
            <option value="ready">Ready</option>
            <option value="running">Running</option>
            <option value="waiting_approval">Waiting approval</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </label>
        <label style={styles.field}>
          <span style={styles.label}>Scenario</span>
          <select
            aria-label="Filter by scenario"
            value={filters.scenario}
            onChange={(event) =>
              setFilters((current) => ({ ...current, scenario: event.target.value }))
            }
            style={styles.select}
          >
            <option value="all">All scenarios</option>
            {scenarioOptions.map((scenario) => (
              <option key={scenario} value={scenario}>
                {scenario}
              </option>
            ))}
          </select>
        </label>
        <label style={styles.field}>
          <span style={styles.label}>Created date</span>
          <select
            aria-label="Filter by created date"
            value={filters.date}
            onChange={(event) =>
              setFilters((current) => ({ ...current, date: event.target.value }))
            }
            style={styles.select}
          >
            <option value="all">All dates</option>
            {dateOptions.map((date) => (
              <option key={date} value={date}>
                {date}
              </option>
            ))}
          </select>
        </label>
        <label style={styles.field}>
          <span style={styles.label}>Run type</span>
          <select
            aria-label="Filter by run type"
            value={filters.runType}
            onChange={(event) =>
              setFilters((current) => ({ ...current, runType: event.target.value }))
            }
            style={styles.select}
          >
            <option value="all">All run types</option>
            <option value="seeded_demo">Seeded demo</option>
            <option value="benchmark">Benchmark</option>
            <option value="standard">Standard</option>
          </select>
        </label>
      </section>

      {filteredRuns.length === 0 ? (
        <div style={styles.emptyState} data-testid="run-dashboard-no-results">
          <strong>No runs match the current filters.</strong>
          <p style={styles.emptyCopy}>
            Widen the filters to bring back paused, failed, or seeded demo runs.
          </p>
        </div>
      ) : (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.headerCell}>Run</th>
                <th style={styles.headerCell}>Task</th>
                <th style={styles.headerCell}>Scenario</th>
                <th style={styles.headerCell}>Type</th>
                <th style={styles.headerCell}>Status</th>
                <th style={styles.headerCell}>Created</th>
                <th style={styles.headerCell}>Result</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run) => {
                const runType = deriveRunType(run);
                return (
                  <tr key={run.runId} style={styles.row}>
                    <td style={styles.cell}>
                      <div style={styles.runCell}>
                        <Link href={`/runs/${run.runId}`} style={styles.runLink}>
                          {run.runId}
                        </Link>
                        <span style={styles.runMeta}>
                          {run.activeAgentId ?? "unassigned"}
                        </span>
                      </div>
                    </td>
                    <td style={styles.cell}>{run.task.taskTitle}</td>
                    <td style={styles.cell}>
                      <div style={styles.runCell}>
                        <span>{run.scenario.scenarioName}</span>
                        <span style={styles.runMeta}>{run.scenario.scenarioSeed}</span>
                      </div>
                    </td>
                    <td style={styles.cell}>
                      <span style={styles.typePill}>{runTypeLabel(runType)}</span>
                    </td>
                    <td style={styles.cell}>
                      <span style={statusPill(run.status)}>{run.status}</span>
                    </td>
                    <td style={styles.cell}>{formatTimestamp(run.createdAt)}</td>
                    <td style={styles.cell}>
                      {run.gradeResult?.outcome ?? "not graded"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function RunDashboardError({ message }: { message: string }) {
  return (
    <div style={styles.emptyState} data-testid="run-dashboard-error">
      <strong>Could not load runs.</strong>
      <p style={styles.emptyCopy}>{message}</p>
    </div>
  );
}

export function RunDashboardLoading() {
  return (
    <div style={styles.emptyState} data-testid="run-dashboard-loading">
      <strong>Loading runs…</strong>
      <p style={styles.emptyCopy}>
        The operator dashboard is waiting for the local API to return run data.
      </p>
    </div>
  );
}

const basePill: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  borderRadius: "999px",
  padding: "5px 10px",
  fontSize: "0.82rem",
  textTransform: "lowercase",
  border: "1px solid var(--border)",
};

function statusPill(status: Run["status"]): CSSProperties {
  if (status === "succeeded") {
    return { ...basePill, background: "#e7f5ee", borderColor: "#9bc5ad", color: "#1f5f4a" };
  }
  if (status === "failed") {
    return { ...basePill, background: "#fff0ec", borderColor: "#d6a698", color: "#8a4b3a" };
  }
  if (status === "waiting_approval") {
    return { ...basePill, background: "#fbf1d9", borderColor: "#d4be83", color: "#7a6118" };
  }
  if (status === "running") {
    return { ...basePill, background: "#eef5fb", borderColor: "#a7bfd7", color: "#305a79" };
  }
  if (status === "cancelled") {
    return { ...basePill, background: "#f0efef", borderColor: "#c7c3c3", color: "#5e5b5b" };
  }
  return { ...basePill, background: "#f7f4ec" };
}

const styles: Record<string, CSSProperties> = {
  page: {
    display: "grid",
    gap: "18px",
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "14px",
  },
  summaryCard: {
    padding: "16px",
    borderRadius: "16px",
    border: "1px solid var(--border)",
    background: "#fffdf8",
  },
  kicker: {
    margin: "0 0 6px",
    color: "var(--accent)",
    fontSize: "0.78rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  summaryValue: {
    margin: 0,
    fontSize: "2rem",
    lineHeight: 1,
  },
  summaryCopy: {
    margin: "10px 0 0",
    color: "var(--muted)",
    lineHeight: 1.45,
  },
  featuredCard: {
    display: "flex",
    justifyContent: "space-between",
    gap: "16px",
    alignItems: "center",
    padding: "18px 20px",
    borderRadius: "18px",
    border: "1px solid #c9d7cf",
    background: "linear-gradient(135deg, #eef7f0, #fffdf8)",
  },
  featuredTitle: {
    margin: 0,
    fontSize: "1.2rem",
  },
  featuredCopy: {
    margin: "8px 0 0",
    color: "var(--muted)",
  },
  primaryLink: {
    display: "inline-flex",
    whiteSpace: "nowrap",
    alignItems: "center",
    justifyContent: "center",
    padding: "10px 14px",
    borderRadius: "999px",
    border: "1px solid #1f5f4a",
    background: "#1f5f4a",
    color: "#fff",
  },
  filterPanel: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
    gap: "12px",
    padding: "16px",
    borderRadius: "18px",
    border: "1px solid var(--border)",
    background: "var(--panel)",
  },
  field: {
    display: "grid",
    gap: "6px",
  },
  label: {
    fontSize: "0.82rem",
    color: "var(--muted)",
  },
  input: {
    minWidth: 0,
    padding: "10px 12px",
    borderRadius: "12px",
    border: "1px solid var(--border)",
    background: "#fffcf5",
    fontFamily: "inherit",
    fontSize: "0.94rem",
  },
  select: {
    minWidth: 0,
    padding: "10px 12px",
    borderRadius: "12px",
    border: "1px solid var(--border)",
    background: "#fffcf5",
    fontFamily: "inherit",
    fontSize: "0.94rem",
  },
  tableWrap: {
    overflowX: "auto",
    border: "1px solid var(--border)",
    borderRadius: "18px",
    background: "var(--panel)",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  headerCell: {
    textAlign: "left",
    padding: "14px 16px",
    borderBottom: "1px solid var(--border)",
    fontSize: "0.8rem",
    color: "var(--muted)",
    letterSpacing: "0.06em",
    textTransform: "uppercase",
  },
  row: {
    borderBottom: "1px solid #ece6d8",
  },
  cell: {
    padding: "14px 16px",
    verticalAlign: "top",
    fontSize: "0.96rem",
  },
  runCell: {
    display: "grid",
    gap: "4px",
  },
  runLink: {
    color: "#1f5f4a",
    textDecoration: "underline",
    textUnderlineOffset: "3px",
  },
  runMeta: {
    color: "var(--muted)",
    fontSize: "0.84rem",
  },
  typePill: {
    ...basePill,
    background: "#f7f1e2",
    borderColor: "#ddcfaa",
    color: "#6b5a1b",
  },
  emptyState: {
    padding: "14px 2px",
  },
  emptyCopy: {
    margin: "8px 0 0",
    color: "var(--muted)",
    lineHeight: 1.6,
  },
};

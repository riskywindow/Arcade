import Link from "next/link";
import React, { type CSSProperties } from "react";

import { BenchmarkReportCard } from "@/components/runs/benchmark-report-card";
import { SectionCard } from "@/components/section-card";
import {
  getBenchmarkRunComparison,
  getBenchmarkRunResult,
} from "@/lib/api/runs";

type BenchmarkReportPageProps = {
  params: Promise<{
    catalogId: string;
    benchmarkRunId: string;
  }>;
  searchParams: Promise<{
    baseline?: string;
  }>;
};

export default async function BenchmarkReportPage({
  params,
  searchParams,
}: BenchmarkReportPageProps) {
  const { catalogId, benchmarkRunId } = await params;
  const { baseline } = await searchParams;
  const result = await getBenchmarkRunResult(catalogId, benchmarkRunId);
  const comparison =
    baseline && baseline !== benchmarkRunId
      ? await getBenchmarkRunComparison(catalogId, baseline, benchmarkRunId)
      : null;

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Report Surface</p>
          <h1 style={styles.title}>Benchmark scorecard</h1>
          <p style={styles.subtitle}>
            Compact, screenshot-friendly benchmark readout for demos, reviews,
            and portfolio evidence.
          </p>
        </div>
        <div style={styles.linkRow}>
          <Link href="/runs" style={styles.link}>
            Back to runs
          </Link>
          {comparison ? (
            <Link
              href={`/reports/benchmarks/${catalogId}/${benchmarkRunId}`}
              style={styles.link}
            >
              Clear comparison
            </Link>
          ) : null}
        </div>
      </div>

      <SectionCard
        title="Benchmark scorecard"
        description="This report stays intentionally narrow: aggregate benchmark outcome, policy posture, and per-scenario interpretation."
      >
        <BenchmarkReportCard result={result} comparison={comparison} />
      </SectionCard>
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
    maxWidth: "760px",
  },
  linkRow: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap",
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
};

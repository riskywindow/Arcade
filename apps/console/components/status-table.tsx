import React, { type CSSProperties } from "react";

import type { SystemStatusSnapshot } from "@atlas/shared-types";

type StatusTableProps = {
  snapshot: SystemStatusSnapshot;
};

export function StatusTable({ snapshot }: StatusTableProps) {
  const rows = [snapshot.api, snapshot.worker];

  return (
    <table style={styles.table}>
      <thead>
        <tr>
          <th style={styles.head}>Service</th>
          <th style={styles.head}>Reachable</th>
          <th style={styles.head}>Detail</th>
          <th style={styles.head}>URL</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.name}>
            <td style={styles.cell}>{row.name}</td>
            <td style={styles.cell}>{row.reachable ? "yes" : "no"}</td>
            <td style={styles.cell}>{row.detail}</td>
            <td style={styles.cell}>{row.url}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const styles: Record<string, CSSProperties> = {
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  head: {
    textAlign: "left",
    padding: "0 0 10px",
    borderBottom: "1px solid var(--border)",
    color: "var(--muted)",
    fontSize: "0.92rem",
  },
  cell: {
    padding: "12px 0",
    borderBottom: "1px solid var(--border)",
    verticalAlign: "top",
  },
};

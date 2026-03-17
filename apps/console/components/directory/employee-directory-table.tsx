import Link from "next/link";
import React, { type CSSProperties } from "react";

import type { DirectoryEmployee } from "@atlas/shared-types";

type EmployeeDirectoryTableProps = {
  employees: DirectoryEmployee[];
};

export function EmployeeDirectoryTable({ employees }: EmployeeDirectoryTableProps) {
  return (
    <div style={styles.shell}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.header}>Employee</th>
            <th style={styles.header}>Department</th>
            <th style={styles.header}>Role</th>
            <th style={styles.header}>Location</th>
          </tr>
        </thead>
        <tbody>
          {employees.map((employee) => (
            <tr key={employee.employeeId} style={styles.row}>
              <td style={styles.cell}>
                <Link
                  href={`/internal/directory/employees/${employee.employeeId}`}
                  style={styles.employeeLink}
                  data-testid={`employee-link-${employee.employeeId}`}
                >
                  <strong>{employee.displayName}</strong>
                  <span style={styles.meta}>{employee.email}</span>
                </Link>
              </td>
              <td style={styles.cell}>{employee.departmentSlug}</td>
              <td style={styles.cell}>{employee.title}</td>
              <td style={styles.cell}>{employee.location}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  shell: { overflowX: "auto" },
  table: { width: "100%", borderCollapse: "collapse" },
  header: {
    textAlign: "left",
    fontSize: "0.82rem",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: "var(--muted)",
    borderBottom: "1px solid var(--border)",
    padding: "0 0 12px",
  },
  row: { borderBottom: "1px solid rgba(217, 210, 194, 0.5)" },
  cell: { padding: "16px 0", verticalAlign: "top" },
  employeeLink: { display: "grid", gap: "6px" },
  meta: { color: "var(--muted)" },
};

import React, { type CSSProperties } from "react";

type StatusBadgeProps = {
  priority?: string;
  status: string;
};

export function StatusBadge({ priority, status }: StatusBadgeProps) {
  const background =
    status === "resolved"
      ? "#dff4e8"
      : status === "in_progress"
        ? "#f6ead3"
        : status === "pending_user"
          ? "#ece5f7"
          : "#e6eee9";

  return (
    <div style={styles.row}>
      <span style={{ ...styles.badge, background }}>{status.replaceAll("_", " ")}</span>
      {priority ? <span style={styles.priority}>{priority.toUpperCase()}</span> : null}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  row: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
    flexWrap: "wrap",
  },
  badge: {
    borderRadius: "999px",
    padding: "6px 10px",
    fontSize: "0.8rem",
    textTransform: "capitalize",
  },
  priority: {
    fontSize: "0.78rem",
    letterSpacing: "0.08em",
    color: "var(--muted)",
  },
};

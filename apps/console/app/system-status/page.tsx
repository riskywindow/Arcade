import React, { type CSSProperties } from "react";

import { SectionCard } from "@/components/section-card";
import { StatusTable } from "@/components/status-table";
import { getSystemStatus } from "@/lib/api/client";

export default async function SystemStatusPage() {
  const snapshot = await getSystemStatus();

  return (
    <div style={styles.page}>
      <SectionCard
        eyebrow="System"
        title="Local system status"
        description="This page is the first typed console-to-API boundary. It currently checks the API health endpoint and reserves space for later service panels."
      >
        <StatusTable snapshot={snapshot} />
      </SectionCard>
      <SectionCard
        title="Console notes"
        description={`Last checked at ${snapshot.checkedAt}.`}
      >
        <ul style={styles.list}>
          {snapshot.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </SectionCard>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    display: "grid",
    gap: "20px",
  },
  list: {
    margin: 0,
    paddingLeft: "20px",
    lineHeight: 1.7,
  },
};

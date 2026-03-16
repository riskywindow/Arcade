import React, { type CSSProperties } from "react";

import { SectionCard } from "@/components/section-card";

export default function RunsPage() {
  return (
    <div style={styles.page}>
      <SectionCard
        eyebrow="Runs"
        title="Run list placeholder"
        description="This route will become the operator entrypoint for browsing runs, filtering by outcome, and opening replay."
      >
        <ul style={styles.list}>
          <li>Future run summary table</li>
          <li>Filters for task, scenario, and status</li>
          <li>Links into replay and grade detail</li>
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

import React, { type CSSProperties } from "react";

import { SectionCard } from "@/components/section-card";

export default function ScenariosPage() {
  return (
    <div style={styles.page}>
      <SectionCard
        eyebrow="Scenarios"
        title="Scenario catalog placeholder"
        description="This route will eventually show seeded scenarios, task metadata, and benchmark-set composition."
      >
        <ul style={styles.list}>
          <li>Scenario inventory by environment</li>
          <li>Seed and reset metadata</li>
          <li>Task-to-scenario mapping for evaluation runs</li>
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

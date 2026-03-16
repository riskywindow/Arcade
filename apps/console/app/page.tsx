import React from "react";
import { SectionCard } from "@/components/section-card";

export default function HomePage() {
  return (
    <main style={styles.page}>
      <SectionCard
        eyebrow="Phase 1"
        title="Operator console shell"
        description="This scaffold establishes the information architecture for runs, scenarios, system status, replay, policy events, and grading without implementing those views yet."
      />
      <div style={styles.grid}>
        <SectionCard
          title="Planned replay insertion point"
          description="Future replay UI should land under the runs route and compose from reusable timeline, artifact, and policy-event panels."
        />
        <SectionCard
          title="Typed API boundary"
          description="The console talks to backend services through `lib/api/` and shared TypeScript contracts so route pages stay thin."
        />
      </div>
    </main>
  );
}

const styles = {
  page: {
    display: "grid",
    gap: "20px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: "20px",
  },
} satisfies Record<string, React.CSSProperties>;

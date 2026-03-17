import React, { type CSSProperties } from "react";

import { SectionCard } from "@/components/section-card";
import { TicketQueueTable } from "@/components/helpdesk/ticket-queue-table";
import { getHelpdeskQueue } from "@/lib/api/helpdesk";

export default async function HelpdeskQueuePage() {
  const queue = await getHelpdeskQueue();

  return (
    <div style={styles.page}>
      <SectionCard
        eyebrow="Internal App"
        title="Helpdesk Queue"
        description={`Seed ${queue.seed}. This queue is backed by the deterministic Phase 3 environment and is intended for local browse/edit workflows.`}
      >
        <TicketQueueTable tickets={queue.tickets} />
      </SectionCard>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    display: "grid",
    gap: "20px",
  },
};

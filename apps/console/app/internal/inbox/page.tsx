import React, { type CSSProperties } from "react";

import { InboxThreadList } from "@/components/inbox/inbox-thread-list";
import { SectionCard } from "@/components/section-card";
import { getInboxThreads } from "@/lib/api/inbox";

export default async function InboxPage() {
  const inbox = await getInboxThreads();

  return (
    <div style={styles.page}>
      <SectionCard
        eyebrow="Internal App"
        title="Inbox"
        description={`Seed ${inbox.seed}. Browse seeded employee email and internal message threads used by helpdesk and light incident scenarios.`}
      >
        <InboxThreadList threads={inbox.threads} />
      </SectionCard>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: { display: "grid", gap: "20px" },
};

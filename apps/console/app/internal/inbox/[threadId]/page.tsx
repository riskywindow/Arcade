import React from "react";

import { InboxThreadView } from "@/components/inbox/inbox-thread-view";
import { getInboxThread } from "@/lib/api/inbox";

export default async function InboxThreadPage({
  params,
}: {
  params: Promise<{ threadId: string }>;
}) {
  const { threadId } = await params;
  const response = await getInboxThread(threadId);

  return <InboxThreadView thread={response.thread} />;
}

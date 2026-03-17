import React from "react";

import { TicketDetailView } from "@/components/helpdesk/ticket-detail-view";
import { getHelpdeskTicketDetail } from "@/lib/api/helpdesk";

export default async function HelpdeskTicketPage({
  params,
}: {
  params: Promise<{ ticketId: string }>;
}) {
  const { ticketId } = await params;
  const detailResponse = await getHelpdeskTicketDetail(ticketId);

  return <TicketDetailView detail={detailResponse.detail} />;
}

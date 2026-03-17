import React from "react";
import { render, screen } from "@testing-library/react";

import type { InboxThread } from "@atlas/shared-types";

import { InboxThreadList } from "@/components/inbox/inbox-thread-list";
import { InboxThreadView } from "@/components/inbox/inbox-thread-view";

const thread: InboxThread = {
  threadId: "thread_001",
  participantEmails: [
    "tessa.nguyen@northstar-health.example",
    "helpdesk@northstar-health.example",
  ],
  subject: "Travel access issue details",
  lastMessageAt: "2026-01-05T09:00:00Z",
  messageCount: 2,
  messages: [
    {
      messageId: "message_001",
      sender: "tessa.nguyen@northstar-health.example",
      sentAt: "2026-01-05T09:00:00Z",
      subject: "Travel access issue details",
      body: "I replaced my phone during travel and now MFA is failing on every sign-in.",
      channel: "email",
    },
    {
      messageId: "message_002",
      sender: "helpdesk@northstar-health.example",
      sentAt: "2026-01-05T09:05:00Z",
      subject: "Travel access issue details",
      body: "We are reviewing your account and will confirm the safest recovery path.",
      channel: "internal_message",
    },
  ],
};

describe("inbox UI", () => {
  it("renders the seeded inbox thread list", () => {
    render(<InboxThreadList threads={[thread]} />);

    expect(
      screen.getByRole("link", { name: /travel access issue details/i }),
    ).toHaveAttribute("href", "/internal/inbox/thread_001");
    expect(screen.getByText(/2 messages/i)).toBeInTheDocument();
  });

  it("renders inbox thread detail", () => {
    render(<InboxThreadView thread={thread} />);

    expect(
      screen.getByRole("heading", { name: "Travel access issue details" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/reviewing your account/i)).toBeInTheDocument();
  });
});

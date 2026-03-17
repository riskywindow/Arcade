import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import type { HelpdeskTicket, HelpdeskTicketDetail } from "@atlas/shared-types";

import { TicketQueueTable } from "@/components/helpdesk/ticket-queue-table";
import { TicketDetailView } from "@/components/helpdesk/ticket-detail-view";
import { TicketActions } from "@/components/helpdesk/ticket-actions";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh,
  }),
}));

const baseTicket: HelpdeskTicket = {
  ticketId: "ticket_001",
  requesterEmployeeId: "employee_001",
  assignedTeam: "helpdesk",
  assignedTo: null,
  status: "open",
  priority: "p1",
  title: "Travel login lockout after phone replacement",
  summary: "Employee is traveling and cannot access email or VPN.",
  createdAt: "2026-01-05T09:00:00Z",
  updatedAt: "2026-01-05T09:00:00Z",
  relatedEmployeeId: "employee_001",
  relatedDeviceId: "device_001",
  tags: ["travel", "mfa"],
  notes: [],
};

const ticketDetail: HelpdeskTicketDetail = {
  ticket: baseTicket,
  requester: {
    employeeId: "employee_001",
    displayName: "Tessa Nguyen",
    email: "tessa.nguyen@northstar-health.example",
    title: "Implementation Consultant",
    departmentSlug: "customer-success",
    managerEmployeeId: "employee_002",
  },
  relatedEmployee: {
    employeeId: "employee_001",
    displayName: "Tessa Nguyen",
    email: "tessa.nguyen@northstar-health.example",
    title: "Implementation Consultant",
    departmentSlug: "customer-success",
    managerEmployeeId: "employee_002",
  },
  relatedDevice: {
    deviceId: "device_001",
    employeeId: "employee_001",
    hostname: "nst-tessa-nguyen",
    platform: "macos",
    healthState: "healthy",
    compromised: false,
    assignedAt: "2026-01-05T09:00:00Z",
    serialNumber: "SERIAL001",
  },
};

describe("helpdesk UI", () => {
  beforeEach(() => {
    refresh.mockReset();
    vi.restoreAllMocks();
  });

  it("renders the seeded ticket queue", () => {
    render(<TicketQueueTable tickets={[baseTicket]} />);

    expect(
      screen.getByRole("link", {
        name: /travel login lockout after phone replacement/i,
      }),
    ).toHaveAttribute("href", "/internal/helpdesk/tickets/ticket_001");
    expect(screen.getByText(/employee is traveling/i)).toBeInTheDocument();
  });

  it("renders ticket detail context and notes area", () => {
    render(<TicketDetailView detail={ticketDetail} />);

    expect(
      screen.getByRole("heading", {
        name: "Travel login lockout after phone replacement",
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Tessa Nguyen")).toHaveLength(2);
    expect(screen.getByText("No notes yet.")).toBeInTheDocument();
  });

  it("posts ticket actions and refreshes the page", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ticket: baseTicket }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <TicketActions
        currentAssignee={null}
        currentStatus="open"
        ticketId={baseTicket.ticketId}
      />,
    );

    fireEvent.change(screen.getByLabelText("Assigned To"), {
      target: { value: "samir.holt" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Save Assignment" }).closest("form")!);

    fireEvent.change(screen.getByLabelText("Status"), {
      target: { value: "in_progress" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Update Status" }).closest("form")!);

    fireEvent.change(screen.getByLabelText("Internal Note"), {
      target: { value: "Investigated and added an internal note." },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Add Note" }).closest("form")!);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(3);
      expect(refresh).toHaveBeenCalled();
    });
  });
});

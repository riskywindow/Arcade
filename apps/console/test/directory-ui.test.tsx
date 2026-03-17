import React from "react";
import { render, screen } from "@testing-library/react";

import type { DirectoryEmployee, DirectoryEmployeeDetail } from "@atlas/shared-types";

import { EmployeeDetailView } from "@/components/directory/employee-detail-view";
import { EmployeeDirectoryTable } from "@/components/directory/employee-directory-table";

const baseEmployee: DirectoryEmployee = {
  employeeId: "employee_001",
  displayName: "Tessa Nguyen",
  email: "tessa.nguyen@northstar-health.example",
  title: "Implementation Consultant",
  departmentSlug: "customer-success",
  employmentStatus: "active",
  location: "Denver, CO",
  managerEmployeeId: "employee_002",
  startDate: "2026-01-05T09:00:00Z",
};

const employeeDetail: DirectoryEmployeeDetail = {
  employee: baseEmployee,
  manager: {
    employeeId: "employee_002",
    displayName: "Elliot Sloan",
    email: "elliot.sloan@northstar-health.example",
    title: "Clinical Success Manager",
    departmentSlug: "customer-success",
    managerEmployeeId: null,
  },
  devices: [
    {
      deviceId: "device_001",
      employeeId: "employee_001",
      hostname: "nst-tessa-nguyen",
      platform: "macos",
      healthState: "healthy",
      compromised: false,
      assignedAt: "2026-01-05T09:00:00Z",
      serialNumber: "SERIAL001",
    },
  ],
  accountAccess: {
    accountId: "account_001",
    email: "tessa.nguyen@northstar-health.example",
    accountLocked: true,
    mfaEnrolled: true,
    groups: ["all-employees", "dept:customer-success"],
    isAdmin: false,
    passwordLastResetAt: "2026-01-05T09:00:00Z",
  },
  relatedTickets: [
    {
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
    },
  ],
  suspiciousEvents: [
    {
      eventId: "signal_001",
      employeeId: "employee_001",
      detectedAt: "2026-01-05T09:00:00Z",
      signalType: "travel_login_mismatch",
      severity: "medium",
      summary: "Sign-in from Denver shortly after a phone replacement while traveling.",
      disposition: "benign",
    },
  ],
};

describe("directory UI", () => {
  it("renders the seeded employee directory table", () => {
    render(<EmployeeDirectoryTable employees={[baseEmployee]} />);

    expect(
      screen.getByRole("link", { name: /tessa nguyen/i }),
    ).toHaveAttribute("href", "/internal/directory/employees/employee_001");
    expect(screen.getByText("customer-success")).toBeInTheDocument();
  });

  it("renders employee detail context", () => {
    render(<EmployeeDetailView detail={employeeDetail} />);

    expect(screen.getByRole("heading", { name: "Tessa Nguyen" })).toBeInTheDocument();
    expect(screen.getByText(/Implementation Consultant/)).toBeInTheDocument();
    expect(screen.getByText("Elliot Sloan")).toBeInTheDocument();
    expect(screen.getByText("travel_login_mismatch")).toBeInTheDocument();
  });
});

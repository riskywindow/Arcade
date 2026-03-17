import Link from "next/link";
import React, { type CSSProperties, type ReactNode } from "react";

import type { ConsoleNavItem } from "@atlas/shared-types";

const navItems: ConsoleNavItem[] = [
  {
    href: "/internal/helpdesk",
    label: "Helpdesk",
    description: "Seeded internal ticket queue and detail workflow.",
  },
  {
    href: "/internal/directory",
    label: "Directory",
    description: "Seeded employee, device, and access lookup workflow.",
  },
  {
    href: "/internal/wiki",
    label: "Wiki",
    description: "Seeded runbooks, policy docs, and troubleshooting guides.",
  },
  {
    href: "/internal/inbox",
    label: "Inbox",
    description: "Seeded email and internal message threads for scenario evidence.",
  },
  {
    href: "/",
    label: "Home",
    description: "Console overview and phase boundary.",
  },
  {
    href: "/runs",
    label: "Runs",
    description: "Future run list and replay entrypoint.",
  },
  {
    href: "/scenarios",
    label: "Scenarios",
    description: "Future seeded scenario catalog.",
  },
  {
    href: "/system-status",
    label: "System Status",
    description: "Local service reachability.",
  },
];

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div style={styles.frame}>
      <aside style={styles.sidebar}>
        <div style={styles.brandBlock}>
          <p style={styles.eyebrow}>Atlas + Bastion</p>
          <h1 style={styles.brand}>Operator Console</h1>
          <p style={styles.tagline}>
            Internal apps and operator views for the deterministic Atlas + Bastion demo path.
          </p>
        </div>
        <nav aria-label="Primary" style={styles.nav}>
          {navItems.map((item) => (
            <Link
              href={item.href}
              key={item.href}
              style={styles.navItem}
              data-testid={`nav-link-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
            >
              <strong>{item.label}</strong>
              <span style={styles.navDescription}>{item.description}</span>
            </Link>
          ))}
        </nav>
      </aside>
      <div style={styles.content}>{children}</div>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  frame: {
    display: "grid",
    gridTemplateColumns: "300px 1fr",
    minHeight: "100vh",
  },
  sidebar: {
    padding: "32px 24px",
    borderRight: "1px solid var(--border)",
    background: "rgba(255, 253, 248, 0.78)",
    backdropFilter: "blur(8px)",
  },
  brandBlock: {
    marginBottom: "28px",
  },
  eyebrow: {
    margin: "0 0 8px",
    fontSize: "0.8rem",
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "var(--muted)",
  },
  brand: {
    margin: 0,
    fontSize: "2rem",
    lineHeight: 1,
  },
  tagline: {
    margin: "12px 0 0",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  nav: {
    display: "grid",
    gap: "12px",
  },
  navItem: {
    display: "grid",
    gap: "4px",
    padding: "14px",
    border: "1px solid var(--border)",
    borderRadius: "14px",
    background: "var(--panel)",
  },
  navDescription: {
    color: "var(--muted)",
    fontSize: "0.92rem",
    lineHeight: 1.4,
  },
  content: {
    padding: "28px",
  },
};

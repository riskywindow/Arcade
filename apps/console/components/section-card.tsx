import React, { type CSSProperties, type ReactNode } from "react";

type SectionCardProps = {
  eyebrow?: string;
  title: string;
  description: string;
  children?: ReactNode;
};

export function SectionCard({
  eyebrow,
  title,
  description,
  children,
}: SectionCardProps) {
  return (
    <section style={styles.card}>
      {eyebrow ? <p style={styles.eyebrow}>{eyebrow}</p> : null}
      <h2 style={styles.title}>{title}</h2>
      <p style={styles.description}>{description}</p>
      {children ? <div style={styles.content}>{children}</div> : null}
    </section>
  );
}

const styles: Record<string, CSSProperties> = {
  card: {
    padding: "22px",
    borderRadius: "18px",
    border: "1px solid var(--border)",
    background: "var(--panel)",
    boxShadow: "0 12px 30px rgba(48, 41, 24, 0.05)",
  },
  eyebrow: {
    margin: "0 0 8px",
    color: "var(--accent)",
    fontSize: "0.8rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  title: {
    margin: 0,
    fontSize: "1.35rem",
  },
  description: {
    margin: "10px 0 0",
    color: "var(--muted)",
    lineHeight: 1.5,
  },
  content: {
    marginTop: "16px",
  },
};

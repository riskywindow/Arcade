import React, { type CSSProperties } from "react";

type WikiSearchFormProps = {
  query?: string;
};

export function WikiSearchForm({ query = "" }: WikiSearchFormProps) {
  return (
    <form action="/internal/wiki" method="get" style={styles.form}>
      <label htmlFor="wiki-search" style={styles.label}>
        Search docs
      </label>
      <div style={styles.row}>
        <input
          defaultValue={query}
          id="wiki-search"
          name="q"
          placeholder="travel, mfa, vpn, onboarding"
          style={styles.input}
          type="search"
        />
        <button style={styles.button} type="submit">
          Search
        </button>
      </div>
    </form>
  );
}

const styles: Record<string, CSSProperties> = {
  form: { display: "grid", gap: "8px" },
  label: { fontWeight: 600 },
  row: { display: "flex", gap: "10px", flexWrap: "wrap" },
  input: {
    flex: "1 1 320px",
    minHeight: "42px",
    borderRadius: "12px",
    border: "1px solid var(--border)",
    padding: "0 14px",
    background: "#fffdf8",
  },
  button: {
    minHeight: "42px",
    borderRadius: "12px",
    border: "1px solid rgba(112, 79, 34, 0.28)",
    background: "#f2e2bc",
    padding: "0 16px",
    fontWeight: 600,
  },
};

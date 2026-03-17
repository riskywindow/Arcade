"use client";

import React, {
  startTransition,
  useState,
  type CSSProperties,
  type FormEvent,
} from "react";
import { useRouter } from "next/navigation";

import {
  addHelpdeskTicketNote,
  assignHelpdeskTicket,
  transitionHelpdeskTicketStatus,
} from "@/lib/api/helpdesk";

type TicketActionsProps = {
  ticketId: string;
  currentAssignee?: string | null;
  currentStatus: string;
};

export function TicketActions({
  ticketId,
  currentAssignee,
  currentStatus,
}: TicketActionsProps) {
  const router = useRouter();
  const [assignedTo, setAssignedTo] = useState(currentAssignee ?? "");
  const [status, setStatus] = useState(currentStatus);
  const [noteBody, setNoteBody] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function runAction(work: () => Promise<void>) {
    setPending(true);
    setMessage(null);
    try {
      await work();
      startTransition(() => {
        router.refresh();
      });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unexpected error");
    } finally {
      setPending(false);
    }
  }

  function onAssign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runAction(async () => {
      await assignHelpdeskTicket(ticketId, {
        assignedTo: assignedTo.trim() || null,
      });
      setMessage("Assignment updated.");
    });
  }

  function onTransition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runAction(async () => {
      await transitionHelpdeskTicketStatus(ticketId, { status });
      setMessage("Status updated.");
    });
  }

  function onAddNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!noteBody.trim()) {
      setMessage("Note body is required.");
      return;
    }

    void runAction(async () => {
      await addHelpdeskTicketNote(ticketId, {
        author: assignedTo.trim() || "helpdesk.operator",
        body: noteBody.trim(),
        kind: "internal",
      });
      setNoteBody("");
      setMessage("Internal note added.");
    });
  }

  return (
    <div style={styles.stack}>
      <form onSubmit={onAssign} style={styles.form}>
        <label style={styles.label}>
          Assigned To
          <input
            aria-label="Assigned To"
            disabled={pending}
            onChange={(event) => setAssignedTo(event.target.value)}
            style={styles.input}
            value={assignedTo}
          />
        </label>
        <button disabled={pending} style={styles.button} type="submit">
          Save Assignment
        </button>
      </form>

      <form onSubmit={onTransition} style={styles.form}>
        <label style={styles.label}>
          Status
          <select
            aria-label="Status"
            disabled={pending}
            onChange={(event) => setStatus(event.target.value)}
            style={styles.input}
            value={status}
          >
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="pending_user">Pending User</option>
            <option value="resolved">Resolved</option>
          </select>
        </label>
        <button disabled={pending} style={styles.button} type="submit">
          Update Status
        </button>
      </form>

      <form onSubmit={onAddNote} style={styles.form}>
        <label style={styles.label}>
          Internal Note
          <textarea
            aria-label="Internal Note"
            disabled={pending}
            onChange={(event) => setNoteBody(event.target.value)}
            rows={4}
            style={styles.textarea}
            value={noteBody}
          />
        </label>
        <button disabled={pending} style={styles.button} type="submit">
          Add Note
        </button>
      </form>

      {message ? <p style={styles.message}>{message}</p> : null}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  stack: {
    display: "grid",
    gap: "14px",
  },
  form: {
    display: "grid",
    gap: "10px",
  },
  label: {
    display: "grid",
    gap: "8px",
    fontSize: "0.95rem",
  },
  input: {
    padding: "10px 12px",
    borderRadius: "12px",
    border: "1px solid var(--border)",
    background: "#fffefa",
    font: "inherit",
  },
  textarea: {
    padding: "12px",
    borderRadius: "12px",
    border: "1px solid var(--border)",
    background: "#fffefa",
    font: "inherit",
    resize: "vertical",
  },
  button: {
    justifySelf: "start",
    padding: "10px 14px",
    borderRadius: "999px",
    border: "1px solid var(--accent)",
    background: "var(--accent)",
    color: "#f8f6f0",
    cursor: "pointer",
    font: "inherit",
  },
  message: {
    margin: 0,
    color: "var(--muted)",
  },
};

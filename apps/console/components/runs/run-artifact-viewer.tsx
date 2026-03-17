"use client";

import React, { useMemo, useState, type CSSProperties } from "react";

import type { ReplayArtifactRef, ReplayTimelineEntry, RunReplay } from "@atlas/shared-types";

import { apiBaseUrl } from "@/lib/api/base-url";
import { formatTimestamp } from "@/lib/runs";

type RunArtifactViewerProps = {
  replay: RunReplay;
};

export function RunArtifactViewer({ replay }: RunArtifactViewerProps) {
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(
    replay.artifacts[0]?.artifactId ?? null,
  );

  const artifactsWithContext = useMemo(
    () =>
      replay.artifacts.map((artifact) => ({
        artifact,
        timelineEntry: findTimelineEntry(replay.timelineEntries, artifact),
      })),
    [replay.artifacts, replay.timelineEntries],
  );

  if (artifactsWithContext.length === 0) {
    return (
      <div style={styles.emptyState} data-testid="artifact-viewer-empty">
        <strong>No artifacts attached.</strong>
        <p style={styles.emptyCopy}>
          Screenshot and report artifacts will appear here once a run records evidence.
        </p>
      </div>
    );
  }

  const selected =
    artifactsWithContext.find(({ artifact }) => artifact.artifactId === selectedArtifactId) ??
    artifactsWithContext[0];
  const viewerUrl = artifactContentUrl(replay.run.runId, selected.artifact.artifactId);
  const isImage = selected.artifact.contentType.startsWith("image/");
  const sourceLabel =
    sourceFromArtifact(selected.artifact) ??
    selected.timelineEntry?.title ??
    "Artifact attachment";

  return (
    <div style={styles.layout} data-testid="artifact-viewer">
      <div style={styles.gallery}>
        {artifactsWithContext.map(({ artifact, timelineEntry }) => {
          const active = artifact.artifactId === selected.artifact.artifactId;
          return (
            <button
              key={artifact.artifactId}
              type="button"
              onClick={() => setSelectedArtifactId(artifact.artifactId)}
              style={thumbnailButton(active)}
            >
              <div style={styles.thumbnailPreview}>
                {artifact.contentType.startsWith("image/") ? (
                  <img
                    alt={artifact.displayName ?? artifact.artifactId}
                    src={artifactContentUrl(replay.run.runId, artifact.artifactId)}
                    style={styles.thumbnailImage}
                  />
                ) : (
                  <div style={styles.thumbnailFallback}>{artifact.kind}</div>
                )}
              </div>
              <div style={styles.thumbnailText}>
                <strong style={styles.thumbnailTitle}>
                  {artifact.displayName ?? artifact.artifactId}
                </strong>
                <span style={styles.thumbnailMeta}>
                  {timelineEntry?.title ?? artifact.kind}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      <div style={styles.viewerCard}>
        <div style={styles.viewerHeader}>
          <div>
            <p style={styles.kicker}>Selected Artifact</p>
            <h3 style={styles.viewerTitle}>
              {selected.artifact.displayName ?? selected.artifact.artifactId}
            </h3>
            <p style={styles.viewerCopy}>{sourceLabel}</p>
          </div>
          <a href={viewerUrl} style={styles.openLink} target="_blank" rel="noreferrer">
            Open raw artifact
          </a>
        </div>

        <div style={styles.previewFrame}>
          {isImage ? (
            <img
              alt={selected.artifact.displayName ?? selected.artifact.artifactId}
              src={viewerUrl}
              style={styles.previewImage}
            />
          ) : (
            <div style={styles.previewFallback}>
              <strong>{selected.artifact.kind}</strong>
              <span>{selected.artifact.contentType}</span>
            </div>
          )}
        </div>

        <dl style={styles.metaGrid}>
          <div>
            <dt style={styles.term}>Captured</dt>
            <dd style={styles.value}>{formatTimestamp(selected.artifact.createdAt)}</dd>
          </div>
          <div>
            <dt style={styles.term}>Related step</dt>
            <dd style={styles.value}>{selected.artifact.stepId ?? "Not linked"}</dd>
          </div>
          <div>
            <dt style={styles.term}>Related event</dt>
            <dd style={styles.value}>{selected.artifact.eventId ?? "Not linked"}</dd>
          </div>
          <div>
            <dt style={styles.term}>Source</dt>
            <dd style={styles.value}>{sourceLabel}</dd>
          </div>
          {selected.artifact.metadata.pageTitle ? (
            <div>
              <dt style={styles.term}>Page title</dt>
              <dd style={styles.value}>{String(selected.artifact.metadata.pageTitle)}</dd>
            </div>
          ) : null}
          {selected.artifact.metadata.currentUrl ? (
            <div>
              <dt style={styles.term}>Current URL</dt>
              <dd style={styles.value}>
                <code style={styles.inlineCode}>
                  {String(selected.artifact.metadata.currentUrl)}
                </code>
              </dd>
            </div>
          ) : null}
        </dl>
      </div>
    </div>
  );
}

function findTimelineEntry(
  timelineEntries: ReplayTimelineEntry[],
  artifact: ReplayArtifactRef,
): ReplayTimelineEntry | null {
  return (
    timelineEntries.find((entry) => entry.artifactId === artifact.artifactId) ??
    timelineEntries.find((entry) => entry.relatedArtifactIds.includes(artifact.artifactId)) ??
    null
  );
}

function artifactContentUrl(runId: string, artifactId: string): string {
  return `${apiBaseUrl}/runs/${runId}/artifacts/${artifactId}/content`;
}

function sourceFromArtifact(artifact: ReplayArtifactRef): string | null {
  const pageTitle = artifact.metadata.pageTitle;
  if (typeof pageTitle === "string" && pageTitle.length > 0) {
    return pageTitle;
  }
  const currentUrl = artifact.metadata.currentUrl;
  if (typeof currentUrl === "string" && currentUrl.length > 0) {
    return currentUrl;
  }
  return null;
}

function thumbnailButton(active: boolean): CSSProperties {
  return {
    ...styles.thumbnailButton,
    borderColor: active ? "#1f5f4a" : "#ddd5c4",
    boxShadow: active ? "0 0 0 2px rgba(31, 95, 74, 0.12)" : "none",
  };
}

const styles: Record<string, CSSProperties> = {
  layout: {
    display: "grid",
    gap: "16px",
  },
  gallery: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "10px",
  },
  thumbnailButton: {
    display: "grid",
    gap: "10px",
    textAlign: "left",
    padding: "10px",
    borderRadius: "14px",
    border: "1px solid #ddd5c4",
    background: "#fffdf8",
    cursor: "pointer",
  },
  thumbnailPreview: {
    aspectRatio: "16 / 10",
    borderRadius: "10px",
    overflow: "hidden",
    background: "#f4efe1",
    border: "1px solid #e3dbc6",
  },
  thumbnailImage: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    display: "block",
  },
  thumbnailFallback: {
    width: "100%",
    height: "100%",
    display: "grid",
    placeItems: "center",
    color: "var(--muted)",
    textTransform: "capitalize",
  },
  thumbnailText: {
    display: "grid",
    gap: "4px",
  },
  thumbnailTitle: {
    fontSize: "0.92rem",
  },
  thumbnailMeta: {
    color: "var(--muted)",
    fontSize: "0.82rem",
    lineHeight: 1.4,
  },
  viewerCard: {
    padding: "16px 18px",
    borderRadius: "16px",
    border: "1px solid var(--border)",
    background: "#fffdf8",
  },
  viewerHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "12px",
    alignItems: "flex-start",
  },
  kicker: {
    margin: "0 0 6px",
    color: "var(--accent)",
    fontSize: "0.78rem",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  viewerTitle: {
    margin: 0,
    fontSize: "1.1rem",
  },
  viewerCopy: {
    margin: "8px 0 0",
    color: "var(--muted)",
    lineHeight: 1.45,
  },
  openLink: {
    display: "inline-flex",
    whiteSpace: "nowrap",
    padding: "9px 12px",
    borderRadius: "999px",
    border: "1px solid var(--border)",
    background: "var(--panel)",
  },
  previewFrame: {
    marginTop: "14px",
    borderRadius: "16px",
    overflow: "hidden",
    border: "1px solid #e3dbc6",
    background: "#f7f3e8",
  },
  previewImage: {
    width: "100%",
    display: "block",
    objectFit: "contain",
    maxHeight: "460px",
    background: "#f7f3e8",
  },
  previewFallback: {
    minHeight: "220px",
    display: "grid",
    placeItems: "center",
    gap: "6px",
    color: "var(--muted)",
  },
  metaGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
    gap: "12px",
    margin: "14px 0 0",
  },
  term: {
    fontSize: "0.76rem",
    color: "var(--muted)",
    marginBottom: "4px",
  },
  value: {
    margin: 0,
    lineHeight: 1.45,
  },
  inlineCode: {
    fontFamily: "monospace",
    fontSize: "0.84rem",
    wordBreak: "break-all",
  },
  emptyState: {
    padding: "12px 2px",
  },
  emptyCopy: {
    margin: "8px 0 0",
    color: "var(--muted)",
    lineHeight: 1.6,
  },
};

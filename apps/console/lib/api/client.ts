import type { HealthStatus, SystemStatusSnapshot } from "@atlas/shared-types";

const apiBaseUrl =
  process.env.ATLAS_CONSOLE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getSystemStatus(
  fetchImpl: typeof fetch = fetch,
): Promise<SystemStatusSnapshot> {
  const apiHealthUrl = `${apiBaseUrl}/health`;

  try {
    const response = await fetchImpl(apiHealthUrl, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      return unavailableSnapshot(
        `API returned ${response.status}`,
        apiHealthUrl,
      );
    }

    const payload = (await response.json()) as HealthStatus;
    return {
      checkedAt: new Date().toISOString(),
      api: {
        name: payload.service,
        reachable: true,
        url: apiHealthUrl,
        detail: `healthy in ${payload.environment}`,
      },
      worker: {
        name: "atlas-worker",
        reachable: false,
        url: "local-process",
        detail: "worker process status is not wired into the console yet",
      },
      notes: [
        "System status is currently a typed scaffold around the API health endpoint.",
        "Replay, queue, and artifact service status panels will plug into this page later.",
      ],
    };
  } catch (error) {
    const detail = error instanceof Error ? error.message : "unknown error";
    return unavailableSnapshot(detail, apiHealthUrl);
  }
}

function unavailableSnapshot(
  detail: string,
  apiHealthUrl: string,
): SystemStatusSnapshot {
  return {
    checkedAt: new Date().toISOString(),
    api: {
      name: "atlas-api",
      reachable: false,
      url: apiHealthUrl,
      detail,
    },
    worker: {
      name: "atlas-worker",
      reachable: false,
      url: "local-process",
      detail: "worker process status is not wired into the console yet",
    },
    notes: [
      "The console can boot without the API, but system status will show degraded reachability.",
    ],
  };
}

import type {
  InboxThreadListResponse,
  InboxThreadResponse,
} from "@atlas/shared-types";

const apiBaseUrl =
  process.env.ATLAS_CONSOLE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getInboxThreads(
  fetchImpl: typeof fetch = fetch,
): Promise<InboxThreadListResponse> {
  const response = await fetchImpl(`${apiBaseUrl}/environments/helpdesk/inbox/threads`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  return parseJson<InboxThreadListResponse>(response);
}

export async function getInboxThread(
  threadId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<InboxThreadResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/environments/helpdesk/inbox/threads/${threadId}`,
    {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  return parseJson<InboxThreadResponse>(response);
}

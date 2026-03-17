import type {
  WikiDocumentListResponse,
  WikiDocumentResponse,
  WikiSearchResponse,
} from "@atlas/shared-types";

const apiBaseUrl =
  process.env.ATLAS_CONSOLE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getWikiDocuments(
  fetchImpl: typeof fetch = fetch,
): Promise<WikiDocumentListResponse> {
  const response = await fetchImpl(`${apiBaseUrl}/environments/helpdesk/wiki/documents`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  return parseJson<WikiDocumentListResponse>(response);
}

export async function getWikiDocument(
  slug: string,
  fetchImpl: typeof fetch = fetch,
): Promise<WikiDocumentResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/environments/helpdesk/wiki/documents/${slug}`,
    {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  return parseJson<WikiDocumentResponse>(response);
}

export async function searchWikiDocuments(
  query: string,
  fetchImpl: typeof fetch = fetch,
): Promise<WikiSearchResponse> {
  const params = new URLSearchParams({ q: query });
  const response = await fetchImpl(
    `${apiBaseUrl}/environments/helpdesk/wiki/search?${params.toString()}`,
    {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  return parseJson<WikiSearchResponse>(response);
}

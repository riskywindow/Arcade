import type {
  DirectoryEmployeeDetailResponse,
  DirectoryEmployeeListResponse,
} from "@atlas/shared-types";

const apiBaseUrl =
  process.env.ATLAS_CONSOLE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getDirectoryEmployees(
  fetchImpl: typeof fetch = fetch,
): Promise<DirectoryEmployeeListResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/environments/helpdesk/directory/employees`,
    { cache: "no-store", headers: { Accept: "application/json" } },
  );
  return parseJson<DirectoryEmployeeListResponse>(response);
}

export async function getDirectoryEmployeeDetail(
  employeeId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<DirectoryEmployeeDetailResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/environments/helpdesk/directory/employees/${employeeId}`,
    { cache: "no-store", headers: { Accept: "application/json" } },
  );
  return parseJson<DirectoryEmployeeDetailResponse>(response);
}

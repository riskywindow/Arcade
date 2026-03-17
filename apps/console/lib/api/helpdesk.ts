import type {
  AddTicketNoteRequest,
  AssignTicketRequest,
  HelpdeskTicketDetailResponse,
  HelpdeskTicketQueueResponse,
  HelpdeskTicketResponse,
  TransitionTicketStatusRequest,
} from "@atlas/shared-types";

const apiBaseUrl =
  process.env.ATLAS_CONSOLE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getHelpdeskQueue(
  fetchImpl: typeof fetch = fetch,
): Promise<HelpdeskTicketQueueResponse> {
  const response = await fetchImpl(`${apiBaseUrl}/environments/helpdesk/tickets`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  return parseJson<HelpdeskTicketQueueResponse>(response);
}

export async function getHelpdeskTicketDetail(
  ticketId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<HelpdeskTicketDetailResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/environments/helpdesk/tickets/${ticketId}`,
    {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  return parseJson<HelpdeskTicketDetailResponse>(response);
}

export async function assignHelpdeskTicket(
  ticketId: string,
  payload: AssignTicketRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<HelpdeskTicketResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/environments/helpdesk/tickets/${ticketId}/assignment`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  return parseJson<HelpdeskTicketResponse>(response);
}

export async function transitionHelpdeskTicketStatus(
  ticketId: string,
  payload: TransitionTicketStatusRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<HelpdeskTicketResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/environments/helpdesk/tickets/${ticketId}/status`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  return parseJson<HelpdeskTicketResponse>(response);
}

export async function addHelpdeskTicketNote(
  ticketId: string,
  payload: AddTicketNoteRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<HelpdeskTicketResponse> {
  const response = await fetchImpl(
    `${apiBaseUrl}/environments/helpdesk/tickets/${ticketId}/notes`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  return parseJson<HelpdeskTicketResponse>(response);
}

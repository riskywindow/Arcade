export type HealthStatus = {
  status: "ok";
  service: string;
  environment: string;
};

export type RunStatus =
  | "pending"
  | "ready"
  | "running"
  | "waiting_approval"
  | "succeeded"
  | "failed"
  | "cancelled";

export type RunStepStatus = "pending" | "in_progress" | "completed" | "failed";

export type ToolCallStatus = "requested" | "succeeded" | "failed" | "blocked";

export type PolicyDecisionOutcome = "allow" | "deny" | "require_approval";

export type PolicyCategory =
  | "safe_read"
  | "routine_mutation"
  | "sensitive_mutation"
  | "forbidden_shortcut"
  | "secret_access"
  | "approval_gated";

export type ResourceSensitivity = "low" | "medium" | "high" | "critical";

export type ApprovalRequestStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "expired"
  | "cancelled";

export type SecretHandleKind =
  | "password"
  | "api_token"
  | "session_cookie"
  | "opaque_value";

export type AuditEventKind =
  | "tool_request_received"
  | "policy_evaluated"
  | "tool_execution_completed"
  | "approval_requested"
  | "approval_resolved"
  | "secret_brokered"
  | "kill_switch_triggered";

export type ArtifactKind =
  | "log"
  | "screenshot"
  | "trace"
  | "diff"
  | "report"
  | "note";

export type GradeOutcome = "not_graded" | "passed" | "failed" | "partial";

export type RunEventType =
  | "run.created"
  | "run.ready"
  | "run.started"
  | "run.stop_requested"
  | "run.waiting_approval"
  | "run.resumed"
  | "run.step.created"
  | "approval.requested"
  | "approval.resolved"
  | "audit.recorded"
  | "tool_call.recorded"
  | "artifact.attached"
  | "run.completed";

export type RunEventSource =
  | "api"
  | "worker"
  | "agent"
  | "bastion"
  | "operator"
  | "grader"
  | "system";

export type ActorType =
  | "system"
  | "worker"
  | "agent"
  | "bastion"
  | "operator"
  | "grader";

export type ToolResultOutcome =
  | "success"
  | "retriable_error"
  | "fatal_error"
  | "invalid_request";

export type TerminationReason =
  | "success"
  | "awaiting_approval"
  | "approval_denied"
  | "max_steps_exceeded"
  | "invalid_tool_request"
  | "repeated_failure"
  | "model_error"
  | "scenario_unrecoverable"
  | "cancelled";

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | { [key: string]: JsonValue }
  | JsonValue[];

export type EnvironmentRef = {
  environmentId: string;
  environmentName: string;
  environmentVersion?: string | null;
};

export type ScenarioRef = {
  scenarioId: string;
  environmentId: string;
  scenarioName: string;
  scenarioSeed: string;
};

export type TaskRef = {
  taskId: string;
  scenarioId: string;
  taskKind: string;
  taskTitle: string;
};

export type ToolRequest = {
  requestId: string;
  toolName: string;
  arguments: { [key: string]: JsonValue };
  turnId?: string | null;
  requestedAt?: string | null;
  metadata: { [key: string]: JsonValue };
};

export type ToolResult = {
  requestId: string;
  toolName: string;
  outcome: ToolResultOutcome;
  result?: { [key: string]: JsonValue } | null;
  errorMessage?: string | null;
  artifactIds: string[];
  metadata: { [key: string]: JsonValue };
};

export type AgentTurn = {
  turnId: string;
  runId: string;
  turnIndex: number;
  summary: string;
  startedAt?: string | null;
  completedAt?: string | null;
  toolRequest?: ToolRequest | null;
  toolResult?: ToolResult | null;
  finalOutput?: string | null;
  metadata: { [key: string]: JsonValue };
};

export type ExecutionContext = {
  runId: string;
  agentId?: string | null;
  environment: EnvironmentRef;
  scenario: ScenarioRef;
  task: TaskRef;
  taskBrief: string;
  successCondition?: string | null;
  allowedToolNames: string[];
  maxTurns: number;
  metadata: { [key: string]: JsonValue };
};

export type RunExecutionSummary = {
  runId: string;
  agentId?: string | null;
  finalRunStatus: RunStatus;
  terminationReason: TerminationReason;
  turnsExecuted: number;
  stepsRecorded: number;
  toolCallsRecorded: number;
  artifactIds: string[];
  finalOutput?: string | null;
  metadata: { [key: string]: JsonValue };
};

export type RetryPolicy = {
  maxAttempts: number;
  retryableErrorKinds: string[];
};

export type AgentConfig = {
  provider: string;
  modelName: string;
  temperature: number;
  deterministic: boolean;
  maxSteps: number;
  retryPolicy: RetryPolicy;
  allowedToolNames: string[];
  metadata: { [key: string]: JsonValue };
};

export type ModelToolDefinition = {
  name: string;
  description: string;
  inputSchema: { [key: string]: JsonValue };
  outputSchema: { [key: string]: JsonValue };
  metadata: { [key: string]: JsonValue };
};

export type ModelInvocation = {
  context: ExecutionContext;
  agentConfig: AgentConfig;
  availableTools: ModelToolDefinition[];
  turnHistory: AgentTurn[];
  metadata: { [key: string]: JsonValue };
};

export type ModelResponse = {
  toolRequest?: ToolRequest | null;
  finalOutput?: string | null;
  rawOutput?: string | null;
  metadata: { [key: string]: JsonValue };
};

export type ToolExecutionMetadata = {
  readOnly: boolean;
  idempotent: boolean;
  requiresBrowser: boolean;
  timeoutSeconds: number;
  tags: string[];
};

export type ToolSpec = {
  name: string;
  description: string;
  inputSchema: { [key: string]: JsonValue };
  resultSchema: { [key: string]: JsonValue };
  executionMetadata: ToolExecutionMetadata;
};

export type VisibleSurface =
  | "helpdesk"
  | "employee_directory"
  | "internal_wiki"
  | "inbox";

export type AllowedToolSurface =
  | "browser"
  | "directory_lookup"
  | "document_lookup"
  | "identity_api"
  | "device_api"
  | "approval";

export type VisibleTicketContext = {
  ticketId: string;
  title: string;
  summary: string;
  priority: string;
  status: string;
  requesterEmployeeId: string;
  relatedEmployeeId?: string | null;
  relatedDeviceId?: string | null;
  tags: string[];
};

export type PublicTaskBrief = {
  taskId: string;
  taskKind: string;
  taskTitle: string;
  userProblemSummary: string;
  successCondition: string;
  urgency: string;
  businessContext: string;
  visibleTicket: VisibleTicketContext;
  visibleNotes: string[];
};

export type PublicScenarioDefinition = {
  scenarioId: string;
  environmentId: string;
  scenarioName: string;
  scenarioSeed: string;
  visibleSurfaces: VisibleSurface[];
  allowedToolSurfaces: AllowedToolSurface[];
  publicTask: PublicTaskBrief;
};

export type HelpdeskEnvironmentContract = {
  environmentId: string;
  environmentName: string;
  environmentVersion: string;
  visibleSurfaces: VisibleSurface[];
  hiddenStateDomains: string[];
  resetHooks: string[];
  allowedMutationTargets: string[];
  graderHookPoints: string[];
  scenarioIds: string[];
};

export type NoteKind = "internal" | "customer" | "resolution";

export type EmployeeSummary = {
  employeeId: string;
  displayName: string;
  email: string;
  title: string;
  departmentSlug: string;
  managerEmployeeId?: string | null;
};

export type DeviceSummary = {
  deviceId: string;
  employeeId: string;
  hostname: string;
  platform: string;
  healthState: string;
  compromised: boolean;
  assignedAt: string;
  serialNumber: string;
};

export type AccountAccessSummary = {
  accountId: string;
  email: string;
  accountLocked: boolean;
  mfaEnrolled: boolean;
  groups: string[];
  isAdmin: boolean;
  passwordLastResetAt: string;
};

export type SuspiciousEventSummary = {
  eventId: string;
  employeeId: string;
  detectedAt: string;
  signalType: string;
  severity: string;
  summary: string;
  disposition: string;
};

export type DirectoryEmployee = {
  employeeId: string;
  displayName: string;
  email: string;
  title: string;
  departmentSlug: string;
  employmentStatus: string;
  location: string;
  managerEmployeeId?: string | null;
  startDate: string;
};

export type DirectoryEmployeeListResponse = {
  seed: string;
  employees: DirectoryEmployee[];
};

export type DirectoryEmployeeDetail = {
  employee: DirectoryEmployee;
  manager?: EmployeeSummary | null;
  devices: DeviceSummary[];
  accountAccess: AccountAccessSummary;
  relatedTickets: HelpdeskTicket[];
  suspiciousEvents: SuspiciousEventSummary[];
};

export type DirectoryEmployeeDetailResponse = {
  detail: DirectoryEmployeeDetail;
};

export type WikiDocument = {
  pageId: string;
  slug: string;
  title: string;
  category: string;
  summary: string;
  body: string;
  updatedAt: string;
};

export type WikiDocumentListResponse = {
  seed: string;
  documents: WikiDocument[];
};

export type WikiDocumentResponse = {
  document: WikiDocument;
};

export type WikiSearchResult = {
  document: WikiDocument;
  score: number;
  matchedTerms: string[];
};

export type WikiSearchResponse = {
  seed: string;
  query: string;
  results: WikiSearchResult[];
};

export type InboxMessage = {
  messageId: string;
  sender: string;
  sentAt: string;
  subject: string;
  body: string;
  channel: string;
};

export type InboxThread = {
  threadId: string;
  participantEmails: string[];
  subject: string;
  messages: InboxMessage[];
  lastMessageAt: string;
  messageCount: number;
};

export type InboxThreadListResponse = {
  seed: string;
  threads: InboxThread[];
};

export type InboxThreadResponse = {
  thread: InboxThread;
};

export type TicketNote = {
  noteId: string;
  ticketId: string;
  author: string;
  body: string;
  kind: NoteKind;
  createdAt: string;
};

export type HelpdeskTicket = {
  ticketId: string;
  requesterEmployeeId: string;
  assignedTeam: string;
  assignedTo?: string | null;
  status: string;
  priority: string;
  title: string;
  summary: string;
  createdAt: string;
  updatedAt: string;
  relatedEmployeeId?: string | null;
  relatedDeviceId?: string | null;
  tags: string[];
  notes: TicketNote[];
};

export type HelpdeskTicketDetail = {
  ticket: HelpdeskTicket;
  requester: EmployeeSummary;
  relatedEmployee?: EmployeeSummary | null;
  relatedDevice?: DeviceSummary | null;
};

export type HelpdeskTicketQueueResponse = {
  seed: string;
  tickets: HelpdeskTicket[];
};

export type HelpdeskTicketResponse = {
  ticket: HelpdeskTicket;
};

export type HelpdeskTicketDetailResponse = {
  detail: HelpdeskTicketDetail;
};

export type AddTicketNoteRequest = {
  author: string;
  body: string;
  kind?: NoteKind;
};

export type AssignTicketRequest = {
  assignedTo?: string | null;
};

export type TransitionTicketStatusRequest = {
  status: string;
};

export type RunStep = {
  stepId: string;
  runId: string;
  stepIndex: number;
  title: string;
  status: RunStepStatus;
  startedAt?: string | null;
  completedAt?: string | null;
};

export type ToolCall = {
  toolCallId: string;
  toolName: string;
  action: string;
  arguments: Record<string, JsonValue>;
  status: ToolCallStatus;
  result?: Record<string, JsonValue> | null;
  errorMessage?: string | null;
};

export type PolicyDecision = {
  decisionId: string;
  outcome: PolicyDecisionOutcome;
  actionType: string;
  rationale: string;
  approvalRequestId?: string | null;
  metadata: Record<string, JsonValue>;
};

export type SecretHandle = {
  secretId: string;
  handle: string;
  kind: SecretHandleKind;
  scope: string;
  redactionHint?: string | null;
  metadata: Record<string, JsonValue>;
};

export type ApprovalRequestRef = {
  approvalRequestId: string;
  runId: string;
  stepId?: string | null;
  status: ApprovalRequestStatus;
  requestedActionType: string;
  toolName?: string | null;
  requestedArguments: Record<string, JsonValue>;
  requesterRole: string;
  reasonCode?: string | null;
  summary?: string | null;
  targetResourceType?: string | null;
  targetResourceId?: string | null;
  requestedAt: string;
  expiresAt?: string | null;
  resolvedAt?: string | null;
  resolutionSummary?: string | null;
  metadata: Record<string, JsonValue>;
};

export type AuditRecordEnvelope = {
  auditId: string;
  runId: string;
  stepId?: string | null;
  requestId?: string | null;
  actorType: ActorType;
  eventKind: AuditEventKind;
  occurredAt: string;
  payload: Record<string, JsonValue>;
};

export type BastionToolRequest = {
  requestId: string;
  runId: string;
  stepId: string;
  turnId?: string | null;
  agentId?: string | null;
  environment: EnvironmentRef;
  scenario: ScenarioRef;
  task: TaskRef;
  toolRequest: ToolRequest;
  toolSpec: ToolSpec;
  requestedAt?: string | null;
  metadata: Record<string, JsonValue>;
};

export type PolicyEvaluationInput = {
  requestId: string;
  runId: string;
  stepId: string;
  agentId?: string | null;
  environment: EnvironmentRef;
  scenario: ScenarioRef;
  task: TaskRef;
  toolName: string;
  actionType: string;
  requesterRole: string;
  targetResourceType?: string | null;
  targetResourceId?: string | null;
  policyCategoryHint?: PolicyCategory | null;
  resourceSensitivity: ResourceSensitivity;
  readOnly: boolean;
  requiresBrowser: boolean;
  secretAccessRequested: boolean;
  toolTags: string[];
  metadata: Record<string, JsonValue>;
};

export type PolicyEvaluationResult = {
  decision: PolicyDecision;
  category: PolicyCategory;
  reasonCode: string;
  enforcementMessage?: string | null;
  auditMetadata: Record<string, JsonValue>;
};

export type PolicyRuleMatch = {
  scenarioIds?: string[];
  taskKinds?: string[];
  requesterRoles?: string[];
  toolNames?: string[];
  actionTypes?: string[];
  targetResourceTypes?: string[];
  policyCategories?: PolicyCategory[];
  resourceSensitivities?: ResourceSensitivity[];
  readOnly?: boolean | null;
  requiresBrowser?: boolean | null;
  secretAccessRequested?: boolean | null;
  toolTagsAll?: string[];
};

export type PolicyRule = {
  ruleId: string;
  description: string;
  priority: number;
  match: PolicyRuleMatch;
  outcome: PolicyDecisionOutcome;
  category: PolicyCategory;
  rationale: string;
  reasonCode?: string | null;
  enforcementMessage?: string | null;
  approvalActionType?: string | null;
  metadata: Record<string, JsonValue>;
};

export type PolicyPack = {
  packId: string;
  version: string;
  defaultOutcome: PolicyDecisionOutcome;
  defaultCategory: PolicyCategory;
  defaultRationale: string;
  defaultReasonCode?: string | null;
  rules: PolicyRule[];
};

export type BastionToolResponse = {
  requestId: string;
  runId: string;
  stepId: string;
  policyEvaluation: PolicyEvaluationResult;
  toolResult?: ToolResult | null;
  approvalRequest?: ApprovalRequestRef | null;
  secretHandles: SecretHandle[];
  auditRecords: AuditRecordEnvelope[];
  metadata: Record<string, JsonValue>;
};

export type Artifact = {
  schemaVersion: number;
  artifactId: string;
  runId?: string | null;
  stepId?: string | null;
  kind: ArtifactKind;
  uri: string;
  contentType: string;
  createdAt: string;
  displayName?: string | null;
  description?: string | null;
  sha256?: string | null;
  sizeBytes?: number | null;
  metadata: Record<string, JsonValue>;
};

export type GradeResult = {
  gradeId?: string | null;
  outcome: GradeOutcome;
  score?: number | null;
  summary: string;
  rubricVersion?: string | null;
  evidenceArtifactIds: string[];
  details: Record<string, JsonValue>;
};

export type Run = {
  runId: string;
  environment: EnvironmentRef;
  scenario: ScenarioRef;
  task: TaskRef;
  status: RunStatus;
  createdAt: string;
  updatedAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
  currentStepIndex: number;
  activeAgentId?: string | null;
  gradeResult?: GradeResult | null;
};

export type RunCreatedPayload = {
  schemaVersion: number;
  eventType: "run.created";
  run: Run;
};

export type RunReadyPayload = {
  schemaVersion: number;
  eventType: "run.ready";
  runId: string;
  status: "ready";
};

export type RunStartedPayload = {
  schemaVersion: number;
  eventType: "run.started";
  runId: string;
  status: "running";
  startedAt: string;
};

export type RunStopRequestedPayload = {
  schemaVersion: number;
  eventType: "run.stop_requested";
  runId: string;
  stopRequestId: string;
  operatorId: string;
  requestedAt: string;
  reason?: string | null;
};

export type RunWaitingApprovalPayload = {
  schemaVersion: number;
  eventType: "run.waiting_approval";
  runId: string;
  status: "waiting_approval";
  approvalRequestId: string;
  waitingAt: string;
};

export type RunResumedPayload = {
  schemaVersion: number;
  eventType: "run.resumed";
  runId: string;
  status: "running";
  approvalRequestId: string;
  resumedAt: string;
};

export type RunStepCreatedPayload = {
  schemaVersion: number;
  eventType: "run.step.created";
  runId: string;
  step: RunStep;
};

export type ToolCallRecordedPayload = {
  schemaVersion: number;
  eventType: "tool_call.recorded";
  runId: string;
  stepId?: string | null;
  toolCall: ToolCall;
  policyDecision?: PolicyDecision | null;
};

export type ApprovalRequestedPayload = {
  schemaVersion: number;
  eventType: "approval.requested";
  runId: string;
  approvalRequest: Record<string, JsonValue>;
};

export type ApprovalResolvedPayload = {
  schemaVersion: number;
  eventType: "approval.resolved";
  runId: string;
  approvalRequest: Record<string, JsonValue>;
  operatorId: string;
  decidedAt: string;
};

export type AuditRecordedPayload = {
  schemaVersion: number;
  eventType: "audit.recorded";
  runId: string;
  auditRecord: Record<string, JsonValue>;
};

export type ArtifactAttachedPayload = {
  schemaVersion: number;
  eventType: "artifact.attached";
  runId: string;
  stepId?: string | null;
  artifact: Artifact;
};

export type RunCompletedPayload = {
  schemaVersion: number;
  eventType: "run.completed";
  runId: string;
  finalStatus: "succeeded" | "failed" | "cancelled";
  completedAt: string;
  gradeResult?: GradeResult | null;
};

export type RunEventPayload =
  | RunCreatedPayload
  | RunReadyPayload
  | RunStartedPayload
  | RunStopRequestedPayload
  | RunWaitingApprovalPayload
  | RunResumedPayload
  | RunStepCreatedPayload
  | ApprovalRequestedPayload
  | ApprovalResolvedPayload
  | AuditRecordedPayload
  | ToolCallRecordedPayload
  | ArtifactAttachedPayload
  | RunCompletedPayload;

export type RunEvent = {
  schemaVersion: number;
  eventId: string;
  runId: string;
  sequence: number;
  occurredAt: string;
  source: RunEventSource;
  actorType: ActorType;
  correlationId?: string | null;
  eventType: RunEventType;
  payload: RunEventPayload;
};

export type CreateRunRequest = {
  environment: EnvironmentRef;
  scenario: ScenarioRef;
  task: TaskRef;
  activeAgentId?: string | null;
};

export type RunResponse = {
  run: Run;
};

export type RunListResponse = {
  runs: Run[];
};

export type RunEventListResponse = {
  runId: string;
  events: RunEvent[];
};

export type ArtifactListResponse = {
  runId: string;
  artifacts: Artifact[];
};

export type AuditListResponse = {
  runId: string;
  records: AuditRecordEnvelope[];
};

export type ApprovalListResponse = {
  runId: string;
  approvals: ApprovalRequestRef[];
};

export type ApprovalDecisionRequest = {
  operatorId: string;
  resolutionSummary?: string | null;
};

export type StopRunRequest = {
  operatorId: string;
  reason?: string | null;
};

export type ApprovalResponse = {
  approval: ApprovalRequestRef;
};

export type StopRunResponse = {
  runId: string;
  status: RunStatus;
  stopRequestId: string;
  requestedAt: string;
};

export type ServiceStatus = {
  name: string;
  reachable: boolean;
  url: string;
  detail: string;
};

export type SystemStatusSnapshot = {
  checkedAt: string;
  api: ServiceStatus;
  worker: ServiceStatus;
  notes: string[];
};

export type ConsoleNavItem = {
  href: string;
  label: string;
  description: string;
};

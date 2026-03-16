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
  | "run.step.created"
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
  | RunStepCreatedPayload
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

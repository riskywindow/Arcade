from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from atlas_core import EnvironmentRef, ScenarioRef, TaskRef


class HelpdeskModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


ENVIRONMENT_ID = "env_helpdesk"
ENVIRONMENT_NAME = "Northstar Helpdesk"
ENVIRONMENT_VERSION = "v1"


class VisibleSurface(StrEnum):
    HELPDESK = "helpdesk"
    EMPLOYEE_DIRECTORY = "employee_directory"
    INTERNAL_WIKI = "internal_wiki"
    INBOX = "inbox"


class AllowedToolSurface(StrEnum):
    BROWSER = "browser"
    DIRECTORY_LOOKUP = "directory_lookup"
    DOCUMENT_LOOKUP = "document_lookup"
    IDENTITY_API = "identity_api"
    DEVICE_API = "device_api"
    APPROVAL = "approval"


class PolicyExpectation(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    ALLOW_AND_DENY_PATHS = "allow_and_deny_paths"
    DENY_AND_REQUIRE_APPROVAL_PATHS = "deny_and_require_approval_paths"


class ResetHookKind(StrEnum):
    REBUILD_FROM_SEED = "rebuild_from_seed"
    RESET_BASELINE_FIXTURE = "reset_baseline_fixture"


class GraderHookName(StrEnum):
    ACCOUNT_STATE = "account_state"
    MFA_STATE = "mfa_state"
    GROUP_MEMBERSHIP = "group_membership"
    TICKET_STATE = "ticket_state"
    SOP_EVIDENCE = "sop_evidence"
    APPROVAL_RECORD = "approval_record"
    DEVICE_STATE = "device_state"
    INBOX_CONTEXT = "inbox_context"


class VisibleTicketContext(HelpdeskModel):
    ticket_id: str
    title: str
    summary: str
    priority: str
    status: str
    requester_employee_id: str
    related_employee_id: str | None = None
    related_device_id: str | None = None
    tags: tuple[str, ...] = ()


class PublicTaskBrief(HelpdeskModel):
    task_id: str
    task_kind: str
    task_title: str
    user_problem_summary: str
    success_condition: str
    urgency: str
    business_context: str
    visible_ticket: VisibleTicketContext
    visible_notes: tuple[str, ...] = ()


class PublicScenarioDefinition(HelpdeskModel):
    scenario_id: str
    environment_id: str
    scenario_name: str
    scenario_seed: str
    visible_surfaces: tuple[VisibleSurface, ...]
    allowed_tool_surfaces: tuple[AllowedToolSurface, ...]
    public_task: PublicTaskBrief


class ScenarioHiddenTruth(HelpdeskModel):
    owner: str
    root_cause: str
    required_final_state: tuple[str, ...]
    expected_side_effects: tuple[str, ...]
    negative_conditions: tuple[str, ...]
    tempting_shortcuts: tuple[str, ...]
    hidden_state_refs: tuple[str, ...]


class ScenarioGraderHooks(HelpdeskModel):
    hook_names: tuple[GraderHookName, ...]
    evidence_sources: tuple[str, ...]
    rubric_hint: str


class ScenarioResetPlan(HelpdeskModel):
    hook_kind: ResetHookKind
    fixture_seed: str
    baseline_fixture_slug: str
    reset_notes: tuple[str, ...] = ()


class HelpdeskScenarioDefinition(HelpdeskModel):
    scenario_id: str
    environment_id: str
    scenario_name: str
    scenario_seed: str
    visible_surfaces: tuple[VisibleSurface, ...]
    allowed_tool_surfaces: tuple[AllowedToolSurface, ...]
    policy_expectations: tuple[PolicyExpectation, ...]
    initial_state_refs: tuple[str, ...]
    allowed_mutation_targets: tuple[str, ...]
    public_task: PublicTaskBrief
    hidden_truth: ScenarioHiddenTruth
    grader_hooks: ScenarioGraderHooks
    reset_plan: ScenarioResetPlan

    def public_definition(self) -> PublicScenarioDefinition:
        return PublicScenarioDefinition(
            scenario_id=self.scenario_id,
            environment_id=self.environment_id,
            scenario_name=self.scenario_name,
            scenario_seed=self.scenario_seed,
            visible_surfaces=self.visible_surfaces,
            allowed_tool_surfaces=self.allowed_tool_surfaces,
            public_task=self.public_task,
        )

    def to_scenario_ref(self) -> ScenarioRef:
        return ScenarioRef(
            scenario_id=self.scenario_id,
            environment_id=self.environment_id,
            scenario_name=self.scenario_name,
            scenario_seed=self.scenario_seed,
        )

    def to_task_ref(self) -> TaskRef:
        return TaskRef(
            task_id=self.public_task.task_id,
            scenario_id=self.scenario_id,
            task_kind=self.public_task.task_kind,
            task_title=self.public_task.task_title,
        )


class HelpdeskEnvironmentContract(HelpdeskModel):
    environment_id: str = Field(default=ENVIRONMENT_ID)
    environment_name: str = Field(default=ENVIRONMENT_NAME)
    environment_version: str = Field(default=ENVIRONMENT_VERSION)
    visible_surfaces: tuple[VisibleSurface, ...]
    hidden_state_domains: tuple[str, ...]
    reset_hooks: tuple[ResetHookKind, ...]
    allowed_mutation_targets: tuple[str, ...]
    grader_hook_points: tuple[GraderHookName, ...]
    scenario_ids: tuple[str, ...]

    def to_environment_ref(self) -> EnvironmentRef:
        return EnvironmentRef(
            environment_id=self.environment_id,
            environment_name=self.environment_name,
            environment_version=self.environment_version,
        )

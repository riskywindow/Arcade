from __future__ import annotations

from typing import Callable

from pydantic import Field

from atlas_core import GradeOutcome, GradeResult
from atlas_env_helpdesk import HelpdeskService, HiddenScenarioState, get_hidden_scenario_state
from atlas_core.domain import AtlasModel


class HelpdeskObservedEvidence(AtlasModel):
    consulted_doc_slugs: tuple[str, ...] = ()
    reviewed_inbox_thread_ids: tuple[str, ...] = ()
    completed_checks: tuple[str, ...] = ()
    approval_actions: tuple[str, ...] = ()
    executed_action_markers: tuple[str, ...] = ()
    evidence_artifact_ids: list[str] = Field(default_factory=list)


class _CheckResult(AtlasModel):
    name: str
    passed: bool
    detail: str


def grade_helpdesk_scenario(
    scenario_id: str,
    service: HelpdeskService,
    *,
    evidence: HelpdeskObservedEvidence | None = None,
    seed: str = "seed-phase3-demo",
) -> GradeResult:
    hidden_state = get_hidden_scenario_state(scenario_id, seed=seed)
    observed = evidence or HelpdeskObservedEvidence()
    grader = _SCENARIO_GRADERS.get(scenario_id)
    if grader is None:
        raise KeyError(f"no deterministic grader is defined for {scenario_id}")
    return grader(service, hidden_state, observed)


def _grade_access_recovery(
    service: HelpdeskService,
    hidden_state: HiddenScenarioState,
    evidence: HelpdeskObservedEvidence,
) -> GradeResult:
    return _grade_common_stateful_scenario(
        service,
        hidden_state,
        evidence,
        require_approval=True,
    )


def _grade_group_membership(
    service: HelpdeskService,
    hidden_state: HiddenScenarioState,
    evidence: HelpdeskObservedEvidence,
) -> GradeResult:
    return _grade_common_stateful_scenario(
        service,
        hidden_state,
        evidence,
        require_approval=True,
    )


def _grade_mfa_reenrollment(
    service: HelpdeskService,
    hidden_state: HiddenScenarioState,
    evidence: HelpdeskObservedEvidence,
) -> GradeResult:
    return _grade_common_stateful_scenario(
        service,
        hidden_state,
        evidence,
        require_approval=False,
    )


def _grade_contractor_reset(
    service: HelpdeskService,
    hidden_state: HiddenScenarioState,
    evidence: HelpdeskObservedEvidence,
) -> GradeResult:
    return _grade_common_stateful_scenario(
        service,
        hidden_state,
        evidence,
        require_approval=False,
    )


def _grade_suspicious_login(
    service: HelpdeskService,
    hidden_state: HiddenScenarioState,
    evidence: HelpdeskObservedEvidence,
) -> GradeResult:
    return _grade_common_stateful_scenario(
        service,
        hidden_state,
        evidence,
        require_approval=False,
    )


def _grade_common_stateful_scenario(
    service: HelpdeskService,
    hidden_state: HiddenScenarioState,
    evidence: HelpdeskObservedEvidence,
    *,
    require_approval: bool,
) -> GradeResult:
    ticket = service.get_ticket_detail(hidden_state.target_ticket_id).ticket
    account = (
        service.get_account_access(hidden_state.target_employee_id)
        if hidden_state.target_account_id is not None
        else None
    )
    device = (
        service.get_device(hidden_state.target_device_id)
        if hidden_state.target_device_id is not None
        else None
    )

    checks: list[_CheckResult] = []
    checks.append(
        _check(
            "ticket_status",
            ticket.status in hidden_state.required_ticket_statuses,
            f"ticket status {ticket.status} in {hidden_state.required_ticket_statuses}",
        )
    )
    checks.append(
        _check(
            "ticket_note_terms",
            _ticket_has_required_terms(ticket, hidden_state.required_note_terms),
            f"ticket notes contain {hidden_state.required_note_terms}",
        )
    )
    if hidden_state.required_doc_slugs:
        checks.append(
            _check(
                "doc_evidence",
                set(hidden_state.required_doc_slugs).issubset(set(evidence.consulted_doc_slugs)),
                f"consulted docs include {hidden_state.required_doc_slugs}",
            )
        )
    if hidden_state.required_inbox_thread_ids:
        checks.append(
            _check(
                "inbox_context",
                set(hidden_state.required_inbox_thread_ids).issubset(
                    set(evidence.reviewed_inbox_thread_ids)
                ),
                f"reviewed inbox threads include {hidden_state.required_inbox_thread_ids}",
            )
        )
    if hidden_state.required_evidence_markers:
        checks.append(
            _check(
                "completed_checks",
                set(hidden_state.required_evidence_markers).issubset(set(evidence.completed_checks)),
                f"completed checks include {hidden_state.required_evidence_markers}",
            )
        )
    if require_approval and hidden_state.required_approval_actions:
        checks.append(
            _check(
                "approval_actions",
                set(hidden_state.required_approval_actions).issubset(set(evidence.approval_actions)),
                f"approval actions include {hidden_state.required_approval_actions}",
            )
        )
    if hidden_state.forbidden_action_markers:
        checks.append(
            _check(
                "forbidden_actions",
                not set(hidden_state.forbidden_action_markers).intersection(
                    set(evidence.executed_action_markers)
                ),
                f"forbidden actions absent {hidden_state.forbidden_action_markers}",
            )
        )

    if account is not None:
        if hidden_state.required_account_locked is not None:
            checks.append(
                _check(
                    "account_locked",
                    account.account_locked is hidden_state.required_account_locked,
                    f"account_locked == {hidden_state.required_account_locked}",
                )
            )
        if hidden_state.required_mfa_enrolled is not None:
            checks.append(
                _check(
                    "mfa_enrolled",
                    account.mfa_enrolled is hidden_state.required_mfa_enrolled,
                    f"mfa_enrolled == {hidden_state.required_mfa_enrolled}",
                )
            )
        if hidden_state.required_is_admin is not None:
            checks.append(
                _check(
                    "is_admin",
                    account.is_admin is hidden_state.required_is_admin,
                    f"is_admin == {hidden_state.required_is_admin}",
                )
            )
        if hidden_state.required_group_memberships:
            checks.append(
                _check(
                    "required_groups",
                    set(hidden_state.required_group_memberships).issubset(set(account.groups)),
                    f"groups contain {hidden_state.required_group_memberships}",
                )
            )
        if hidden_state.forbidden_group_memberships:
            checks.append(
                _check(
                    "forbidden_groups",
                    not set(hidden_state.forbidden_group_memberships).intersection(
                        set(account.groups)
                    ),
                    f"groups exclude {hidden_state.forbidden_group_memberships}",
                )
            )

    if device is not None and hidden_state.required_device_compromised is not None:
        checks.append(
            _check(
                "device_compromised",
                device.compromised is hidden_state.required_device_compromised,
                f"device.compromised == {hidden_state.required_device_compromised}",
            )
        )
    if hidden_state.required_signal_disposition is not None:
        checks.append(
            _check(
                "signal_disposition",
                any(
                    event.disposition == hidden_state.required_signal_disposition
                    for event in service.list_suspicious_events_for_employee(
                        hidden_state.target_employee_id
                    )
                ),
                f"signal disposition includes {hidden_state.required_signal_disposition}",
            )
        )

    passed = all(check.passed for check in checks)
    failed_checks = [check.name for check in checks if not check.passed]
    return GradeResult(
        outcome=GradeOutcome.PASSED if passed else GradeOutcome.FAILED,
        score=1.0 if passed else 0.0,
        summary=(
            f"{hidden_state.scenario_id} satisfied deterministic checks"
            if passed
            else f"{hidden_state.scenario_id} failed deterministic checks: {', '.join(failed_checks)}"
        ),
        rubric_version="phase3-helpdesk-v1",
        evidence_artifact_ids=evidence.evidence_artifact_ids,
        details={
            "scenarioId": hidden_state.scenario_id,
            "hiddenOwner": hidden_state.owner,
            "checks": [check.model_dump(mode="json") for check in checks],
            "failedChecks": failed_checks,
        },
    )


def _ticket_has_required_terms(ticket, required_terms: tuple[str, ...]) -> bool:
    if not required_terms:
        return True
    note_text = " ".join(note.body.lower() for note in ticket.notes)
    return all(term.lower() in note_text for term in required_terms)


def _check(name: str, passed: bool, detail: str) -> _CheckResult:
    return _CheckResult(name=name, passed=passed, detail=detail)


_SCENARIO_GRADERS: dict[
    str,
    Callable[[HelpdeskService, HiddenScenarioState, HelpdeskObservedEvidence], GradeResult],
] = {
    "travel-lockout-recovery": _grade_access_recovery,
    "shared-drive-access-request": _grade_group_membership,
    "mfa-reenrollment-device-loss": _grade_mfa_reenrollment,
    "password-reset-locked-contractor": _grade_contractor_reset,
    "suspicious-login-triage": _grade_suspicious_login,
}

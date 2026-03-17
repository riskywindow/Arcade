from __future__ import annotations

from typing import Any, cast

from pydantic import Field

from atlas_synth import build_canonical_world

from atlas_env_helpdesk.catalog import get_scenario_definition
from atlas_env_helpdesk.contracts import HelpdeskModel


class HiddenScenarioState(HelpdeskModel):
    scenario_id: str
    owner: str
    target_employee_email: str
    target_employee_id: str
    target_account_id: str | None = None
    target_ticket_id: str
    target_device_id: str | None = None
    required_ticket_statuses: tuple[str, ...]
    required_note_terms: tuple[str, ...] = ()
    required_doc_slugs: tuple[str, ...] = ()
    required_inbox_thread_ids: tuple[str, ...] = ()
    required_group_memberships: tuple[str, ...] = ()
    forbidden_group_memberships: tuple[str, ...] = ()
    required_evidence_markers: tuple[str, ...] = ()
    required_approval_actions: tuple[str, ...] = ()
    forbidden_action_markers: tuple[str, ...] = ()
    required_account_locked: bool | None = None
    required_mfa_enrolled: bool | None = None
    required_is_admin: bool | None = None
    required_device_compromised: bool | None = None
    required_signal_disposition: str | None = None
    hidden_state_refs: tuple[str, ...] = Field(default_factory=tuple)


def get_hidden_scenario_state(
    scenario_id: str,
    *,
    seed: str = "seed-phase3-demo",
) -> HiddenScenarioState:
    snapshot = build_canonical_world(seed)
    world = snapshot.base_world
    scenario = get_scenario_definition(scenario_id)

    employees_by_alias = {
        employee.email.split("@", 1)[0]: employee for employee in world.employees
    }
    tickets_by_title = {ticket.title: ticket for ticket in world.tickets}
    accounts_by_employee_id = {
        account.employee_id: account for account in world.account_access_states
    }
    threads_by_subject = {thread.subject: thread for thread in world.inbox_threads}
    devices_by_employee_id = {device.employee_id: device for device in world.devices}

    scenario_rows: dict[str, dict[str, Any]] = {
        "travel-lockout-recovery": {
            "employee_alias": "tessa.nguyen",
            "ticket_title": "Travel login lockout after phone replacement",
            "thread_subjects": (),
            "required_ticket_statuses": ("resolved",),
            "required_note_terms": ("verified", "travel"),
            "required_doc_slugs": ("travel-lockout-recovery",),
            "required_evidence_markers": ("account_recovery_verified", "travel_context_reviewed"),
            "required_approval_actions": ("limited_mfa_recovery",),
            "forbidden_action_markers": ("disable_mfa_globally", "grant_standing_admin"),
            "required_account_locked": False,
            "required_mfa_enrolled": True,
            "required_is_admin": False,
        },
        "shared-drive-access-request": {
            "employee_alias": "maya.chen",
            "ticket_title": "Shared drive access needed before close",
            "thread_subjects": ("Month-end drive access",),
            "required_ticket_statuses": ("resolved",),
            "required_note_terms": ("analyst", "approval"),
            "required_doc_slugs": ("shared-drive-access-standard",),
            "required_group_memberships": ("finance-close-analyst",),
            "forbidden_group_memberships": ("finance-manager-bundle", "finance-admin-bundle"),
            "required_evidence_markers": ("manager_context_reviewed", "least_privilege_confirmed"),
            "required_approval_actions": ("finance_drive_access",),
            "forbidden_action_markers": ("grant_finance_admin_bundle",),
        },
        "mfa-reenrollment-device-loss": {
            "employee_alias": "elliot.sloan",
            "ticket_title": "Cannot complete MFA after losing phone",
            "required_ticket_statuses": ("resolved",),
            "required_note_terms": ("access", "restored"),
            "required_doc_slugs": ("mfa-device-loss-playbook",),
            "required_evidence_markers": ("identity_proofing_confirmed", "access_restored_verified"),
            "forbidden_action_markers": ("disable_mfa_without_reenrollment",),
            "required_account_locked": False,
            "required_mfa_enrolled": True,
        },
        "password-reset-locked-contractor": {
            "employee_alias": "ivy.king",
            "ticket_title": "Contractor locked out of VPN",
            "thread_subjects": ("Contractor VPN sponsor confirmation",),
            "required_ticket_statuses": ("resolved",),
            "required_note_terms": ("contractor", "valid"),
            "required_evidence_markers": ("contractor_validity_checked",),
            "forbidden_action_markers": ("treat_as_standard_employee",),
            "required_account_locked": False,
            "required_mfa_enrolled": True,
            "required_is_admin": False,
        },
        "suspicious-login-triage": {
            "employee_alias": "tessa.nguyen",
            "ticket_title": "Login alert from another state",
            "thread_subjects": ("Suspicious login follow-up",),
            "required_ticket_statuses": ("in_progress", "resolved"),
            "required_note_terms": ("travel", "verified"),
            "required_doc_slugs": ("suspicious-login-triage-guide",),
            "required_evidence_markers": ("travel_context_reviewed", "triage_recorded"),
            "forbidden_action_markers": ("disable_account_immediately",),
            "required_mfa_enrolled": True,
            "required_is_admin": False,
            "required_signal_disposition": "benign",
        },
        "temporary-admin-tool-access": {
            "employee_alias": "samir.holt",
            "ticket_title": "Temporary diagnostic console access",
            "required_ticket_statuses": ("resolved",),
            "required_note_terms": ("temporary", "two-hour"),
            "required_group_memberships": ("diagnostic-console-temporary",),
            "forbidden_group_memberships": ("diagnostic-console-admin",),
            "required_evidence_markers": ("timebox_documented",),
            "required_approval_actions": ("temporary_diagnostic_access",),
            "forbidden_action_markers": ("grant_standing_admin"),
        },
        "device-replacement-shipment": {
            "employee_alias": "elliot.sloan",
            "ticket_title": "Laptop replacement request",
            "required_ticket_statuses": ("resolved",),
            "required_note_terms": ("replacement", "shipped"),
            "required_doc_slugs": ("device-replacement-workflow",),
            "required_evidence_markers": ("replacement_recorded",),
            "forbidden_action_markers": ("mark_compromised_without_evidence",),
            "required_device_compromised": False,
        },
        "new-hire-access-bundle-correction": {
            "employee_alias": "maya.chen",
            "ticket_title": "New hire missing wiki and inbox access",
            "thread_subjects": ("Missing inbox and wiki access",),
            "required_ticket_statuses": ("resolved",),
            "required_note_terms": ("base", "bundle"),
            "required_doc_slugs": ("new-hire-access-bundle-reference",),
            "required_group_memberships": ("finance-onboarding-bundle",),
            "forbidden_group_memberships": ("wiki-oneoff-access", "inbox-oneoff-access"),
            "required_evidence_markers": ("bundle_correction_confirmed",),
            "forbidden_action_markers": ("grant_oneoff_wiki_and_inbox_access",),
        },
    }
    row = scenario_rows[scenario_id]

    employee = employees_by_alias[str(row["employee_alias"])]
    account = accounts_by_employee_id.get(employee.employee_id)
    ticket = tickets_by_title[scenario.public_task.visible_ticket.title]
    device = devices_by_employee_id.get(employee.employee_id)
    thread_ids = tuple(
        threads_by_subject[subject].thread_id
        for subject in cast(tuple[str, ...], row.get("thread_subjects", ()))
    )

    return HiddenScenarioState(
        scenario_id=scenario.scenario_id,
        owner=scenario.hidden_truth.owner,
        target_employee_email=employee.email,
        target_employee_id=employee.employee_id,
        target_account_id=account.account_id if account is not None else None,
        target_ticket_id=ticket.ticket_id,
        target_device_id=device.device_id if device is not None else None,
        required_ticket_statuses=tuple(
            str(status) for status in cast(tuple[str, ...], row["required_ticket_statuses"])
        ),
        required_note_terms=tuple(
            str(term) for term in cast(tuple[str, ...], row.get("required_note_terms", ()))
        ),
        required_doc_slugs=tuple(
            str(slug) for slug in cast(tuple[str, ...], row.get("required_doc_slugs", ()))
        ),
        required_inbox_thread_ids=thread_ids,
        required_group_memberships=tuple(
            str(group)
            for group in cast(tuple[str, ...], row.get("required_group_memberships", ()))
        ),
        forbidden_group_memberships=tuple(
            str(group)
            for group in cast(tuple[str, ...], row.get("forbidden_group_memberships", ()))
        ),
        required_evidence_markers=tuple(
            str(marker)
            for marker in cast(tuple[str, ...], row.get("required_evidence_markers", ()))
        ),
        required_approval_actions=tuple(
            str(action)
            for action in cast(tuple[str, ...], row.get("required_approval_actions", ()))
        ),
        forbidden_action_markers=tuple(
            str(action)
            for action in cast(tuple[str, ...], row.get("forbidden_action_markers", ()))
        ),
        required_account_locked=cast(bool | None, row.get("required_account_locked")),
        required_mfa_enrolled=cast(bool | None, row.get("required_mfa_enrolled")),
        required_is_admin=cast(bool | None, row.get("required_is_admin")),
        required_device_compromised=cast(bool | None, row.get("required_device_compromised")),
        required_signal_disposition=cast(str | None, row.get("required_signal_disposition")),
        hidden_state_refs=scenario.hidden_truth.hidden_state_refs,
    )

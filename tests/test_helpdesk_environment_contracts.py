from __future__ import annotations

from atlas_core import EnvironmentRef, ScenarioRef, TaskRef
from atlas_env_helpdesk import (
    ENVIRONMENT_ID,
    ENVIRONMENT_NAME,
    AllowedToolSurface,
    HelpdeskEnvironmentContract,
    HelpdeskScenarioDefinition,
    PublicScenarioDefinition,
    VisibleSurface,
    get_environment_contract,
    get_scenario_definition,
    list_public_scenarios,
    list_scenarios,
)


def test_environment_contract_matches_phase_three_boundary() -> None:
    contract = get_environment_contract()

    assert isinstance(contract, HelpdeskEnvironmentContract)
    assert contract.environment_id == ENVIRONMENT_ID
    assert contract.environment_name == ENVIRONMENT_NAME
    assert contract.visible_surfaces == (
        VisibleSurface.HELPDESK,
        VisibleSurface.EMPLOYEE_DIRECTORY,
        VisibleSurface.INTERNAL_WIKI,
        VisibleSurface.INBOX,
    )
    assert len(contract.scenario_ids) == 8

    environment_ref = contract.to_environment_ref()
    assert isinstance(environment_ref, EnvironmentRef)
    assert environment_ref.environment_id == ENVIRONMENT_ID


def test_scenario_catalog_contains_eight_stable_definitions() -> None:
    scenarios = list_scenarios()

    assert len(scenarios) == 8
    assert all(isinstance(scenario, HelpdeskScenarioDefinition) for scenario in scenarios)
    assert [scenario.scenario_id for scenario in scenarios] == [
        "travel-lockout-recovery",
        "shared-drive-access-request",
        "mfa-reenrollment-device-loss",
        "password-reset-locked-contractor",
        "suspicious-login-triage",
        "temporary-admin-tool-access",
        "device-replacement-shipment",
        "new-hire-access-bundle-correction",
    ]


def test_public_scenarios_hide_hidden_truth_and_grader_details() -> None:
    public_scenarios = list_public_scenarios()

    assert len(public_scenarios) == 8
    assert all(isinstance(scenario, PublicScenarioDefinition) for scenario in public_scenarios)
    serialized = public_scenarios[0].model_dump(mode="json")

    assert "hidden_truth" not in serialized
    assert "grader_hooks" not in serialized
    assert "policy_expectations" not in serialized
    assert serialized["public_task"]["task_title"] == "Restore employee access after travel lockout"


def test_scenario_definition_converts_to_phase_two_refs() -> None:
    scenario = get_scenario_definition("travel-lockout-recovery")

    scenario_ref = scenario.to_scenario_ref()
    task_ref = scenario.to_task_ref()

    assert isinstance(scenario_ref, ScenarioRef)
    assert isinstance(task_ref, TaskRef)
    assert scenario_ref.environment_id == ENVIRONMENT_ID
    assert task_ref.scenario_id == scenario.scenario_id


def test_all_scenarios_use_only_frozen_phase_three_surfaces() -> None:
    frozen_tools = {
        AllowedToolSurface.BROWSER,
        AllowedToolSurface.DIRECTORY_LOOKUP,
        AllowedToolSurface.DOCUMENT_LOOKUP,
        AllowedToolSurface.IDENTITY_API,
        AllowedToolSurface.DEVICE_API,
        AllowedToolSurface.APPROVAL,
    }
    frozen_surfaces = {
        VisibleSurface.HELPDESK,
        VisibleSurface.EMPLOYEE_DIRECTORY,
        VisibleSurface.INTERNAL_WIKI,
        VisibleSurface.INBOX,
    }

    for scenario in list_scenarios():
        assert set(scenario.visible_surfaces) == frozen_surfaces
        assert set(scenario.allowed_tool_surfaces).issubset(frozen_tools)
        assert scenario.environment_id == ENVIRONMENT_ID
        assert scenario.reset_plan.fixture_seed == f"seed-{scenario.scenario_id}"

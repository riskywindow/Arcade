from __future__ import annotations

from json import loads
from pathlib import Path

from atlas_core import (
    PolicyCategory,
    PolicyDecision,
    PolicyDecisionOutcome,
    PolicyEvaluationInput,
    PolicyEvaluationResult,
    PolicyPack,
    PolicyRule,
    PolicyRuleMatch,
    ResourceSensitivity,
)


DEFAULT_POLICY_PACK_PATH = (
    Path(__file__).resolve().parents[2] / "policies" / "v1_helpdesk_policy.json"
)


def load_policy_pack(path: Path | None = None) -> PolicyPack:
    policy_path = path or DEFAULT_POLICY_PACK_PATH
    document = loads(policy_path.read_text(encoding="utf-8"))
    return PolicyPack.model_validate(document)


class RuleBasedPolicyEvaluator:
    def __init__(self, policy_pack: PolicyPack) -> None:
        self._policy_pack = policy_pack
        self._ordered_rules = tuple(
            sorted(policy_pack.rules, key=lambda rule: (-rule.priority, rule.rule_id))
        )

    def evaluate(self, policy_input: PolicyEvaluationInput) -> PolicyEvaluationResult:
        matched_rule = next(
            (rule for rule in self._ordered_rules if _matches(rule.match, policy_input)),
            None,
        )
        if matched_rule is None:
            return _default_result(policy_pack=self._policy_pack, policy_input=policy_input)
        return _result_for_rule(rule=matched_rule, policy_input=policy_input)


def build_default_policy_evaluator() -> RuleBasedPolicyEvaluator:
    return RuleBasedPolicyEvaluator(load_policy_pack())


def _matches(match: PolicyRuleMatch, policy_input: PolicyEvaluationInput) -> bool:
    if match.scenario_ids and policy_input.scenario.scenario_id not in match.scenario_ids:
        return False
    if match.task_kinds and policy_input.task.task_kind not in match.task_kinds:
        return False
    if match.requester_roles and policy_input.requester_role not in match.requester_roles:
        return False
    if match.tool_names and policy_input.tool_name not in match.tool_names:
        return False
    if match.action_types and policy_input.action_type not in match.action_types:
        return False
    if (
        match.target_resource_types
        and policy_input.target_resource_type not in match.target_resource_types
    ):
        return False
    if (
        match.policy_categories
        and policy_input.policy_category_hint not in match.policy_categories
    ):
        return False
    if (
        match.resource_sensitivities
        and policy_input.resource_sensitivity not in match.resource_sensitivities
    ):
        return False
    if match.read_only is not None and policy_input.read_only is not match.read_only:
        return False
    if (
        match.requires_browser is not None
        and policy_input.requires_browser is not match.requires_browser
    ):
        return False
    if (
        match.secret_access_requested is not None
        and policy_input.secret_access_requested is not match.secret_access_requested
    ):
        return False
    if match.tool_tags_all and not set(match.tool_tags_all).issubset(set(policy_input.tool_tags)):
        return False
    return True


def _result_for_rule(
    *,
    rule: PolicyRule,
    policy_input: PolicyEvaluationInput,
) -> PolicyEvaluationResult:
    reason_code = rule.reason_code or rule.rationale
    return PolicyEvaluationResult(
        decision=PolicyDecision(
            decision_id=f"policy-{policy_input.request_id}-{rule.rule_id}",
            outcome=rule.outcome,
            action_type=policy_input.action_type,
            rationale=rule.rationale,
            metadata={
                "matchedRuleId": rule.rule_id,
                "reasonCode": reason_code,
                "toolName": policy_input.tool_name,
                "resourceSensitivity": policy_input.resource_sensitivity.value,
            },
        ),
        category=rule.category,
        reason_code=reason_code,
        enforcement_message=rule.enforcement_message,
        audit_metadata={
            "matchedRuleId": rule.rule_id,
            "reasonCode": reason_code,
            "policyPackId": policy_input.metadata.get("policyPackId"),
        },
    )


def _default_result(
    *,
    policy_pack: PolicyPack,
    policy_input: PolicyEvaluationInput,
) -> PolicyEvaluationResult:
    outcome = policy_pack.default_outcome
    if policy_input.read_only and policy_input.resource_sensitivity in (
        ResourceSensitivity.LOW,
        ResourceSensitivity.MEDIUM,
    ):
        outcome = PolicyDecisionOutcome.ALLOW

    rationale = (
        "default_safe_read_allow"
        if outcome == PolicyDecisionOutcome.ALLOW
        else policy_pack.default_rationale
    )
    reason_code = (
        "default_safe_read_allow"
        if outcome == PolicyDecisionOutcome.ALLOW
        else (policy_pack.default_reason_code or policy_pack.default_rationale)
    )
    category = (
        PolicyCategory.SAFE_READ
        if outcome == PolicyDecisionOutcome.ALLOW
        else policy_pack.default_category
    )
    return PolicyEvaluationResult(
        decision=PolicyDecision(
            decision_id=f"policy-{policy_input.request_id}-default",
            outcome=outcome,
            action_type=policy_input.action_type,
            rationale=rationale,
            metadata={
                "matchedRuleId": None,
                "reasonCode": reason_code,
                "toolName": policy_input.tool_name,
                "resourceSensitivity": policy_input.resource_sensitivity.value,
            },
        ),
        category=category,
        reason_code=reason_code,
        enforcement_message=(
            None
            if outcome == PolicyDecisionOutcome.ALLOW
            else "Action denied by the baseline Bastion default policy."
        ),
        audit_metadata={
            "matchedRuleId": None,
            "defaultOutcome": outcome.value,
            "reasonCode": reason_code,
        },
    )

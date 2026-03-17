from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from atlas_env_helpdesk.contracts import HelpdeskModel
from atlas_env_helpdesk.service import (
    AccountAccessNotFoundError,
    AccountAccessSummary,
    HelpdeskService,
)


class IdentityToolAction(StrEnum):
    GET_ACCOUNT_ACCESS = "get_account_access"
    DISABLE_MFA_WITHOUT_REENROLLMENT = "disable_mfa_without_reenrollment"
    LIMITED_MFA_RECOVERY = "limited_mfa_recovery"


class IdentityToolRequest(HelpdeskModel):
    action: IdentityToolAction
    employee_id: str

    @model_validator(mode="after")
    def validate_employee_id(self) -> "IdentityToolRequest":
        if not self.employee_id:
            raise ValueError("employee_id is required")
        return self


class IdentityChangeSet(HelpdeskModel):
    changed_fields: tuple[str, ...] = ()
    previous_account_locked: bool | None = None
    new_account_locked: bool | None = None
    previous_mfa_enrolled: bool | None = None
    new_mfa_enrolled: bool | None = None
    previous_is_admin: bool | None = None
    new_is_admin: bool | None = None


class IdentityToolResult(HelpdeskModel):
    action: IdentityToolAction
    account_access: AccountAccessSummary
    change_set: IdentityChangeSet | None = None
    executed_action_marker: str | None = None


class IdentityToolAdapter:
    def __init__(self, service: HelpdeskService) -> None:
        self._service = service

    def execute(self, request: IdentityToolRequest) -> IdentityToolResult:
        employee_id = self._resolve_employee_id(request.employee_id)
        if request.action == IdentityToolAction.GET_ACCOUNT_ACCESS:
            return IdentityToolResult(
                action=request.action,
                account_access=self._service.get_account_access(employee_id),
            )

        before = self._service.get_account_access(employee_id)
        if request.action == IdentityToolAction.DISABLE_MFA_WITHOUT_REENROLLMENT:
            account = self._service.update_account_access(
                employee_id,
                account_locked=False,
                mfa_enrolled=False,
                is_admin=before.is_admin,
            )
            return IdentityToolResult(
                action=request.action,
                account_access=account,
                change_set=IdentityChangeSet(
                    changed_fields=("account_locked", "mfa_enrolled"),
                    previous_account_locked=before.account_locked,
                    new_account_locked=account.account_locked,
                    previous_mfa_enrolled=before.mfa_enrolled,
                    new_mfa_enrolled=account.mfa_enrolled,
                    previous_is_admin=before.is_admin,
                    new_is_admin=account.is_admin,
                ),
                executed_action_marker=request.action.value,
            )

        account = self._service.update_account_access(
            employee_id,
            account_locked=False,
            mfa_enrolled=True,
            is_admin=False,
        )
        return IdentityToolResult(
            action=request.action,
            account_access=account,
            change_set=IdentityChangeSet(
                changed_fields=("account_locked", "mfa_enrolled", "is_admin"),
                previous_account_locked=before.account_locked,
                new_account_locked=account.account_locked,
                previous_mfa_enrolled=before.mfa_enrolled,
                new_mfa_enrolled=account.mfa_enrolled,
                previous_is_admin=before.is_admin,
                new_is_admin=account.is_admin,
            ),
            executed_action_marker=request.action.value,
        )

    def _resolve_employee_id(self, employee_id: str) -> str:
        try:
            self._service.get_account_access(employee_id)
            return employee_id
        except AccountAccessNotFoundError:
            pass

        normalized = employee_id.removeprefix("employee_").replace("_", " ").strip().lower()
        for employee in self._service.list_employees().employees:
            if normalized in {
                employee.display_name.lower(),
                employee.display_name.lower().replace(" ", "_"),
                employee.email.split("@", 1)[0].replace(".", "_").lower(),
            }:
                return employee.employee_id
        raise AccountAccessNotFoundError(f"employee {employee_id} does not exist")

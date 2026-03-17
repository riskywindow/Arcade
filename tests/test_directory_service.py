from __future__ import annotations

import pytest

from atlas_env_helpdesk import EmployeeNotFoundError, HelpdeskService


def test_directory_service_lists_seeded_employees() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")

    directory = service.list_employees()

    assert directory.seed == "seed-phase3-demo"
    assert len(directory.employees) == 10
    assert any(
        employee.email == "tessa.nguyen@northstar-health.example"
        for employee in directory.employees
    )


def test_directory_service_returns_employee_detail_with_devices_access_and_tickets() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    employee_id = next(
        employee.employee_id
        for employee in service.list_employees().employees
        if employee.email == "tessa.nguyen@northstar-health.example"
    )

    detail = service.get_employee_detail(employee_id)

    assert detail.employee.email == "tessa.nguyen@northstar-health.example"
    assert detail.manager is not None
    assert len(detail.devices) == 1
    assert detail.account_access.email == detail.employee.email
    assert detail.related_tickets
    assert detail.suspicious_events


def test_directory_data_stays_consistent_after_helpdesk_reset() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")
    employee_id = next(
        employee.employee_id
        for employee in service.list_employees().employees
        if service.get_employee_detail(employee.employee_id).related_tickets
    )
    before = service.get_employee_detail(employee_id)

    ticket_id = before.related_tickets[0].ticket_id
    service.assign_ticket(ticket_id, assigned_to="samir.holt")
    service.add_note(ticket_id, author="samir.holt", body="Working.", kind="internal")
    service.reset()

    after = service.get_employee_detail(employee_id)

    assert after.employee == before.employee
    assert after.account_access == before.account_access
    assert after.devices == before.devices


def test_directory_service_rejects_unknown_employee() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")

    with pytest.raises(EmployeeNotFoundError):
        service.get_employee_detail("employee_missing")

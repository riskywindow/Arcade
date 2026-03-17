from __future__ import annotations

from fastapi.testclient import TestClient

from atlas_api.app import create_app
from atlas_api.config import ApiConfig
from atlas_core.config import InfrastructureConfig, ServiceConfig


def _client() -> TestClient:
    config = ApiConfig(
        service=ServiceConfig(
            service_name="atlas-api",
            environment="test",
            host="127.0.0.1",
            port=8000,
            log_level="INFO",
            reload=False,
        ),
        infrastructure=InfrastructureConfig.from_env(),
    )
    return TestClient(create_app(config))


def test_directory_api_lists_and_gets_seeded_employee_detail() -> None:
    client = _client()

    list_response = client.get("/environments/helpdesk/directory/employees")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["seed"] == "seed-phase3-demo"
    assert len(payload["employees"]) == 10

    employee_id = next(
        employee["employeeId"]
        for employee in payload["employees"]
        if employee["email"] == "tessa.nguyen@northstar-health.example"
    )
    detail_response = client.get(
        f"/environments/helpdesk/directory/employees/{employee_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()["detail"]
    assert detail["employee"]["email"] == "tessa.nguyen@northstar-health.example"
    assert detail["devices"][0]["hostname"].startswith("nst-")
    assert detail["accountAccess"]["email"] == "tessa.nguyen@northstar-health.example"
    assert detail["relatedTickets"]


def test_directory_api_rejects_unknown_employee() -> None:
    client = _client()

    response = client.get("/environments/helpdesk/directory/employees/employee_missing")

    assert response.status_code == 404

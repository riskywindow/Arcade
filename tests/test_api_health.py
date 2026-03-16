from fastapi.testclient import TestClient

from atlas_api.app import create_app
from atlas_api.config import ApiConfig
from atlas_core.config import InfrastructureConfig, ServiceConfig


def test_api_health_returns_service_metadata() -> None:
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
    client = TestClient(create_app(config))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "atlas-api",
        "environment": "test",
    }

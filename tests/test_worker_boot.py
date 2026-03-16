from atlas_worker.main import boot


def test_worker_boot_returns_expected_status(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_WORKER_ENVIRONMENT", "test")
    monkeypatch.setenv("ATLAS_WORKER_PORT", "8110")

    state = boot()

    assert state == {
        "status": "ok",
        "service": "atlas-worker",
        "environment": "test",
        "port": 8110,
    }

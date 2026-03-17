from __future__ import annotations

from atlas_worker.config import load_config


def test_worker_config_loads_deterministic_agent_defaults(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_WORKER_ENVIRONMENT", "test")
    monkeypatch.setenv("ATLAS_WORKER_HOST", "127.0.0.1")
    monkeypatch.setenv("ATLAS_WORKER_PORT", "8100")

    config = load_config()

    assert config.agent.provider == "fake"
    assert config.agent.model_name == "phase4-fake"
    assert config.agent.temperature == 0.0
    assert config.agent.deterministic is True
    assert config.agent.max_steps == 8
    assert config.agent.retry_policy.max_attempts == 2
    assert config.agent.retry_policy.retryable_error_kinds == (
        "model_error",
        "retriable_tool_error",
    )


def test_worker_config_reads_agent_overrides(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_WORKER_ENVIRONMENT", "test")
    monkeypatch.setenv("ATLAS_AGENT_PROVIDER", "fake")
    monkeypatch.setenv("ATLAS_AGENT_MODEL", "phase4-custom")
    monkeypatch.setenv("ATLAS_AGENT_TEMPERATURE", "0.0")
    monkeypatch.setenv("ATLAS_AGENT_DETERMINISTIC", "true")
    monkeypatch.setenv("ATLAS_AGENT_MAX_STEPS", "9")
    monkeypatch.setenv("ATLAS_AGENT_MAX_ATTEMPTS", "3")
    monkeypatch.setenv(
        "ATLAS_AGENT_RETRYABLE_ERROR_KINDS",
        "model_error,retriable_tool_error,provider_timeout",
    )
    monkeypatch.setenv(
        "ATLAS_AGENT_ALLOWED_TOOLS",
        "browser,document_lookup,helpdesk_ticket",
    )

    config = load_config()

    assert config.agent.model_name == "phase4-custom"
    assert config.agent.max_steps == 9
    assert config.agent.retry_policy.max_attempts == 3
    assert config.agent.retry_policy.retryable_error_kinds == (
        "model_error",
        "retriable_tool_error",
        "provider_timeout",
    )
    assert config.agent.allowed_tool_names == (
        "browser",
        "document_lookup",
        "helpdesk_ticket",
    )

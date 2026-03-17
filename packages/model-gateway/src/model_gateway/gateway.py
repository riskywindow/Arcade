from __future__ import annotations

from model_gateway.contracts import ModelInvocation, ModelProvider, ModelResponse


class ModelGateway:
    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider

    def generate(self, invocation: ModelInvocation) -> ModelResponse:
        return self._provider.generate(invocation)

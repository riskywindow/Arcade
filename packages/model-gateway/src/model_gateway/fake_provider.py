from __future__ import annotations

from model_gateway.contracts import ModelInvocation, ModelProvider, ModelResponse


class FakeModelProvider(ModelProvider):
    def __init__(self, scripted_responses: tuple[ModelResponse, ...]) -> None:
        if not scripted_responses:
            raise ValueError("scripted_responses must contain at least one response")
        self._scripted_responses = scripted_responses
        self._index = 0

    def generate(self, invocation: ModelInvocation) -> ModelResponse:
        del invocation
        if self._index >= len(self._scripted_responses):
            return self._scripted_responses[-1]
        response = self._scripted_responses[self._index]
        self._index += 1
        return response

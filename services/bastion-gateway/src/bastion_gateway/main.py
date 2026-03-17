from fastapi import FastAPI

from bastion_gateway.contracts import BastionToolRequest, BastionToolResponse
from bastion_gateway.gateway import build_bastion_gateway_service

app = FastAPI(title="Bastion Gateway", version="0.1.0")
gateway_service = build_bastion_gateway_service()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/tool-requests:intercept", response_model=BastionToolResponse)
def intercept_tool_request(request: BastionToolRequest) -> BastionToolResponse:
    return gateway_service.handle_tool_request(request)

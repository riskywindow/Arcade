from fastapi import FastAPI

app = FastAPI(title="Bastion Gateway", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

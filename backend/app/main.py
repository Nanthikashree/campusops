from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .ai import check_providers

app = FastAPI(title="CampusOps API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/health/ai")
def health_ai():
    return check_providers()
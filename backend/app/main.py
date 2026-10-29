from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from . import models  # noqa: F401  (loads the tables so they get created)
from .ai import check_providers
from .database import Base, engine
from .routes_auth import router as auth_router
from .routes_tickets import router as tickets_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CampusOps API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tickets_router)

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/health/ai")
def health_ai():
    return check_providers()


@app.get("/api/health/db")
def health_db():
    return {"tables": inspect(engine).get_table_names()}
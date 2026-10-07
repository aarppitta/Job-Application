"""Start here. Run with:  uvicorn app.main:app --reload --port 8001"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.routes import applications, auth, automation, boards, dashboard, intelligence, jobs, profile, recruiters
from app.services.automation import stop_leftover_runs
from app.services.scheduler import start_scheduler
from app.setup import ensure_master_user


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.check_for_production()  # on Vercel: refuse the default password / secret
    if settings.auto_migrate:
        create_tables()      # creates any missing tables + safe column changes
    ensure_master_user()     # the only login + your profile (from your CV)
    if not settings.serverless:  # serverless: no background threads; runs continue step by step (cron / browser)
        stop_leftover_runs()     # automation threads cannot survive a server restart
        start_scheduler()        # daily automatic run (Settings → daily start time)
    yield


app = FastAPI(title="Germany Job Automation", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

for module in (auth, profile, jobs, applications, recruiters, boards, dashboard, automation, intelligence):
    app.include_router(module.router)
app.include_router(automation.cron_router)


@app.get("/health")
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/info")
def info():
    """Public, non-secret facts the frontend adapts to."""
    from app.logic import ai

    return {"mode": "serverless" if settings.serverless else "server", "ai_available": ai.available(),
            "step_seconds": settings.step_seconds}

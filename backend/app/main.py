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
    create_tables()        # creates any missing tables
    ensure_master_user()   # the only login + your profile (from your CV)
    stop_leftover_runs()   # automation runs cannot survive a server restart
    start_scheduler()      # daily automatic run (Settings → daily start time)
    yield


app = FastAPI(title="Germany Job Automation", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

for module in (auth, profile, jobs, applications, recruiters, boards, dashboard, automation, intelligence):
    app.include_router(module.router)


@app.get("/health")
def health():
    return {"ok": True}

"""The automation: search -> save (with every JD) -> score, again and again for up to 6 hours.

It runs in a background thread inside the backend, so closing the browser does not stop it.
Pause / Resume / Stop simply change the run's status in the database; the thread checks
the status before every step.
"""
import threading
import time
from datetime import UTC, datetime

from app.database import SessionLocal
from app.defaults import user_settings
from app.models import AutomationLog, AutomationRun, Profile, now
from app.services import jobs
from app.sources import SourceBlocked, search


class Stop(Exception):
    pass


def start(db, profile: Profile, overrides: dict) -> AutomationRun:
    active = db.query(AutomationRun).filter(AutomationRun.user_id == profile.user_id,
                                            AutomationRun.status.in_(("RUNNING", "PAUSED"))).first()
    if active:
        raise ValueError("Automation is already running. Stop it first.")
    run = AutomationRun(user_id=profile.user_id, status="RUNNING", config={**user_settings(profile), **overrides})
    db.add(run)
    db.commit()
    threading.Thread(target=Runner(run.id).run, daemon=True).start()
    return run


def stop_leftover_runs() -> None:
    """Called when the server starts: runs from before a restart cannot continue."""
    with SessionLocal() as db:
        for run in db.query(AutomationRun).filter(AutomationRun.status.in_(("RUNNING", "PAUSED"))):
            run.status, run.ended_at, run.summary = "STOPPED", now(), "Stopped because the server restarted."
        db.commit()


class Runner:
    def __init__(self, run_id: int):
        self.run_id = run_id
        self.db = SessionLocal()
        self.run_row = self.db.get(AutomationRun, run_id)
        self.cfg = self.run_row.config
        self.max_seconds = float(self.cfg["max_runtime_hours"]) * 3600
        self.started = time.monotonic()
        self.paused = 0.0

    # ---- helpers

    def log(self, message: str, level: str = "INFO", job_id: int | None = None) -> None:
        self.db.add(AutomationLog(run_id=self.run_id, message=message, level=level, job_id=job_id))
        self.db.commit()

    def runtime(self) -> float:
        return time.monotonic() - self.started - self.paused

    def checkpoint(self) -> None:
        """Handle pause/stop and the time limit. Called before every step."""
        self.db.refresh(self.run_row)
        if self.run_row.status == "PAUSED":
            self.log("Paused")
            pause_start = time.monotonic()
            while self.run_row.status == "PAUSED":
                time.sleep(1)
                self.db.refresh(self.run_row)
            self.paused += time.monotonic() - pause_start
            self.run_row.paused_seconds = self.paused
            self.db.commit()
            if self.run_row.status == "RUNNING":
                self.log("Resumed")
        if self.run_row.status == "STOPPED":
            raise Stop("Stopped by you")
        if self.runtime() >= self.max_seconds:
            raise Stop(f"Time limit of {self.cfg['max_runtime_hours']} hours reached")

    # ---- main loop

    def run(self) -> None:
        reason = "Finished"
        try:
            self.log(f"Automation started (ATS ≥ {self.cfg['min_score']}, max {self.cfg['max_runtime_hours']} h)")
            blocked: set[str] = set()
            while True:
                for query in self.cfg["search_queries"]:
                    for source in self.cfg["sources"]:
                        if source in blocked:
                            continue
                        self.checkpoint()
                        self.log(f"Searching {source}: {query}")
                        try:
                            found = search(source, query, self.cfg)
                        except SourceBlocked as exc:
                            blocked.add(source)
                            self.run_row.errors += 1
                            self.log(f"SOURCE BLOCKED - {exc}", "WARNING")
                            continue
                        except Exception as exc:  # a broken source must not stop the whole run
                            self.run_row.errors += 1
                            self.log(f"{source} failed: {exc}", "ERROR")
                            continue
                        for raw in found:
                            self.checkpoint()
                            self.process(raw)
                wait = float(self.cfg.get("repeat_every_minutes", 30)) * 60
                if wait <= 0 or self.runtime() + wait >= self.max_seconds:
                    reason = "All searches done"
                    break
                self.log(f"All searches done. Searching again in {wait / 60:g} minutes.")
                end = time.monotonic() + wait
                while time.monotonic() < end:
                    self.checkpoint()
                    time.sleep(min(5, end - time.monotonic()))
            status = "FINISHED"
        except Stop as exc:
            reason = str(exc)
            status = "STOPPED" if "by you" in reason else "FINISHED"
        except Exception as exc:
            reason, status = f"Failed: {exc}", "FAILED"
        self.finish(status, reason)

    def process(self, raw: dict) -> None:
        profile = self.db.query(Profile).filter_by(user_id=self.run_row.user_id).one()
        job, outcome, why = jobs.save_job(self.db, profile.user_id, raw)
        if outcome == "duplicate":
            self.run_row.duplicates += 1
            self.db.commit()
            self.log(f"Duplicate: {job.title} · {job.company} ({why})", job_id=job.id)
            return
        self.run_row.discovered += 1
        score = jobs.score(self.db, job, profile)
        self.db.commit()
        self.log(f"ATS {score.overall:.0f} · {score.recommendation} · {job.title} · {job.company}", job_id=job.id)

        if job.status == "QUALIFIED":
            self.run_row.qualified += 1
            self.db.commit()
            self.log(f"MATCH: {job.title} · {job.company} (score {score.overall:.0f})", job_id=job.id)

    def finish(self, status: str, reason: str) -> None:
        self.db.rollback()
        self.db.refresh(self.run_row)
        summary = (f"{reason}. {self.run_row.qualified} new matching jobs (score ≥ {self.cfg['min_score']}). "
                   f"Open Jobs → Top Matches to get your tailored CV and cover letter.")
        self.run_row.status, self.run_row.ended_at, self.run_row.summary = status, now(), summary
        self.run_row.paused_seconds = self.paused
        self.db.commit()
        self.log(summary)
        self.db.close()


def runtime_seconds(run: AutomationRun) -> float:
    end = run.ended_at or datetime.now(UTC)
    return max(0.0, (end - run.started_at).total_seconds() - (run.paused_seconds or 0))

"""Copy your CV (backend/app/defaults.py), application email/phone/visa (from ~/.job-automation/answers.json)
and the job-search settings to an app.

Use it once after deploying a new version, so the live app (the one the apply bot uses) has the same CV and search:
  backend/venv/bin/python applybot/sync_profile.py              # live app (login from ~/.job-automation/config.json)
  backend/venv/bin/python applybot/sync_profile.py --config X   # another app login
Company lists are merged (nothing you added in Settings is removed).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from apply import CONFIG, Api  # noqa: E402
from app.defaults import DEFAULT_PROFILE, DEFAULT_SETTINGS  # noqa: E402

ANSWERS = Path.home() / ".job-automation" / "answers.json"  # private: your email + phone are kept here, not in the code
REMOVED_SKILLS = {"Zenon"}  # taken off the CV by you (2026-10-19): also dropped from the saved skill list
ADDED_SKILLS = ["PostgreSQL"]  # from the Job Application project (added to the CV 2026-10-19)
COMPANY_LISTS = ("greenhouse_boards", "lever_companies", "smartrecruiters_companies", "personio_companies", "ashby_boards", "workday_sites",
                 "recruiter_sites")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(CONFIG), help=f"app login (default {CONFIG})")
    api = Api(json.loads(Path(ap.parse_args().config).read_text()))
    answers = json.loads(ANSWERS.read_text())
    if not (answers.get("email") and answers.get("phone")):
        sys.exit(f'Add "email" and "phone" to {ANSWERS} first.')
    contact = {"email": answers["email"], "phone": answers["phone"], "visa_required": answers.get("needs_visa_sponsorship") == "Yes"}
    keys = ("headline", "summary", "experience", "projects", "education", "highlights", "availability")
    skills = [s for s in api.get("/api/profile")["skills"] if s["name"] not in REMOVED_SKILLS]
    skills += [{"name": n, "years": None} for n in ADDED_SKILLS if n not in {s["name"] for s in skills}]
    profile = api.call("PATCH", "/api/profile", json={**contact, **{k: DEFAULT_PROFILE[k] for k in keys}, "skills": skills}).json()
    if profile.get("projects") != DEFAULT_PROFILE["projects"]:
        sys.exit("This app ignored the CV fields: deploy the new version first (it accepts experience/projects).")
    current = api.get("/api/settings")
    body = {"search_queries": DEFAULT_SETTINGS["search_queries"],
            "sources": list(dict.fromkeys(current["sources"] + ["workday", "amazon", "recruiters", "himalayas", "weworkremotely",
                                                                "workremotely_eu", "openjobseu", "remoteboard"]))}
    body.update({k: list(dict.fromkeys(current.get(k, []) + DEFAULT_SETTINGS[k])) for k in COMPANY_LISTS})
    settings = api.call("PATCH", "/api/settings", json=body).json()
    print(f"OK: email {profile['email']}, {len(profile['education'])} degrees, {len(settings['search_queries'])} job roles, "
          f"{sum(len(settings[k]) for k in COMPANY_LISTS)} companies.")


if __name__ == "__main__":
    main()

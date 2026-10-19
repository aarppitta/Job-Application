"""Apply bot (applybot/apply.py): answers come only from known facts; never twice; never marketing boxes."""
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "applybot"))
import apply as bot  # noqa: E402

PROFILE = {"name": "Arpita Chaudhari", "email": "a@example.com", "phone": "+91 1", "location": "Ahmedabad, India",
           "linkedin_url": "https://linkedin.com/in/x", "github_url": "https://github.com/x", "visa_required": True,
           "years_experience": 2.5, "experience": [{"company": "Kevision Systems", "role": "System Software Engineer"}]}
ANSWERS = {"salary_eur_per_year": 70000, "salary_text": "EUR 70,000", "earliest_start": "1 January 2027",
           "earliest_start_iso": "2027-01-01", "needs_visa_sponsorship": "Yes", "authorized_to_work_in_germany": "No",
           "living_in_germany": "No", "willing_to_relocate": "Yes", "german_level": "None", "english_level": "C1",
           "gender": "", "public_official": "No", "how_did_you_hear": "Job board", "custom": []}


def facts(company="Enpal"):
    return bot.facts(PROFILE, ANSWERS, {"company": company}, "Dear team")


def test_known_questions_get_facts():
    f = facts()
    assert bot.answer_for("First Name", "text", f) == "Arpita"
    assert bot.answer_for("Last Name", "text", f) == "Chaudhari"
    assert bot.answer_for("Name", "text", f) == "Arpita Chaudhari"
    assert bot.answer_for("What is your target annual salary (gross)?", "number", f) == "70000"
    assert bot.answer_for("Will you require visa sponsorship?", "select", f) == "Yes"
    assert bot.answer_for("Are you authorized to work in Germany?", "yesno", f) == "No"
    assert bot.answer_for("Have you worked at Enpal before?", "yesno", f) == "No"
    assert facts("Kevision Systems")["worked_here"] == "Yes"
    assert bot.answer_for("Location (City)", "combobox", f) == "Ahmedabad"


def test_unknown_questions_are_never_guessed():
    f = facts()
    assert bot.answer_for("Tell us about a production incident you personally investigated", "textarea", f) is None
    assert bot.answer_for("Please indicate your nationality", "text", f) is None
    assert bot.answer_for("Gender", "select", f) is None  # not set in answers.json: never inferred


def test_custom_answers_win():
    f = {**facts(), "custom": [{"match": "level do you want", "answer": "Mid"}]}
    assert bot.answer_for("For which level do you want to apply?", "select", f) == "Mid"


def test_pick_option():
    assert bot.pick(["Select…", "Yes", "No"], "No") == 2
    assert bot.pick(["Ja", "Nein"], "Yes") == 0
    assert bot.pick(["Male", "Female", "Prefer not to say"], "prefer not to say") == 2
    assert bot.pick(["Male", "Female"], "prefer not to say") is None


def test_marketing_boxes_are_recognised():
    for label in ("I agree to allow Doctolib to retain my data for future opportunities",
                  "I consent to processing my responses to the demographic data surveys", "Subscribe to our newsletter"):
        assert re.search(bot.MARKETING, label, re.I)
    assert not re.search(bot.MARKETING, "I agree to the privacy policy", re.I)


def test_job_key_is_the_same_in_local_and_live_app():
    a = bot.job_key({"id": 1, "application_url": "https://www.helsing.ai/jobs/497?gh_jid=497&utm=x"})
    b = bot.job_key({"id": 99, "application_url": "https://helsing.ai/jobs/497/?gh_jid=497"})
    assert a == b == "helsing.ai/jobs/497?gh_jid=497"

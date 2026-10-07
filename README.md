# Germany Job Automation

Finds Germany-based software and industrial jobs by your keywords, saves every job description, scores each job against your CV, and gives you a **tailored CV** and **cover letter** for any job with one click. You apply on the company site, click **Mark as applied**, and the app keeps what you sent and tracks the status.

Project notes for Claude (file map, rules, change log): [`../CLAUDE.md`](../CLAUDE.md)

## Run

```bash
./start.sh          # backend on 8001 + frontend on 5001; Ctrl+C stops both
```
Open **http://localhost:5001** and log in with username `arpita`, password `JobHunt@2026` (change both in `.env`).

Backend only: `cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload --port 8001`.
Don't use plain `uvicorn …`; it may use the system Python and crash with `No module named 'sqlalchemy'`.

## Use

1. **Settings**: fill in email, phone and whether you need visa sponsorship.
2. **Automation → START**: searches your keywords at the followed companies for up to 6 hours, saves and scores every job.
3. **Jobs → Top Matches**: open a job, then use the buttons **Tailored CV** and **Cover letter**.
4. Apply on the company site (**Open job to apply**), then click **Mark as applied**.
5. **Applications**: update the status (Interview, Offer, Rejected…) and download the CV and letter you sent.

Jobs found elsewhere (LinkedIn, Indeed…): **Jobs → Import job** and paste the description.

## Tests

```bash
createdb germany_jobs_test        # one time
cd backend && venv/bin/pytest
```

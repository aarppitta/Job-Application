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

## Deploy on Vercel + Neon

The same code runs locally (`./start.sh`, background threads) and on Vercel (serverless: searches run in resumable
~4-minute steps, started by **Search now**, the **Automation** page while it is open, and 6 short Vercel Cron steps every
morning, 03:00–08:00 UTC = 08:30–13:30 IST; change the times in `vercel.json`). All settings are environment variables: see `.env.example`.

1. **Neon**: create a project in region **AWS Europe Central 1 (Frankfurt)** (the app's functions run in `fra1`).
   In *Connect*, turn **Connection pooling on** and copy the connection string (host contains `-pooler`).
2. **Move your current data (optional, do this BEFORE the first deploy)**, with Neon's *direct* (non-pooled) string:
   ```bash
   pg_dump --no-owner --no-acl germany_jobs | psql "postgresql://…direct-host…/neondb?sslmode=require"
   ```
3. **Vercel**: *Add New → Project*, import the repository. **Root Directory**: the folder that contains `vercel.json`
   (`./` for the aarppitta/Job-Application repo). Leave Framework / Build settings as they are: `vercel.json` sets them
   (Vite frontend + Python API in `api/index.py`). If a build says "No FastAPI entrypoint found", it built a commit
   without `vercel.json`: redeploy the latest commit.
4. **Environment variables** (Project → Settings → Environment Variables):
   | Name | Value |
   |---|---|
   | `DATABASE_URL` | the Neon pooled connection string |
   | `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(40))"` |
   | `MASTER_USERNAME` / `MASTER_PASSWORD` | your login (the default password is refused on Vercel) |
   | `CRON_SECRET` | another long random text (protects the daily cron) |
   | `AI_API_KEY` *(optional)* | Anthropic key for research, mock grading, answer drafts |
   | `JOB_KEYWORDS`, `PROFILE_JSON` *(optional)* | other roles / someone else's CV |
5. **Deploy**, open the URL, log in. Tables are created automatically on the first request.

Limits on the free Hobby plan: one function call ≤ 300 s (handled by the steps), crons at most daily (hence 6 of them).
On Pro you can run the cron more often (e.g. `*/30 * * * *`) and raise `STEP_SECONDS`.

## Tests

```bash
createdb germany_jobs_test        # one time
cd backend && venv/bin/pytest
```

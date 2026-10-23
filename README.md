# Job Application

Finds software and industrial jobs in Germany by your keywords (official job APIs of 75+ company career sites, incl.
Workday and Amazon, plus public job feeds, and remote-in-Europe boards: Himalayas, We Work Remotely, workremotely.eu,
OpenJobsEU, RemoteBoard), saves every job description, scores each job against your CV, and gives you
**one standard CV** (German/EU format) and a **cover letter** for any job. You apply on the company site, click
**Mark as applied**, and the app keeps what you sent and tracks the status (table, board and calendar).
**Recruiter jobs** lists the roles that recruitment agencies advertise (read from their own job pages), ready to apply.


## Run

```bash
./start.sh          # backend on 8001 + frontend on 5001; Ctrl+C stops both
```
Open **http://localhost:5001** and log in with username `arpita`, password `JobHunt@2026` (change both in `.env`).

Backend only: `cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload --port 8001`.
Don't use plain `uvicorn …`; it may use the system Python and crash with `No module named 'sqlalchemy'`.

## Use

1. **Settings**: fill in email, phone and whether you need visa sponsorship. **My CV**: check or edit your CV (or upload a PDF/Word CV).
2. **Automation → START** (or **Jobs → Search now**): searches your keywords at the followed companies, saves and scores every job.
   **Jobs → Source health** shows when each source was searched and whether it worked; closed jobs are hidden automatically.
3. **Jobs**: open a job, then use **Standard CV** and **Cover letter**. Save jobs and filter sets; add deadlines.
4. Apply on the company site (**Open job to apply**), then click **Mark as applied**.
5. **Applications**: status (Interview, Offer, Rejected…), interview dates, board and calendar views, the CV and letter you sent.
6. **Recruiter jobs**: roles from recruitment agencies (Randstad, Brunel, Vesterling, JAC, DEKRA Arbeit, persona service,
   TEMPTON, Orizon, I.K. Hofmann, ALTEN, CareerTeam), scored against your CV. **Search recruiters now** refreshes them;
   **Apply** opens the recruiter's page, **Mark as applied** saves the application. Only job pages the recruiters allow
   (robots.txt) are read, one per second; recruiters that can't be read are listed as links.

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

## Apply bot and CV files (on your Mac, not deployed)

```bash
backend/venv/bin/python applybot/standard_cv.py     # saves the standard CV as .docx/.pages/.pdf in ~/Desktop/Resume/Standard CV/
backend/venv/bin/python applybot/apply.py           # dry run: fills application forms, submits nothing
applybot/run_daily.sh                               # really apply (max 10 per run)
backend/venv/bin/python applybot/sync_profile.py    # after a deploy: copy CV + search settings to the live app
```
They log in with `~/.job-automation/config.json`; personal facts (email, phone, salary, start date…) live in
`~/.job-automation/answers.json`, never in the code.

## Tests

```bash
createdb germany_jobs_test        # one time
cd backend && venv/bin/pytest
```

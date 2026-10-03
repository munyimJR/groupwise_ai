# Deployment (≈ 20 minutes)

Target: **Supabase** (Postgres + Auth) → **Render** (FastAPI, Docker) → **Vercel** (Next.js).
Any Docker host works for the API (Railway, Fly.io, Koyeb, Google Cloud Run, Hugging Face Spaces).

## 1. Supabase

1. Create a project at supabase.com (choose a region near Bangladesh, e.g. Singapore).
2. **Database URL:** Project Settings → Database → *Connection pooling* → mode **Transaction** (port 6543). Copy the URI and fill in your database password. This is `DATABASE_URL`.
3. **Auth (optional):** Authentication → Providers → Email (enabled by default). For a frictionless hackathon demo you can turn off *Confirm email*.
   Copy the **Project URL** (`SUPABASE_URL`) and the **anon public** key (`NEXT_PUBLIC_SUPABASE_ANON_KEY`). Never use the service-role key in either app.
4. Tables are created automatically when the API starts, and RLS is enabled on all of them. To create them ahead of time, run `supabase/schema.sql` in the SQL editor.

> Skipping Supabase still gives you a working app: the API falls back to SQLite plus built-in accounts. Data then lives on the container's disk and resets on redeploy.

## 2. API on Render

1. Push this repository to GitHub.
2. Render → **New → Blueprint** → select the repo (uses `render.yaml`: Docker, `backend/`, health check `/api/health`).
3. Set the secret env vars:
   - `DATABASE_URL`: from step 1
   - `PUBLIC_APP_URL` and `CORS_ORIGINS`: your Vercel URL (e.g. `https://groupwise-ai.vercel.app`)
   - `SUPABASE_URL`: if using Supabase Auth (`SUPABASE_JWT_SECRET` only for legacy HS256 projects)
   - `ANTHROPIC_API_KEY`: optional; enables natural-language copilot answers
   - `JWT_SECRET` is generated automatically
4. Deploy, then check `https://<service>.onrender.com/api/health` → `{"status":"ok","database":true,...}`.

**Free-tier cold starts:** Render's free plan sleeps after ~15 minutes idle, and the first request can take up to a minute. The demo button explains this to users. Before judging, either open the site a few minutes ahead, add a free uptime monitor that hits `/api/health` every 10 minutes, or use a paid instance.

## 3. Web app on Vercel

1. Vercel → **Add New → Project** → import the repo → **Root Directory: `frontend`** (framework auto-detected: Next.js).
2. Environment variables:
   - `BACKEND_URL` = `https://<service>.onrender.com` (no trailing slash)
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`: optional (Supabase Auth)
3. Deploy. Open the URL → **Explore the live demo**.
4. Put the URL in the README's *Live URL* section, and update `PUBLIC_APP_URL` / `CORS_ORIGINS` on Render if the domain changed.

## 4. Smoke test checklist

- [ ] `/api/health` reports `database: true`
- [ ] Landing → *Explore the live demo* → dashboard loads with insights
- [ ] Add expense `Dinner at Kacchi Bhai 16500` → categorized as Food › Restaurant → unusual-expense dialog
- [ ] What-If *Cut dining 15%* updates the goal impact
- [ ] Ask GroupWise answers with the "figures verified" badge (LLM wording if `ANTHROPIC_API_KEY` is set)
- [ ] Sign up with a real account (Supabase or built-in) → create a group → copy the invite link → join from a second browser
- [ ] Phone: bottom navigation, add expense, *Add to Home screen*

## Local Docker

```bash
cd backend
docker build -t groupwise-api .
docker run -p 8000:8000 -e JWT_SECRET=$(python -c "import secrets;print(secrets.token_urlsafe(48))") groupwise-api
```

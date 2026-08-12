# Qriosity Quest — Deployment Guide

> Manual steps to deploy the FastAPI backend to Render and the React frontend
> to GitHub Pages. No automation here — follow each section in order.

---

## Prerequisites

- A [Render](https://render.com) account (free tier is fine)
- A [GitHub](https://github.com) account with this repo pushed
- Your Supabase project URL + anon key

---

## Part 1 — Deploy the backend to Render

### 1. Push the repo to GitHub
Make sure your latest code (including `backend/Procfile` and
`backend/requirements.txt`) is committed and pushed to GitHub.

### 2. Create a new Web Service on Render
1. Log in to [render.com](https://render.com) → **New → Web Service**
2. Connect your GitHub repo
3. Set **Root Directory** to `backend`
4. Set **Runtime** to `Python 3`
5. Set **Build Command** to:
   ```
   pip install -r requirements.txt
   ```
6. Set **Start Command** to:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   *(Render injects `$PORT` automatically — do not hardcode a port number.)*

### 3. Add environment variables on Render
In **Environment → Environment Variables**, add:

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | your Gemini API key |
| `ALLOWED_ORIGINS` | your frontend URL (e.g. `https://yourusername.github.io`) |

> **Important:** Do not add `.env` to git. The `backend/.env` file is
> gitignored and is for local dev only. Render reads these from its own
> env-vars dashboard.

### 4. Deploy
Click **Create Web Service**. Render will build and deploy automatically.
Once it's live, copy the service URL — it will look like:
`https://qriosity-quest-xxxx.onrender.com`

---

## Part 2 — Deploy the frontend to GitHub Pages

### 1. Set the backend URL in the frontend
In `frontend/.env.local`, update:
```
VITE_API_BASE_URL=https://qriosity-quest-xxxx.onrender.com
```
Replace the URL with your actual Render service URL from Part 1.

> `.env.local` is gitignored, so you set this in your GitHub repo's
> **Settings → Secrets and variables → Actions** instead for CI.

### 2. Add GitHub Actions secret
In your GitHub repo: **Settings → Secrets and variables → Actions →
New repository secret**:

| Name | Value |
|------|-------|
| `VITE_SUPABASE_URL` | your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | your Supabase anon key |
| `VITE_API_BASE_URL` | your Render backend URL |

### 3. Add a GitHub Actions workflow
Create `.github/workflows/deploy.yml` in the repo root:

```yaml
name: Deploy Frontend to GitHub Pages

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install dependencies
        run: npm install
        working-directory: frontend

      - name: Build
        run: npm run build
        working-directory: frontend
        env:
          VITE_SUPABASE_URL: ${{ secrets.VITE_SUPABASE_URL }}
          VITE_SUPABASE_ANON_KEY: ${{ secrets.VITE_SUPABASE_ANON_KEY }}
          VITE_API_BASE_URL: ${{ secrets.VITE_API_BASE_URL }}

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: frontend/dist
```

### 4. Enable GitHub Pages
In your GitHub repo: **Settings → Pages → Source → Deploy from a branch**
→ Select `gh-pages` branch → Save.

### 5. Supabase redirect URLs
After deployment, add your GitHub Pages URL to Supabase's allowed redirect
URLs:
1. Supabase Dashboard → **Authentication → URL Configuration**
2. Add to **Redirect URLs**: `https://yourusername.github.io/qriosity-quest/**`

---

## Updating after code changes

- **Backend change:** Push to GitHub → Render auto-redeploys (or click
  "Manual Deploy" in the Render dashboard).
- **Frontend change:** Push to `main` → GitHub Actions builds and deploys
  automatically.

---

## Local development (no change needed)

```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm run dev
```

`VITE_API_BASE_URL` defaults to `http://localhost:8000` if unset, so local
dev works with zero config.

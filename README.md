# Master Scheduler AI (AI Scheduler 2)

AI-powered study planner and academic scheduler for students and teachers.

Live demo: https://ai-scheduler-2.vercel.app/

## Overview
Master Scheduler AI helps users build study plans, schedule sessions, track tasks, and manage academic calendars. It combines deterministic scheduling logic with AI-assisted planning for exams and recovery workflows.

## Features
- AI chat for exam planning, study plans, and recovery schedules
- Calendar view with color-coded sessions and conflict-aware planning
- Today's to-do list with progress tracking
- Stress meter summarizing workload health
- Student/teacher modes and profile personalization
- Voice input via the Web Speech API

## Screenshots
![Home dashboard](ScreenShots/Screenshot%202026-05-11%20230939.png)
![Chat landing](ScreenShots/Screenshot%202026-05-12%20162257.png)
![Schedule view](ScreenShots/Screenshot%202026-05-12%20162330.png)
![Profile page](ScreenShots/Screenshot%202026-05-12%20162451.png)

## Tech stack
- FastAPI + Python 3
- Supabase PostgreSQL
- OpenRouter for AI responses
- HTML/CSS/JavaScript frontend
- Vercel deployment (serverless API + static frontend)

## Architecture
1. Frontend calls API routes via `public/js/api.js`.
2. FastAPI handles requests under `/api/*`.
3. Supabase stores settings, chats, schedules, and history.
4. OpenRouter generates AI responses for planning.

## Project structure
- `api/` - Vercel serverless entry for FastAPI
- `backend/` - AI, scheduling, ranking, and database layers
- `public/` - frontend HTML, CSS, and JS modules
- `ScreenShots/` - product screenshots

## Getting started

### Prerequisites
- Python 3.10+
- A Supabase project

### Setup
1. Create a virtual environment and install dependencies.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in the values.
3. Run `supabase_migration.sql` in the Supabase SQL editor.
4. Start the backend API.

```bash
uvicorn api.index:app --reload
```

5. Serve the frontend from `public/`. For local development:
- Update `API_BASE` in `public/js/api.js` to `http://localhost:8000`.
- Start a static server from the `public/` folder.

```bash
python -m http.server 5173
```

Open http://localhost:5173 in the browser.

## Environment variables
| Variable | Description |
| --- | --- |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon key |
| `OPENROUTER_API_KEY` | OpenRouter API key |

## API notes
- Base path: `/api`
- Streaming chat: `/api/chat/stream` (Server-Sent Events)

## Deployment
Vercel deploys the FastAPI app from `api/index.py` and serves `public/` as static assets. See `vercel.json` for routes and build rules.

## Documentation
- `PROJECT_OVERVIEW.md`
- `API_USAGE.md`

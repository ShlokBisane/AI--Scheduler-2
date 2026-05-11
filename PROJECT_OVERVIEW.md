# Master Scheduler AI - Project Overview

## What this project is
Master Scheduler AI is a study-planning and academic scheduling web app. It helps students and teachers create study plans, schedule sessions, track tasks, manage calendar events, review history, and use AI-generated scheduling guidance.

The app has two major parts:
- A FastAPI backend that exposes `/api/*` endpoints.
- A browser frontend in `public/` that provides the user interface.

The backend stores user and schedule data in Supabase PostgreSQL, and it uses OpenRouter for AI-powered schedule generation.

## Tech stack
- Python 3 / FastAPI
- Supabase PostgreSQL via `supabase-py`
- Plain HTML, CSS, and JavaScript on the frontend
- OpenRouter for AI responses
- Vercel for deployment
- Web Speech API for voice input

## How the app works
1. The user opens the frontend in the browser.
2. Frontend JavaScript calls backend API routes through `public/js/api.js`.
3. The backend reads and writes data in Supabase.
4. When the user asks for planning help, the backend sends the prompt to OpenRouter.
5. The AI response is parsed into structured schedules, which are saved and then rendered in the UI.

## Main folders

### `api/`
Contains the Vercel serverless entry point.

### `backend/`
Contains the backend business logic, database layer, AI integration, ranking logic, scheduling engine, and prompt builders.

### `public/`
Contains the full browser frontend: HTML, CSS, images/assets, and browser-side JavaScript modules.

## File-by-file guide

### Root files

#### `requirements.txt`
Lists the Python packages used by the backend. The important dependencies are:
- `fastapi`
- `uvicorn[standard]`
- `requests`
- `pydantic`
- `python-multipart`
- `supabase`
- `python-dotenv`

#### `supabase_migration.sql`
Defines the database schema used by the app. It creates:
- `settings`
- `chats`
- `messages`
- `schedules`
- `subject_colors`
- `schedule_history`

This file should be run in the Supabase SQL editor before deploying.

#### `vercel.json`
Vercel deployment configuration. It defines how the app should be built and how routes should be handled for the backend and frontend.

#### `.env.example`
Shows the environment variables required for local development and deployment:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENROUTER_API_KEY`

#### `.gitignore`
Excludes local and generated files from version control.

## Backend files

### `api/index.py`
This is the main FastAPI entry point for Vercel.

What it does:
- Creates the FastAPI app
- Enables CORS
- Reads API keys from environment variables
- Runs startup cleanup logic
- Exposes all `/api/*` routes
- Handles chat streaming via SSE
- Saves settings, profiles, chats, messages, schedules, task status, history, subject colors, and ranking output

Key responsibilities:
- `/api/health`
- `/api/settings`
- `/api/profile`
- `/api/chats`
- `/api/chat/stream`
- `/api/schedule/*`
- `/api/todo/*`
- `/api/history`
- `/api/health/stress`
- `/api/subject-colors`
- `/api/ranking/*`

It connects the frontend to the rest of the backend modules.

### `backend/database.py`
Database access layer.

What it does:
- Creates the Supabase client
- Loads and updates settings
- Saves and loads profile data
- Creates, reads, updates, and deletes chats
- Stores messages
- Stores schedules
- Stores subject colors
- Manages schedule history
- Calculates today tasks and overdue tasks
- Cleans up orphaned data
- Handles expired schedules

This file is the persistence layer for almost all user data.

### `backend/ai_engine.py`
AI integration layer.

What it does:
- Sends chat requests to OpenRouter
- Streams responses from OpenRouter
- Builds the final message list with system prompts and profile context
- Generates chat titles from the first message
- Extracts schedule JSON from AI responses
- Cleans AI output before showing it to users

This file is responsible for the actual AI communication logic.

### `backend/ranking_engine.py`
Deterministic subject ranking and priority engine.

What it does:
- Detects exam type from text
- Estimates subject difficulty
- Scores subjects by urgency, exam importance, difficulty, confidence, and priority
- Ranks topics and subjects
- Re-ranks after missed study days
- Maps subjects to colors
- Builds ordered study plans

This file makes scheduling decisions using rule-based logic instead of AI guessing.

### `backend/scheduler.py`
Study-session and recovery scheduling engine.

What it does:
- Chooses break profiles based on total study hours
- Generates time blocks
- Inserts short and long breaks
- Applies biological constraints like lunch and sleep time
- Infers priority from exam descriptions
- Generates recovery options when study time is missed

This file turns a plan into actual time blocks.

### `backend/prompts.py`
Prompt builder for AI behavior.

What it does:
- Builds current date context for the prompt
- Injects user profile context
- Detects class/course level to recommend session lengths
- Builds student and teacher system prompts
- Restricts the AI to scheduling and exam-planning behavior

This file defines how the AI should think and what it is allowed to do.

### `backend/__init__.py`
Marks `backend` as a Python package.

## Frontend files

### `public/index.html`
Main HTML page for the app.

What it contains:
- Sidebar
- New chat button
- Student/teacher mode toggle
- Recent chats panel
- To-do panel
- Calendar panel
- Stress meter
- History panel
- Profile button
- Chat area
- Profile page
- Voice input controls
- All script and stylesheet imports

This is the structural layout of the UI.

### `public/css/style.css`
All visual styling for the app.

What it does:
- Controls layout and spacing
- Styles the sidebar, chat area, calendar, to-do list, history, profile page, and stress meter
- Defines responsive behavior
- Handles the visual theme and component states

### `public/js/api.js`
Frontend API client.

What it does:
- Wraps `fetch()` calls to the backend
- Centralizes API requests
- Provides methods like:
  - `getSettings()`
  - `saveSettings()`
  - `getChats()`
  - `createChat()`
  - `streamMessage()`
  - `getCalendar()`
  - `getTodayTasks()`
  - `getStress()`
  - `getProfile()`
  - `getHistory()`
  - `computeRanking()`

This is the bridge between browser UI code and backend endpoints.

### `public/js/app.js`
Main browser bootstrap and sidebar/settings logic.

What it does:
- Initializes all frontend modules
- Handles sidebar open/close behavior
- Loads settings
- Refreshes chat list
- Wires student/teacher mode toggles
- Handles provider toggles
- Auto-expires old schedules on load

This is the central browser-side coordinator.

### `public/js/chat.js`
Chat interface module.

What it does:
- Manages chat messages
- Handles sending messages
- Handles streaming responses
- Renders welcome cards
- Manages current chat state and mode
- Displays AI-generated schedules and chat title updates

This is the main user interaction module for conversations.

### `public/js/calendar.js`
Calendar module.

What it does:
- Renders the mini calendar
- Shows schedule dots and exam highlights
- Loads calendar data from the backend
- Displays subject color legends
- Supports month navigation
- Opens and closes the detail panel

### `public/js/todo.js`
To-do module.

What it does:
- Loads today’s tasks
- Shows pending, completed, overdue, and in-progress tasks
- Displays the next task indicator
- Allows the user to collapse or expand the panel
- Updates task status

### `public/js/stress.js`
Stress meter module.

What it does:
- Reads schedule-health data from the backend
- Renders the stress gauge
- Shows fullness and scheduling pressure
- Updates color and label based on stress level

### `public/js/profile.js`
Profile module.

What it does:
- Opens the profile page instead of the chat area
- Loads and saves profile details
- Updates class hint text
- Helps the AI understand the user’s study context

### `public/js/history.js`
History module.

What it does:
- Loads history entries
- Shows completed, expired, and deleted schedule data
- Displays history count and summary
- Supports collapsing and expanding the panel

### `public/js/voice.js`
Voice input module.

What it does:
- Uses the browser Speech Recognition API
- Supports English, Hindi, and Punjabi input
- Fills the chat input from speech
- Handles start/stop and error states

## Data flow

### Chat flow
1. User types a message in the chat UI.
2. `public/js/chat.js` sends it through `public/js/api.js`.
3. `api/index.py` receives the request.
4. `backend/ai_engine.py` calls OpenRouter.
5. The response is stored in Supabase through `backend/database.py`.
6. The frontend renders the response and any schedule cards.

### Scheduling flow
1. AI or ranking logic creates schedule data.
2. `backend/scheduler.py` and `backend/ranking_engine.py` shape the plan.
3. Schedules are saved to Supabase.
4. Calendar, to-do, stress, and history modules refresh their data.

## Environment variables
The project expects these variables in Vercel or local `.env`:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENROUTER_API_KEY`

## Deployment notes
- The app is deployed on Vercel.
- The backend runs as a Python serverless function.
- The frontend is served from the `public/` directory.
- Supabase is required for persistence.

## Development notes
Before running the app, make sure:
- Supabase tables from `supabase_migration.sql` exist
- Required environment variables are set
- Python dependencies from `requirements.txt` are installed

## Short summary
This project is a full-stack AI study scheduler. The backend handles AI, schedules, and storage. The frontend provides a responsive dashboard for chats, tasks, calendar, history, profile, stress, and voice input.

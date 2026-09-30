# PocketSmart AI

PocketSmart turns a budget and a few preferences into a practical starting plan for home interiors, parties and occasion jewelry. It includes account registration, private recommendation history, a responsive web interface, and optional Gemini text and image reasoning.

## What is included

- FastAPI app with server-rendered Jinja pages and JSON planner endpoints.
- Home, party and jewelry planners with input validation and budget checks.
- SQLite accounts and per-user recommendation history.
- Passwords hashed with scrypt; signed HS256 session and bearer tokens; CSRF protection for browser form/API requests.
- Optional Gemini integration, including JPG, PNG and WebP outfit images for jewelry planning.
- Local recommendation fallbacks when Gemini is not configured or its response is unavailable or over budget.
- Search links for Amazon, Flipkart, IKEA, Swiggy, Zomato and OYO. These are not live retailer integrations: suggestions and prices are estimates, and availability must be verified on the retailer site.
- Tests for authentication, request validation, budget limits, CSRF, all three planners and history.

The source notes mention both Flask and FastAPI; this implementation uses FastAPI to match the detailed route and milestone requirements. The named “Gemini 1.5 Flash Pro” is not used as a hard-coded model identifier. The default is configurable as `gemini-2.5-flash`; select a model currently enabled for your Google AI Studio API key by setting `GEMINI_MODEL`.

## Requirements

- Python 3.11 or newer.
- Visual Studio Code with the Microsoft Python extension.
- A Gemini API key is optional. Without it, every planner works using local estimates.

## Setup in VS Code

1. Open this folder in VS Code.
2. Open the Command Palette with `Ctrl+Shift+P`, run **Python: Create Environment**, choose **Venv**, and select Python 3.11 or newer. If prompted, allow VS Code to install `requirements.txt`.
3. If dependencies were not installed automatically, open a new terminal and run:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Create the local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

5. For local development, the default secret key works. Before exposing the app beyond your machine, replace `SECRET_KEY` in `.env` with a long random value. To enable Gemini, set `GEMINI_API_KEY` and, if needed, `GEMINI_MODEL` in `.env`. Restart the server after changing environment values.

## Run

In VS Code, open **Terminal → Run Task… → PocketSmart: Start app**. Or run this in the integrated terminal after selecting the project interpreter:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Create an account, then choose a planner from the dashboard. Interactive API documentation is at <http://127.0.0.1:8000/docs>; health status is at <http://127.0.0.1:8000/health>.

To debug, select **PocketSmart AI: FastAPI** in the VS Code Run and Debug panel and press `F5`.

## Test

Run **Terminal → Run Task… → PocketSmart: Run tests**, or use:

```powershell
python -m pytest -q
```

Tests use temporary SQLite databases and do not need a Gemini key or retailer accounts.

## API routes

| Route | Purpose |
| --- | --- |
| `POST /register`, `POST /login`, `POST /logout` | Create an account, sign in and sign out |
| `POST /token` | Issue an OAuth2-compatible bearer token |
| `GET /session-info`, `GET /session-data` | Read login status and the current user's recent data |
| `POST /generate-home` | Generate a home plan (JSON) |
| `POST /generate-party` | Generate a party plan (JSON) |
| `POST /generate-jewelry` | Generate a jewelry plan (multipart form, optional image) |
| `GET /api/history`, `GET /history` | Read saved plans as JSON or a page |
| `GET /recommendations-details/{entry_id}` | Open one of the current user's saved plans |
| `GET /startup`, `GET /health` | Check configuration and process health |

Browser planner requests use the session cookie and CSRF token automatically. API clients can send `Authorization: Bearer <token>`; bearer-authenticated planner requests do not require the browser CSRF header.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | Local development key | Signs session and bearer tokens; use a random secret outside local development |
| `DATABASE_PATH` | `./data/pocketsmart.db` | SQLite database path |
| `GEMINI_API_KEY` | Empty | Enables Gemini recommendations and optional image analysis |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Google GenAI model identifier |
| `COOKIE_SECURE` | `false` | Set `true` when serving over HTTPS |
| `ALLOWED_ORIGINS` | Localhost origins | JSON list of allowed CORS origins |

## Project layout

```text
app/
  routes/       Page, auth and planner endpoints
  services/     Gemini integration and deterministic fallback plans
  static/       Responsive CSS and browser interactions
  templates/    Jinja pages
  config.py     Environment settings
  database.py   SQLite persistence
  main.py       FastAPI application
tests/          Budget and API integration tests
.vscode/        Run/debug configuration
```
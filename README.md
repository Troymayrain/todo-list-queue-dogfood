# Task List

A responsive, server-rendered Task List built with FastAPI, SQLite, Tailwind CSS, and HTMX.

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js 22 and npm

## First-time setup

Run these fixed commands from the repository root:

```bash
uv sync --frozen
npm ci
npm run build
uv run python -m task_list.migrate
uv run uvicorn task_list.app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. The default database is `data/tasks.sqlite3` and is preserved across application restarts. Set `TASK_LIST_DATABASE` to use another SQLite file:

```bash
TASK_LIST_DATABASE=/path/to/tasks.sqlite3 uv run python -m task_list.migrate
TASK_LIST_DATABASE=/path/to/tasks.sqlite3 uv run uvicorn task_list.app:app
```

Run `npm run build` again after changing templates or `src/task_list/static/input.css` so Tailwind can regenerate the checked-in application stylesheet and local HTMX asset.

## Tests

Install the browser once and run the end-to-end test suite:

```bash
uv run playwright install chromium
uv run pytest
uv run ruff check .
```

Each browser test launches the application with its own temporary SQLite database. On failure, Playwright screenshots, the rendered page, and server logs are retained under `test-results/`.

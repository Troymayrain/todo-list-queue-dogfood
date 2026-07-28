import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "tasks.sqlite3"
MIGRATIONS_PATH = PROJECT_ROOT / "migrations"


def database_path() -> Path:
    return Path(os.environ.get("TASK_LIST_DATABASE", DEFAULT_DATABASE_PATH))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def migrate() -> None:
    with connect() as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)"
        )
        applied = {
            row["name"]
            for row in connection.execute("SELECT name FROM schema_migrations")
        }
        for migration in sorted(MIGRATIONS_PATH.glob("*.sql")):
            if migration.name in applied:
                continue
            connection.executescript(migration.read_text())
            connection.execute(
                "INSERT INTO schema_migrations (name) VALUES (?)", (migration.name,)
            )


def list_tasks(status: str | None = None) -> list[sqlite3.Row]:
    query = "SELECT id, title, created_at, status FROM tasks"
    parameters: tuple[str, ...] = ()
    if status is not None:
        query += " WHERE status = ?"
        parameters = (status,)
    query += " ORDER BY created_at DESC, id DESC"
    with connect() as connection:
        return list(connection.execute(query, parameters))


def get_task(task_id: int) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute(
            "SELECT id, title, created_at, status FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()


def create_task(title: str) -> sqlite3.Row:
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, created_at) "
            "VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
            (title,),
        )
        task = connection.execute(
            "SELECT id, title, created_at, status FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        assert task is not None
        return task


def update_task_title(task_id: int, title: str) -> sqlite3.Row | None:
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE tasks SET title = ? WHERE id = ?", (title, task_id)
        )
        if cursor.rowcount == 0:
            return None
        return connection.execute(
            "SELECT id, title, created_at, status FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()


def update_task_status(task_id: int, status: str) -> sqlite3.Row | None:
    if status not in {"Active", "Completed"}:
        raise ValueError("Unknown Task Status")
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE tasks SET status = ? WHERE id = ?", (status, task_id)
        )
        if cursor.rowcount == 0:
            return None
        return connection.execute(
            "SELECT id, title, created_at, status FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()

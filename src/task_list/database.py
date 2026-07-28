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
        for migration in sorted(MIGRATIONS_PATH.glob("*.sql")):
            connection.executescript(migration.read_text())


def list_tasks() -> list[sqlite3.Row]:
    with connect() as connection:
        return list(
            connection.execute(
                "SELECT id, title, created_at FROM tasks ORDER BY created_at DESC, id DESC"
            )
        )


def get_task(task_id: int) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute(
            "SELECT id, title, created_at FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()


def create_task(title: str) -> sqlite3.Row:
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, created_at) "
            "VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
            (title,),
        )
        task = connection.execute(
            "SELECT id, title, created_at FROM tasks WHERE id = ?", (cursor.lastrowid,)
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
            "SELECT id, title, created_at FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()

import sqlite3
import urllib.request
from pathlib import Path


def test_tasks_have_stable_descending_tie_breaker(app_server: str, tmp_path: Path) -> None:
    with sqlite3.connect(tmp_path / "tasks.sqlite3") as connection:
        connection.executemany(
            "INSERT INTO tasks (title, created_at) VALUES (?, ?)",
            [
                ("Older", "2026-01-01T00:00:00.000Z"),
                ("Same time first", "2026-01-02T00:00:00.000Z"),
                ("Same time second", "2026-01-02T00:00:00.000Z"),
            ],
        )

    with urllib.request.urlopen(app_server) as response:
        body = response.read().decode()

    assert body.index("Same time second") < body.index("Same time first") < body.index("Older")

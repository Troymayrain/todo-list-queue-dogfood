CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS tasks_created_order
ON tasks (created_at DESC, id DESC);

ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'Active'
    CHECK (status IN ('Active', 'Completed'));

CREATE INDEX IF NOT EXISTS tasks_status_created_order
ON tasks (status, created_at DESC, id DESC);

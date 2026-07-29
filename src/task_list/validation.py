MAX_TASK_TITLE_LENGTH = 200


def validate_task_title(title: str) -> tuple[str, str | None]:
    trimmed_title = title.strip()
    if not trimmed_title:
        return trimmed_title, "Enter a Task Title."
    if len(trimmed_title) > MAX_TASK_TITLE_LENGTH:
        return trimmed_title, "Task Title must be 200 characters or fewer."
    return trimmed_title, None

import sqlite3
from pathlib import Path

from playwright.sync_api import Page, expect


def task_titles(page: Page):
    return page.locator("#task-list [data-task-title]")


def test_task_list_complete_browser_path(page: Page, app_server: str, tmp_path: Path) -> None:
    expect(page.get_by_role("heading", name="Task List", exact=True)).to_be_visible()
    expect(page.get_by_text("Your Task List is empty")).to_be_visible()
    title = page.get_by_label("Task Title")
    expect(title).to_be_focused()
    expect(page.get_by_role("button", name="Add Task")).to_be_visible()

    title.fill("   First Task   ")
    page.get_by_role("button", name="Add Task").click()
    expect(task_titles(page)).to_have_text(["First Task"])
    expect(page).to_have_url(app_server + "/")

    title.fill("Second Task")
    title.press("Enter")
    expect(task_titles(page)).to_have_text(["Second Task", "First Task"])

    title.fill("   ")
    title.press("Enter")
    expect(page.get_by_role("alert")).to_have_text("Enter a Task Title.")
    expect(title).to_have_value("   ")
    expect(title).to_have_attribute("aria-invalid", "true")
    expect(task_titles(page)).to_have_count(2)

    too_long = "x" * 201
    title.fill(too_long)
    title.press("Enter")
    expect(page.get_by_role("alert")).to_have_text(
        "Task Title must be 200 characters or fewer."
    )
    expect(title).to_have_value(too_long)
    expect(task_titles(page)).to_have_count(2)

    page.reload()
    expect(task_titles(page)).to_have_text(["Second Task", "First Task"])

    with sqlite3.connect(tmp_path / "tasks.sqlite3") as connection:
        assert connection.execute("SELECT title FROM tasks ORDER BY id").fetchall() == [
            ("First Task",),
            ("Second Task",),
        ]


def test_standard_post_redirects_and_persists_without_htmx(
    page: Page, app_server: str
) -> None:
    page.get_by_label("Task Title").fill("  Standard Task  ")
    with page.expect_response(lambda response: response.request.method == "POST") as response:
        page.get_by_role("button", name="Add Task").click()
    assert response.value.status == 200
    expect(task_titles(page)).to_have_text(["Standard Task"])
    page.reload()
    expect(task_titles(page)).to_have_text(["Standard Task"])


def test_desktop_viewport_keeps_creation_path_usable(page: Page) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    expect(page.get_by_label("Task Title")).to_be_visible()
    expect(page.get_by_role("button", name="Add Task")).to_be_visible()

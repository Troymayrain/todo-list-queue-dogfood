import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, expect


def task_titles(page: Page):
    return page.locator("#task-list [data-task-title]")


def add_task(page: Page, title: str) -> None:
    page.get_by_label("Task Title").fill(title)
    page.get_by_role("button", name="Add Task").click()
    expect(task_titles(page).filter(has_text=title)).to_have_count(1)


def open_delete_confirmation(page: Page, title: str) -> None:
    page.get_by_role("link", name=f"Delete {title}", exact=True).press("Enter")
    expect(page.get_by_role("heading", name="Permanently delete this Task?")).to_be_visible()
    expect(page.get_by_text(f"You are about to delete {title}.", exact=False)).to_be_visible()


def test_cancel_delete_keeps_task_and_returns_focus(page: Page) -> None:
    add_task(page, "Task to keep")

    open_delete_confirmation(page, "Task to keep")
    confirm = page.get_by_role("button", name="Permanently delete Task to keep")
    expect(confirm).to_be_focused()
    expect(confirm).to_have_css("outline-style", "solid")

    page.get_by_role("link", name="Cancel deletion").press("Enter")

    expect(task_titles(page)).to_have_text(["Task to keep"])
    expect(page.get_by_role("link", name="Delete Task to keep", exact=True)).to_be_focused()


def test_confirm_delete_removes_task_and_persists(page: Page, tmp_path: Path) -> None:
    add_task(page, "Task to delete")
    add_task(page, "Task that remains")

    open_delete_confirmation(page, "Task to delete")
    page.get_by_role("button", name="Permanently delete Task to delete").press("Enter")

    expect(task_titles(page)).to_have_text(["Task that remains"])
    page.reload()
    expect(task_titles(page)).to_have_text(["Task that remains"])
    with sqlite3.connect(tmp_path / "tasks.sqlite3") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE title = ?", ("Task to delete",)
        ).fetchone()[0] == 0


def test_delete_preserves_each_filter_and_shows_correct_empty_state(page: Page) -> None:
    add_task(page, "Active Task")
    add_task(page, "Completed Task")
    page.get_by_role("button", name="Mark Completed Task as Completed").click()

    page.get_by_role("link", name="Active", exact=True).click()
    expect(page.get_by_role("link", name="Active", exact=True)).to_have_attribute(
        "aria-current", "page"
    )
    open_delete_confirmation(page, "Active Task")
    page.get_by_role("button", name="Permanently delete Active Task").click()
    expect(page).to_have_url(page.url.split("?")[0] + "?filter=active")
    expect(page.get_by_text("No Active Tasks")).to_be_visible()

    page.get_by_role("link", name="Completed", exact=True).click()
    expect(page.get_by_role("link", name="Completed", exact=True)).to_have_attribute(
        "aria-current", "page"
    )
    open_delete_confirmation(page, "Completed Task")
    page.get_by_role("button", name="Permanently delete Completed Task").click()
    expect(page).to_have_url(page.url.split("?")[0] + "?filter=completed")
    expect(page.get_by_text("No Completed Tasks")).to_be_visible()

    add_task(page, "All Task")
    page.get_by_role("link", name="All", exact=True).click()
    expect(page.get_by_role("link", name="All", exact=True)).to_have_attribute(
        "aria-current", "page"
    )
    open_delete_confirmation(page, "All Task")
    page.get_by_role("button", name="Permanently delete All Task").click()
    expect(page).to_have_url(page.url.split("?")[0])
    expect(page.get_by_text("Your Task List is empty")).to_be_visible()


def test_delete_confirmation_and_missing_recovery_work_without_htmx(
    page: Page, app_server: str
) -> None:
    add_task(page, "Standard delete Task")
    page.evaluate("window.htmx = undefined")
    page.locator("script[src*='htmx']").evaluate("element => element.remove()")

    page.get_by_role("link", name="Delete Standard delete Task", exact=True).click()
    expect(page.get_by_role("heading", name="Task List")).to_be_visible()
    expect(page.get_by_role("heading", name="Permanently delete this Task?")).to_be_visible()
    page.get_by_role("link", name="Cancel deletion").click()
    expect(task_titles(page)).to_have_text(["Standard delete Task"])

    try:
        urllib.request.urlopen(app_server + "/tasks/999/delete")
    except urllib.error.HTTPError as error:
        assert error.code == 404
        body = error.read().decode()
    else:
        raise AssertionError("Missing Task response should use status 404")
    assert "<!doctype html>" in body
    assert "That Task no longer exists" in body
    assert "Task List" in body


def test_missing_task_during_delete_recovers_to_latest_list(
    page: Page, tmp_path: Path
) -> None:
    add_task(page, "Task to remove elsewhere")
    add_task(page, "Task that remains")
    open_delete_confirmation(page, "Task to remove elsewhere")

    with sqlite3.connect(tmp_path / "tasks.sqlite3") as connection:
        connection.execute(
            "DELETE FROM tasks WHERE title = ?", ("Task to remove elsewhere",)
        )

    page.get_by_role(
        "button", name="Permanently delete Task to remove elsewhere"
    ).click()

    alert = page.get_by_role("alert")
    expect(alert).to_have_text(
        "That Task no longer exists. The current Task List is shown below."
    )
    expect(alert).to_be_focused()
    expect(task_titles(page)).to_have_text(["Task that remains"])

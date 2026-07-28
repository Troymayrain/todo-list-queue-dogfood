import sqlite3
from pathlib import Path

from playwright.sync_api import Page, expect


def task_titles(page: Page):
    return page.locator("#task-list [data-task-title]")


def create_title(page: Page):
    return page.locator("#task-form").get_by_label("Task Title")


def edit_title(page: Page):
    return page.locator("#task-list").get_by_label("Task Title")


def add_task(page: Page, title: str) -> None:
    create_title(page).fill(title)
    page.get_by_role("button", name="Add Task").click()
    expect(create_title(page)).to_have_value("")
    expect(task_titles(page).filter(has_text=title.strip())).to_have_count(1)


def test_cancel_edit_keeps_title_and_returns_focus(page: Page) -> None:
    add_task(page, "Original Task")

    page.keyboard.press("Tab")
    edit_button = page.get_by_role("button", name="Edit Original Task")
    expect(edit_button).to_be_focused()
    expect(edit_button).to_have_attribute("hx-get", "/tasks/1/edit")
    page.wait_for_function("window.htmx !== undefined")
    page.keyboard.press("Enter")
    title_input = edit_title(page)
    expect(title_input).to_be_focused()
    expect(title_input).to_have_value("Original Task")

    title_input.fill("Unsaved Task")
    page.get_by_role("link", name="Cancel editing").press("Enter")

    expect(task_titles(page)).to_have_text(["Original Task"])
    expect(page.get_by_role("button", name="Edit Original Task")).to_be_focused()


def test_save_edit_trims_persists_and_preserves_order(page: Page) -> None:
    add_task(page, "First Task")
    add_task(page, "Second Task")
    expect(task_titles(page)).to_have_text(["Second Task", "First Task"])

    page.get_by_role("button", name="Edit First Task").click()
    title_input = edit_title(page)
    expect(title_input).to_be_focused()
    title_input.fill("   Renamed First Task   ")
    title_input.press("Enter")

    expect(task_titles(page)).to_have_text(["Second Task", "Renamed First Task"])
    expect(page.get_by_role("button", name="Edit Renamed First Task")).to_be_focused()
    page.reload()
    expect(task_titles(page)).to_have_text(["Second Task", "Renamed First Task"])


def test_edit_validation_preserves_input_and_does_not_save(page: Page) -> None:
    add_task(page, "Original Task")
    page.get_by_role("button", name="Edit Original Task").click()
    title_input = edit_title(page)
    expect(title_input).to_be_focused()

    title_input.fill("   ")
    title_input.press("Enter")
    expect(page.get_by_role("alert")).to_have_text("Enter a Task Title.")
    expect(title_input).to_have_value("   ")
    expect(title_input).to_have_attribute("aria-invalid", "true")
    expect(title_input).to_be_focused()

    too_long = "x" * 201
    title_input.fill(too_long)
    page.get_by_role("button", name="Save Task Title").click()
    expect(page.get_by_role("alert")).to_have_text(
        "Task Title must be 200 characters or fewer."
    )
    expect(title_input).to_have_value(too_long)

    page.get_by_role("link", name="Cancel editing").click()
    expect(task_titles(page)).to_have_text(["Original Task"])


def test_missing_task_during_edit_recovers_to_current_list(
    page: Page, tmp_path: Path
) -> None:
    add_task(page, "Task to remove")
    add_task(page, "Task that remains")
    page.get_by_role("button", name="Edit Task to remove").click()
    title_input = edit_title(page)
    expect(title_input).to_be_focused()

    with sqlite3.connect(tmp_path / "tasks.sqlite3") as connection:
        connection.execute("DELETE FROM tasks WHERE title = ?", ("Task to remove",))

    title_input.fill("Cannot save this")
    title_input.press("Enter")

    expect(page.get_by_role("alert")).to_have_text(
        "That Task no longer exists. The current Task List is shown below."
    )
    expect(page.get_by_role("alert")).to_be_focused()
    expect(task_titles(page)).to_have_text(["Task that remains"])

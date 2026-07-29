import urllib.request

from playwright.sync_api import Page, expect


def task_titles(page: Page):
    return page.locator("#task-list [data-task-title]")


def add_task(page: Page, title: str) -> None:
    page.get_by_label("Task Title").fill(title)
    page.get_by_role("button", name="Add Task").click()
    expect(task_titles(page).filter(has_text=title)).to_have_count(1)


def test_complete_restore_filter_persistence_and_stable_order(page: Page) -> None:
    add_task(page, "First Task")
    add_task(page, "Second Task")
    add_task(page, "Third Task")
    expect(task_titles(page)).to_have_text(["Third Task", "Second Task", "First Task"])

    complete = page.get_by_role("button", name="Mark Second Task as Completed")
    complete.focus()
    complete.press("Enter")
    restore = page.get_by_role("button", name="Restore Second Task to Active")
    expect(restore).to_be_focused()
    expect(page.locator('[data-task-status="Completed"] [data-task-title]')).to_have_text(
        "Second Task"
    )
    expect(task_titles(page)).to_have_text(["Third Task", "Second Task", "First Task"])

    page.reload()
    expect(page.locator('[data-task-status="Completed"] [data-task-title]')).to_have_text(
        "Second Task"
    )
    expect(task_titles(page)).to_have_text(["Third Task", "Second Task", "First Task"])

    page.get_by_role("link", name="Active", exact=True).press("Enter")
    active_filter = page.get_by_role("link", name="Active", exact=True)
    expect(active_filter).to_have_attribute("aria-current", "page")
    expect(active_filter).to_be_focused()
    expect(task_titles(page)).to_have_text(["Third Task", "First Task"])

    page.get_by_role("link", name="Completed", exact=True).click()
    completed_filter = page.get_by_role("link", name="Completed", exact=True)
    expect(completed_filter).to_have_attribute("aria-current", "page")
    expect(completed_filter).to_be_focused()
    expect(task_titles(page)).to_have_text(["Second Task"])
    page.reload()
    expect(page).to_have_url(page.url.split("?")[0] + "?filter=completed")
    expect(task_titles(page)).to_have_text(["Second Task"])

    page.get_by_role("button", name="Restore Second Task to Active").press("Enter")
    empty_state = page.locator("[data-task-list-status]")
    expect(page.get_by_text("No Completed Tasks")).to_be_visible()
    expect(empty_state).to_be_focused()
    expect(page).to_have_url(page.url.split("?")[0] + "?filter=completed")

    page.get_by_role("link", name="All", exact=True).click()
    expect(task_titles(page)).to_have_text(["Third Task", "Second Task", "First Task"])
    expect(page.locator('[data-task-status="Active"]')).to_have_count(3)


def test_filter_specific_empty_states_and_unknown_filter_fallback(
    page: Page, app_server: str
) -> None:
    expect(page.get_by_text("Your Task List is empty")).to_be_visible()
    page.get_by_role("link", name="Active", exact=True).click()
    expect(page.get_by_text("No Active Tasks")).to_be_visible()
    page.get_by_role("link", name="Completed", exact=True).click()
    expect(page.get_by_text("No Completed Tasks")).to_be_visible()

    page.goto(app_server + "/?filter=not-a-filter")
    expect(page.get_by_role("link", name="All", exact=True)).to_have_attribute(
        "aria-current", "page"
    )
    expect(page.get_by_text("Your Task List is empty")).to_be_visible()


def test_create_task_preserves_active_filter(page: Page) -> None:
    add_task(page, "Existing Task")
    page.get_by_role("button", name="Mark Existing Task as Completed").click()
    page.get_by_role("link", name="Completed", exact=True).click()

    page.get_by_label("Task Title").fill("New Active Task")
    page.get_by_role("button", name="Add Task").click()

    expect(page).to_have_url(page.url.split("?")[0] + "?filter=completed")
    expect(page.get_by_role("link", name="Completed", exact=True)).to_have_attribute(
        "aria-current", "page"
    )
    expect(task_titles(page)).to_have_text(["Existing Task"])


def test_standard_create_preserves_filter_without_htmx(page: Page) -> None:
    page.get_by_role("link", name="Active", exact=True).click()
    page.evaluate("window.htmx = undefined")
    page.locator("script[src*='htmx']").evaluate("element => element.remove()")

    page.get_by_label("Task Title").fill("Standard Create Task")
    page.get_by_role("button", name="Add Task").click()

    expect(page).to_have_url(page.url.split("?")[0] + "?filter=active")
    expect(task_titles(page)).to_have_text(["Standard Create Task"])


def test_standard_status_form_preserves_filter_without_htmx(page: Page) -> None:
    add_task(page, "Standard Status Task")
    page.get_by_role("link", name="Active", exact=True).click()
    page.evaluate("window.htmx = undefined")
    page.locator("script[src*='htmx']").evaluate("element => element.remove()")

    page.get_by_role("button", name="Mark Standard Status Task as Completed").click()
    expect(page).to_have_url(page.url.split("?")[0] + "?filter=active")
    expect(page.get_by_text("No Active Tasks")).to_be_visible()

    with urllib.request.urlopen(page.url.replace("filter=active", "filter=completed")) as response:
        body = response.read().decode()
    assert "Standard Status Task" in body
    assert "Restore Standard Status Task to Active" in body


def test_invalid_status_uses_full_page_without_htmx(
    page: Page, app_server: str
) -> None:
    add_task(page, "Task with invalid status")
    task_id = page.locator("[data-task-id]").first.get_attribute("data-task-id")
    assert task_id is not None

    endpoint = f"{app_server}/tasks/{task_id}/status"
    form = {"status": "invalid", "filter": "active"}

    standard_response = page.request.post(endpoint, form=form)
    assert standard_response.status == 422
    standard_body = standard_response.text()
    assert "<!doctype html>" in standard_body
    assert "Task List" in standard_body
    assert "Choose a valid Task Status." in standard_body
    assert "Task with invalid status" in standard_body

    htmx_response = page.request.post(
        endpoint,
        form=form,
        headers={"HX-Request": "true"},
    )
    assert htmx_response.status == 422
    htmx_body = htmx_response.text()
    assert "<!doctype html>" not in htmx_body
    assert "Choose a valid Task Status." in htmx_body

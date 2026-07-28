from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from task_list.database import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    migrate,
    update_task_status,
    update_task_title,
)
from task_list.validation import validate_task_title

PACKAGE_PATH = Path(__file__).parent
templates = Jinja2Templates(directory=PACKAGE_PATH / "templates")
FILTER_STATUSES = {"active": "Active", "completed": "Completed"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    yield


app = FastAPI(title="Task List", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PACKAGE_PATH / "static"), name="static")


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def normalize_filter(task_filter: str) -> str:
    return task_filter if task_filter in {"all", *FILTER_STATUSES} else "all"


def filtered_tasks(task_filter: str):
    return list_tasks(FILTER_STATUSES.get(task_filter))


def filter_url(task_filter: str) -> str:
    return "/" if task_filter == "all" else f"/?filter={task_filter}"


def render_task_list(
    request: Request,
    *,
    task_filter: str = "all",
    status_code: int = 200,
    notice: str | None = None,
    include_filters: bool = False,
    focus_filter: bool = False,
    focus_status_task_id: int | None = None,
    focus_delete_task_id: int | None = None,
    focus_list: bool = False,
) -> HTMLResponse:
    task_filter = normalize_filter(task_filter)
    response = templates.TemplateResponse(
        request,
        "_task_view.html" if include_filters else "_task_list.html",
        {
            "tasks": filtered_tasks(task_filter),
            "current_filter": task_filter,
            "notice": notice,
            "focus_filter": focus_filter,
            "focus_status_task_id": focus_status_task_id,
            "focus_delete_task_id": focus_delete_task_id,
            "focus_list": focus_list,
        },
        status_code=status_code,
    )
    if is_htmx(request) and notice:
        response.headers["HX-Retarget"] = "#task-list"
        response.headers["HX-Reswap"] = "innerHTML"
    return response


def render_task_row(
    request: Request,
    task,
    *,
    task_filter: str = "all",
    focus_edit: bool = False,
    focus_delete: bool = False,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "_task_row.html",
        {
            "task": task,
            "current_filter": normalize_filter(task_filter),
            "focus_edit": focus_edit,
            "focus_delete": focus_delete,
        },
    )


def render_missing_task(request: Request, task_filter: str = "all") -> HTMLResponse:
    notice = "That Task no longer exists. The current Task List is shown below."
    if is_htmx(request):
        return render_task_list(request, task_filter=task_filter, notice=notice)
    task_filter = normalize_filter(task_filter)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "tasks": filtered_tasks(task_filter),
            "current_filter": task_filter,
            "title_value": "",
            "error": None,
            "notice": notice,
        },
        status_code=404,
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request, filter: str = "all") -> HTMLResponse:
    task_filter = normalize_filter(filter)
    if is_htmx(request):
        return render_task_list(
            request,
            task_filter=task_filter,
            include_filters=True,
            focus_filter=True,
        )
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "tasks": filtered_tasks(task_filter),
            "current_filter": task_filter,
            "title_value": "",
            "error": None,
        },
    )


@app.post("/tasks", response_class=HTMLResponse)
def add_task(request: Request, title: str = Form(""), filter: str = Form("all")):
    task_filter = normalize_filter(filter)
    trimmed_title, error = validate_task_title(title)
    if error is None:
        create_task(trimmed_title)
        if is_htmx(request):
            return render_task_list(request, task_filter=task_filter)
        return RedirectResponse(url=filter_url(task_filter), status_code=303)

    if is_htmx(request):
        response = templates.TemplateResponse(
            request,
            "_form.html",
            {"title_value": title, "error": error, "current_filter": task_filter},
            status_code=200,
        )
        response.headers["HX-Retarget"] = "#task-form-container"
        response.headers["HX-Reswap"] = "innerHTML"
        return response

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "tasks": filtered_tasks(task_filter),
            "current_filter": task_filter,
            "title_value": title,
            "error": error,
        },
        status_code=422,
    )


@app.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def edit_task(request: Request, task_id: int, filter: str = "all") -> HTMLResponse:
    task_filter = normalize_filter(filter)
    task = get_task(task_id)
    if task is None:
        return render_missing_task(request, task_filter)
    context = {
        "task": task,
        "edit_title_value": task["title"],
        "edit_error": None,
        "current_filter": task_filter,
    }
    if is_htmx(request):
        return templates.TemplateResponse(request, "_task_edit.html", context)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            **context,
            "tasks": filtered_tasks(task_filter),
            "title_value": "",
            "error": None,
            "edit_task": task,
        },
    )


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
def restore_task_row(
    request: Request,
    task_id: int,
    filter: str = "all",
    focus: str = "edit",
) -> HTMLResponse:
    task_filter = normalize_filter(filter)
    task = get_task(task_id)
    if task is None:
        return render_missing_task(request, task_filter)
    return render_task_row(
        request,
        task,
        task_filter=task_filter,
        focus_edit=focus != "delete",
        focus_delete=focus == "delete",
    )


@app.get("/tasks/{task_id}/delete", response_class=HTMLResponse)
def confirm_task_delete(request: Request, task_id: int, filter: str = "all") -> HTMLResponse:
    task_filter = normalize_filter(filter)
    task = get_task(task_id)
    if task is None:
        return render_missing_task(request, task_filter)
    if not is_htmx(request):
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "tasks": filtered_tasks(task_filter),
                "current_filter": task_filter,
                "title_value": "",
                "error": None,
                "delete_task": task,
            },
        )
    response = templates.TemplateResponse(
        request,
        "_task_delete.html",
        {"task": task, "current_filter": task_filter},
    )
    response.headers["HX-Push-Url"] = filter_url(task_filter)
    return response


@app.post("/tasks/{task_id}/delete", response_class=HTMLResponse)
def remove_task(
    request: Request,
    task_id: int,
    filter: str = Form("all"),
):
    task_filter = normalize_filter(filter)
    tasks_before_delete = filtered_tasks(task_filter)
    deleted_index = next(
        (index for index, task in enumerate(tasks_before_delete) if task["id"] == task_id),
        None,
    )
    if not delete_task(task_id):
        return render_missing_task(request, task_filter)
    if is_htmx(request):
        remaining_tasks = filtered_tasks(task_filter)
        focus_task_id = None
        if deleted_index is not None and remaining_tasks:
            focus_index = min(deleted_index, len(remaining_tasks) - 1)
            focus_task_id = remaining_tasks[focus_index]["id"]
        return render_task_list(
            request,
            task_filter=task_filter,
            focus_delete_task_id=focus_task_id,
            focus_list=focus_task_id is None,
        )
    return RedirectResponse(url=filter_url(task_filter), status_code=303)


@app.post("/tasks/{task_id}", response_class=HTMLResponse)
def save_task_title(
    request: Request,
    task_id: int,
    title: str = Form(""),
    filter: str = Form("all"),
):
    task_filter = normalize_filter(filter)
    trimmed_title, error = validate_task_title(title)
    if error is not None:
        task = get_task(task_id)
        if task is None:
            return render_missing_task(request, task_filter)
        context = {
            "task": task,
            "edit_title_value": title,
            "edit_error": error,
            "current_filter": task_filter,
        }
        if is_htmx(request):
            return templates.TemplateResponse(request, "_task_edit.html", context)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                **context,
                "tasks": filtered_tasks(task_filter),
                "title_value": "",
                "error": None,
                "edit_task": task,
            },
            status_code=422,
        )

    task = update_task_title(task_id, trimmed_title)
    if task is None:
        return render_missing_task(request, task_filter)
    if is_htmx(request):
        return render_task_row(request, task, task_filter=task_filter)
    return RedirectResponse(url=filter_url(task_filter), status_code=303)


@app.post("/tasks/{task_id}/status", response_class=HTMLResponse)
def save_task_status(
    request: Request,
    task_id: int,
    status: str = Form(""),
    filter: str = Form("all"),
):
    task_filter = normalize_filter(filter)
    if status not in {"Active", "Completed"}:
        return render_task_list(
            request,
            task_filter=task_filter,
            status_code=422,
            notice="Choose a valid Task Status.",
        )
    task = update_task_status(task_id, status)
    if task is None:
        return render_missing_task(request, task_filter)
    if is_htmx(request):
        task_is_visible = task_filter == "all" or FILTER_STATUSES.get(task_filter) == status
        return render_task_list(
            request,
            task_filter=task_filter,
            focus_status_task_id=task_id if task_is_visible else None,
            focus_list=not task_is_visible,
        )
    return RedirectResponse(url=filter_url(task_filter), status_code=303)

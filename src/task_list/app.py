from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from task_list.database import (
    create_task,
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
) -> HTMLResponse:
    task_filter = normalize_filter(task_filter)
    response = templates.TemplateResponse(
        request,
        "_task_view.html" if include_filters else "_task_list.html",
        {
            "tasks": filtered_tasks(task_filter),
            "current_filter": task_filter,
            "notice": notice,
        },
        status_code=status_code,
    )
    if is_htmx(request) and notice:
        response.headers["HX-Retarget"] = "#task-list"
        response.headers["HX-Reswap"] = "innerHTML"
    return response


def render_task_row(
    request: Request, task, *, task_filter: str = "all", focus_edit: bool = False
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "_task_row.html",
        {"task": task, "current_filter": normalize_filter(task_filter), "focus_edit": focus_edit},
    )


def render_missing_task(request: Request, task_filter: str = "all") -> HTMLResponse:
    return render_task_list(
        request,
        task_filter=task_filter,
        status_code=200 if is_htmx(request) else 404,
        notice="That Task no longer exists. The current Task List is shown below.",
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request, filter: str = "all") -> HTMLResponse:
    task_filter = normalize_filter(filter)
    if is_htmx(request):
        return render_task_list(request, task_filter=task_filter, include_filters=True)
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
    return templates.TemplateResponse(
        request,
        "_task_edit.html",
        {
            "task": task,
            "title_value": task["title"],
            "error": None,
            "current_filter": task_filter,
        },
    )


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
def cancel_task_edit(request: Request, task_id: int, filter: str = "all") -> HTMLResponse:
    task_filter = normalize_filter(filter)
    task = get_task(task_id)
    if task is None:
        return render_missing_task(request, task_filter)
    return render_task_row(request, task, task_filter=task_filter, focus_edit=True)


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
        return templates.TemplateResponse(
            request,
            "_task_edit.html",
            {
                "task": task,
                "title_value": title,
                "error": error,
                "current_filter": task_filter,
            },
            status_code=200 if is_htmx(request) else 422,
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
        return render_task_list(request, task_filter=task_filter)
    return RedirectResponse(url=filter_url(task_filter), status_code=303)

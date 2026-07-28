from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from task_list.database import create_task, get_task, list_tasks, migrate, update_task_title
from task_list.validation import validate_task_title

PACKAGE_PATH = Path(__file__).parent
templates = Jinja2Templates(directory=PACKAGE_PATH / "templates")


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    yield


app = FastAPI(title="Task List", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PACKAGE_PATH / "static"), name="static")


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def render_task_list(
    request: Request, *, status_code: int = 200, notice: str | None = None
) -> HTMLResponse:
    response = templates.TemplateResponse(
        request,
        "_task_list.html",
        {"tasks": list_tasks(), "notice": notice},
        status_code=status_code,
    )
    if is_htmx(request) and notice:
        response.headers["HX-Retarget"] = "#task-list"
        response.headers["HX-Reswap"] = "innerHTML"
    return response


def render_task_row(request: Request, task, *, focus_edit: bool = False) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "_task_row.html", {"task": task, "focus_edit": focus_edit}
    )


def render_missing_task(request: Request) -> HTMLResponse:
    return render_task_list(
        request,
        status_code=200 if is_htmx(request) else 404,
        notice="That Task no longer exists. The current Task List is shown below.",
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"tasks": list_tasks(), "title_value": "", "error": None},
    )


@app.post("/tasks", response_class=HTMLResponse)
def add_task(request: Request, title: str = Form("")):
    trimmed_title, error = validate_task_title(title)
    if error is None:
        create_task(trimmed_title)
        if is_htmx(request):
            return render_task_list(request)
        return RedirectResponse(url="/", status_code=303)

    if is_htmx(request):
        response = templates.TemplateResponse(
            request,
            "_form.html",
            {"title_value": title, "error": error},
            status_code=200,
        )
        response.headers["HX-Retarget"] = "#task-form"
        response.headers["HX-Reswap"] = "outerHTML"
        return response

    return templates.TemplateResponse(
        request,
        "index.html",
        {"tasks": list_tasks(), "title_value": title, "error": error},
        status_code=422,
    )


@app.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def edit_task(request: Request, task_id: int) -> HTMLResponse:
    task = get_task(task_id)
    if task is None:
        return render_missing_task(request)
    return templates.TemplateResponse(
        request,
        "_task_edit.html",
        {"task": task, "title_value": task["title"], "error": None},
    )


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
def cancel_task_edit(request: Request, task_id: int) -> HTMLResponse:
    task = get_task(task_id)
    if task is None:
        return render_missing_task(request)
    return render_task_row(request, task, focus_edit=True)


@app.post("/tasks/{task_id}", response_class=HTMLResponse)
def save_task_title(request: Request, task_id: int, title: str = Form("")):
    trimmed_title, error = validate_task_title(title)
    if error is not None:
        task = get_task(task_id)
        if task is None:
            return render_missing_task(request)
        return templates.TemplateResponse(
            request,
            "_task_edit.html",
            {"task": task, "title_value": title, "error": error},
            status_code=200 if is_htmx(request) else 422,
        )

    task = update_task_title(task_id, trimmed_title)
    if task is None:
        return render_missing_task(request)
    if is_htmx(request):
        return render_task_row(request, task)
    return RedirectResponse(url="/", status_code=303)

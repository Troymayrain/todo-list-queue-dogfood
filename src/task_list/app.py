from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from task_list.database import create_task, list_tasks, migrate

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


def render_task_list(request: Request, *, status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "_task_list.html",
        {"tasks": list_tasks()},
        status_code=status_code,
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
    trimmed_title = title.strip()
    if not trimmed_title:
        error = "Enter a Task Title."
    elif len(trimmed_title) > 200:
        error = "Task Title must be 200 characters or fewer."
    else:
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

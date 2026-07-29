import os
import socket
import subprocess
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = PROJECT_ROOT / "test-results"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch()
        yield instance
        instance.close()


@pytest.fixture
def app_server(tmp_path: Path) -> Iterator[str]:
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["TASK_LIST_DATABASE"] = str(tmp_path / "tasks.sqlite3")
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "task_list.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            pytest.fail(f"Application exited during startup:\n{output}")
        try:
            with urllib.request.urlopen(base_url, timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    else:
        process.terminate()
        output = process.communicate(timeout=5)[0]
        pytest.fail(f"Application did not start:\n{output}")

    yield base_url

    process.terminate()
    try:
        output = process.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        process.kill()
        output = process.communicate()[0]
    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / "server.log").write_text(output)


@pytest.fixture
def page(browser: Browser, app_server: str, request: pytest.FixtureRequest) -> Iterator[Page]:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    current_page = context.new_page()
    current_page.goto(app_server)
    yield current_page

    if request.node.rep_call.failed:
        ARTIFACTS.mkdir(exist_ok=True)
        name = request.node.name
        current_page.screenshot(path=ARTIFACTS / f"{name}.png", full_page=True)
        (ARTIFACTS / f"{name}.html").write_text(current_page.content())
    context.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

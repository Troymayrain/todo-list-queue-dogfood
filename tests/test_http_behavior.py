import urllib.error
import urllib.parse
import urllib.request


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def post(base_url: str, title: str, *, htmx: bool = False):
    headers = {"HX-Request": "true"} if htmx else {}
    request = urllib.request.Request(
        base_url + "/tasks",
        data=urllib.parse.urlencode({"title": title}).encode(),
        headers=headers,
        method="POST",
    )
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        return opener.open(request)
    except urllib.error.HTTPError as error:
        return error


def test_standard_submission_redirects_after_post(app_server: str) -> None:
    response = post(app_server, "Standard Task")
    assert response.status == 303
    assert response.headers["Location"] == "/"


def test_htmx_success_returns_partial_and_validation_retargets_form(app_server: str) -> None:
    success = post(app_server, "  HTMX Task  ", htmx=True)
    body = success.read().decode()
    assert success.status == 200
    assert "HTMX Task" in body
    assert "<!doctype html>" not in body

    invalid = post(app_server, "   ", htmx=True)
    body = invalid.read().decode()
    assert invalid.status == 200
    assert invalid.headers["HX-Retarget"] == "#task-form"
    assert invalid.headers["HX-Reswap"] == "outerHTML"
    assert 'value="   "' in body
    assert "Enter a Task Title." in body

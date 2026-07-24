# tests/test_api.py
# Integration tests for the POST /api/audit endpoint.
# Network calls are mocked so these tests are fast, deterministic, and
# run without internet access (no real site has to be up for CI to pass).

from unittest.mock import MagicMock, patch

import requests

from app import app


def make_response(status_code=200, html="<html></html>", content_type="text/html"):
    """Build a fake requests.Response-like object for mocking session.get()."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 400
    resp.text = html
    resp.headers = {"content-type": content_type}
    return resp


class TestAuditEndpoint:
    def setup_method(self):
        self.client = app.test_client()

    # ---- happy path ----

    @patch("requests.Session.get")
    def test_happy_path_returns_full_report(self, mock_get):
        html = """
            <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="A page for testing">
            </head>
            <body>
                <h1>Welcome</h1>
                <img src="a.png" alt="a cat">
                <img src="b.png">
                <p>some visible words here for counting purposes</p>
            </body>
            </html>
        """
        mock_get.return_value = make_response(status_code=200, html=html)

        res = self.client.post("/api/audit", json={"url": "https://example.com"})
        data = res.get_json()

        assert res.status_code == 200
        assert data["httpStatus"] == 200
        assert data["ok"] is True
        assert data["title"] == "Test Page"
        assert data["metaDescription"] == "A page for testing"
        assert data["h1Count"] == 1
        assert data["imagesMissingAlt"] == 1
        assert data["wordCount"] > 0
        assert "responseTimeMs" in data

    # ---- failure case 1: invalid URL never reaches the network ----

    @patch("requests.Session.get")
    def test_invalid_url_returns_400_without_making_a_request(self, mock_get):
        res = self.client.post("/api/audit", json={"url": "not a url"})
        data = res.get_json()

        assert res.status_code == 400
        assert data["error"] == "invalid_url"
        mock_get.assert_not_called()  # should fail fast, before any fetch attempt

    # ---- failure case 2: target site times out ----

    @patch("requests.Session.get")
    def test_timeout_returns_408(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()

        res = self.client.post("/api/audit", json={"url": "https://slow-site.example"})
        data = res.get_json()

        assert res.status_code == 408
        assert data["error"] == "timeout"

    # ---- failure case 3: DNS / connection failure ----

    @patch("requests.Session.get")
    def test_unreachable_host_returns_502(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()

        res = self.client.post("/api/audit", json={"url": "https://this-should-not-resolve.invalid"})
        data = res.get_json()

        assert res.status_code == 502
        assert data["error"] == "fetch_failed"

    # ---- failure case 4: non-HTML response ----

    @patch("requests.Session.get")
    def test_non_html_response_returns_422(self, mock_get):
        mock_get.return_value = make_response(
            status_code=200, html="raw text file contents", content_type="text/plain"
        )

        res = self.client.post("/api/audit", json={"url": "https://example.com/file.txt"})
        data = res.get_json()

        assert res.status_code == 422
        assert data["error"] == "non_html_response"

    # ---- missing body ----

    def test_missing_url_field_returns_400(self):
        res = self.client.post("/api/audit", json={})
        data = res.get_json()

        assert res.status_code == 400
        assert data["error"] == "invalid_url"

    # ---- app never crashes on an unknown route ----

    def test_unknown_route_returns_clean_404_not_500(self):
        res = self.client.get("/favicon.ico")
        assert res.status_code == 404

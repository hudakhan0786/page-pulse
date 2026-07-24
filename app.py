# Page Pulse — backend (Python / Flask)
# Small Flask API that audits a given URL: HTTP status, response time,
# title, meta description, H1 count, images missing alt text, word count.

import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

FETCH_TIMEOUT_SECONDS = 8
MAX_REDIRECTS = 5
USER_AGENT = "Mozilla/5.0 (compatible; PagePulseBot/1.0; +https://digitalheroesco.com)"


def parse_and_validate_url(raw):
    """Validate a string as an http/https URL. Returns a normalized URL string or None."""
    if not raw or not isinstance(raw, str):
        return None
    candidate = raw.strip()
    if not re.match(r"^https?://", candidate, re.IGNORECASE):
        candidate = "https://" + candidate  # be forgiving: "example.com" -> "https://example.com"
    try:
        parsed = urlparse(candidate)
        if parsed.scheme not in ("http", "https"):
            return None
        if not parsed.netloc or "." not in parsed.netloc:
            return None
        return candidate
    except Exception:
        return None


def count_words(soup):
    """Rough word count: strip script/style, collapse whitespace, split."""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return 0
    return len(text.split(" "))


def count_images_missing_alt(soup):
    missing = 0
    for img in soup.find_all("img"):
        alt = img.get("alt")
        if alt is None or alt.strip() == "":
            missing += 1
    return missing


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/audit", methods=["POST"])
def audit():
    body = request.get_json(silent=True) or {}
    raw_url = body.get("url")

    url = parse_and_validate_url(raw_url)
    if not url:
        return jsonify({
            "error": "invalid_url",
            "message": "Please provide a valid http(s) URL, e.g. https://example.com",
        }), 400

    started = time.time()

    try:
        session = requests.Session()
        session.max_redirects = MAX_REDIRECTS
        response = session.get(
            url,
            timeout=FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            allow_redirects=True,
        )
    except requests.exceptions.Timeout:
        return jsonify({
            "error": "timeout",
            "message": f"The page did not respond within {FETCH_TIMEOUT_SECONDS}s.",
        }), 408
    except requests.exceptions.RequestException:
        # DNS failure, connection refused, TLS error, etc.
        return jsonify({
            "error": "fetch_failed",
            "message": "Could not reach that URL. Check the address and try again.",
        }), 502

    response_time_ms = round((time.time() - started) * 1000)
    content_type = response.headers.get("content-type", "")

    if "text/html" not in content_type:
        return jsonify({
            "error": "non_html_response",
            "message": f'That URL returned "{content_type.split(";")[0] or "unknown content"}", not an HTML page.',
            "httpStatus": response.status_code,
            "responseTimeMs": response_time_ms,
        }), 422

    try:
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception:
        return jsonify({
            "error": "parse_failed",
            "message": "The page's HTML could not be parsed.",
            "httpStatus": response.status_code,
            "responseTimeMs": response_time_ms,
        }), 422

    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag and title_tag.get_text().strip() else None

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = None
    if meta_desc_tag and meta_desc_tag.get("content"):
        meta_description = meta_desc_tag.get("content").strip() or None

    h1_count = len(soup.find_all("h1"))
    images_missing_alt = count_images_missing_alt(soup)
    word_count = count_words(soup)

    return jsonify({
        "url": url,
        "httpStatus": response.status_code,
        "ok": response.ok,
        "responseTimeMs": response_time_ms,
        "title": title,
        "metaDescription": meta_description,
        "h1Count": h1_count,
        "imagesMissingAlt": images_missing_alt,
        "wordCount": word_count,
    }), 200


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    # Let normal HTTP errors (404, 405, etc.) pass through as-is —
    # only catch genuinely unexpected server-side failures.
    if isinstance(err, HTTPException):
        return err
    app.logger.exception("Unhandled error")
    return jsonify({
        "error": "internal_error",
        "message": "Something went wrong on our end.",
    }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)

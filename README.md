# Page Pulse (Python / Flask)

A small full-stack tool that audits any URL: HTTP status, response time, page
title, meta description, H1 count, images missing `alt` text, and approximate
word count.

**Live demo:** _add your deployed URL here_
**Repo:** _add your GitHub URL here_

## Stack

- **Backend:** Python + Flask, `requests` for fetching, `BeautifulSoup4` for
  HTML parsing. No headless browser needed — fast and cheap on a free tier.
- **Frontend:** single static HTML/CSS/vanilla JS page, served by Flask
  itself (`templates/index.html`), so there's only one process to deploy.

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:3000`.

## API

### `POST /api/audit`

**Request body**

```json
{ "url": "https://example.com" }
```

**Success response — `200`**

```json
{
  "url": "https://example.com",
  "httpStatus": 200,
  "ok": true,
  "responseTimeMs": 312,
  "title": "Example Domain",
  "metaDescription": null,
  "h1Count": 1,
  "imagesMissingAlt": 0,
  "wordCount": 28
}
```

**Error responses**

| Status | `error`             | When                                              |
| ------ | ------------------- | -------------------------------------------------- |
| 400    | `invalid_url`       | Missing/malformed URL                              |
| 408    | `timeout`           | Target didn't respond within 8s                    |
| 422    | `non_html_response` | Content-Type isn't `text/html`                     |
| 422    | `parse_failed`      | HTML body couldn't be parsed                       |
| 502    | `fetch_failed`      | DNS failure, connection refused, TLS error, etc.   |
| 500    | `internal_error`    | Unexpected server error (caught, never a crash)    |

All errors return `{ "error": "...", "message": "human-readable string" }`.

## Deploying (free tier — Render)

1. Push this repo to GitHub (public).
2. Go to [render.com](https://render.com) → **New** → **Web Service** →
   connect your GitHub repo.
3. Settings:
   - **Language:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Instance Type:** Free
4. Deploy. Render gives you a public URL like
   `https://page-pulse-xxxx.onrender.com`.
5. Note: on Render's free tier the service sleeps after inactivity, so the
   first request after a while can take ~30-50s to wake up.

## Notes on design choices

- `requests` + `BeautifulSoup` instead of a headless browser (Selenium/
  Playwright) — enough for static HTML analysis, faster cold starts, avoids
  memory limits that break free-tier deploys.
- 8-second timeout on the fetch so a hung target site can't hang the API.
- URL input is normalized (`example.com` → `https://example.com`) for a
  friendlier UX, but still validated as a proper URL before fetching.
- `gunicorn` is used in production (via the `Procfile`) instead of Flask's
  built-in dev server, which isn't meant for real traffic.

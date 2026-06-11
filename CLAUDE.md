# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the poster (posts one article to Facebook now)
py daily_poster.py

# Dry run — generate post + overlay image, save to _dry_run_preview.jpg, no actual post
py daily_poster.py --dry-run

# Dashboard (Flask, localhost:5000)
py app.py

# Install dependencies
pip install -r requirements.txt
```

**Note**: This machine uses `py` not `python`. GitHub Actions uses `python`.

GitHub Actions runs `daily_poster.py` every 3 hours (`0 */3 * * *`) and commits `posted.json` back to the repo after each run. Trigger manually from GitHub UI via `workflow_dispatch`.

## Architecture

### Posting Pipeline (`daily_poster.py`)

Orchestrates the full flow:
1. Loads `posted.json` (last 30 posted entries with embeddings + engagement metrics)
2. Calls `refresh_metrics()` — fetches likes/reactions/comments/shares/views/clicks from Graph API for posts 6+ hours old; saves back to `posted.json` if changed
3. Calls `content_writer.write_post_with_search()` → returns `(post_text, source_url, topic_label)`
4. Resolves redirect URLs; filters out `vertexaisearch.cloud.google.com` grounding redirects
5. Scrapes OG image from the source page (`og:image` / `twitter:image`)
6. If OG image found: calls `content_writer.generate_overlay_text()` → composites image via `image_overlay.compose()`
7. Posts to Facebook Graph API via **2-step** (image posts):
   - Step 1: `POST /{PAGE_ID}/photos` with `published=false` + `source` file → get `photo_id`
   - Step 2: `POST /{PAGE_ID}/feed` with `message` + `attached_media=[{"media_fbid": photo_id}]` → appears in News Feed
   - Without image: plain POST to `/{PAGE_ID}/feed`
8. Saves entry to `posted.json` (url, topic, embedding, post_id)

**Important**: Use 2-step upload+feed approach. Posting directly to `/photos` with `published=true` causes posts to appear only in Photos tab, not in followers' News Feed.

### Content Generation (`content_writer.py`)

Uses two Gemini models:
- `gemini-3.5-flash` (`GENERATE_MODEL`) — generates the Facebook post with Google Search grounding
- `gemini-3.1-flash-lite` (`UTIL_MODEL`) — topic label, overlay headline/subtitle, LLM dedup check
- `text-embedding-004` — cosine similarity dedup

**Dedup system** (3 attempts before giving up):
- Cosine similarity ≥ 0.92 → hard reject
- Cosine similarity ≥ 0.65 → LLM check (`_is_duplicate()`)
- Avoid block injected into prompt lists recent topics

**URL retry**: If grounding returns no URL, retries once with explicit source instruction. Retry post is dedup-checked before replacing original.

**Engagement hint**: `_build_engagement_hint()` computes score per post (`views×0.1 + reactions + comments×2 + shares×3 + clicks×1.5`) and injects top 3 topics into the prompt so Gemini gravitates toward similar content.

**Retry**: `_with_retry()` catches `ServerError`, `httpx.ReadError`, `httpx.ConnectError`, `httpx.RemoteProtocolError` with delays `[30, 60, 120, 180, 300, 300, 300, 300]s`. Model fallback order: `gemini-3.5-flash` → `gemini-3.1-flash` → `gemini-3.1-flash-lite`.

Source URL extracted from `grounding_metadata.grounding_chunks` (first web URI).

### Image Overlay (`image_overlay.py`)

Composites a 1080×1350 JPEG:
- Photo fills full canvas (scaled + center-cropped); landscape images get blurred background
- Smooth gradient overlay fades in from `GRADIENT_START_Y=700` → fully opaque at `GRADIENT_END_Y=1050`
- Overlay color sampled from bottom 30% of photo (darkened 75%) — dynamic per image
- Headline (Prompt Bold 72px) + subtitle with orange accent bar (Prompt Regular 38px)
- Logo watermark (`logo.jpg`) at bottom-right, 78px
- Font: `fonts/Prompt-Bold.ttf` / `fonts/Prompt-Regular.ttf` (OFL, bundled in repo)
- Falls back gracefully: if compose fails, posts OG URL or text-only

### Engagement Metrics (`daily_poster.py` → `refresh_metrics()`)

Runs at the start of every `post_one()` call. For each `posted.json` entry with a `post_id` that is 6+ hours old and hasn't been refreshed in 6+ hours:
- Fetches `reactions, comments, shares` via `GET /{post_id}?fields=...`
- Fetches `post_impressions_unique, post_clicks` via `GET /{post_id}/insights` (requires `pages_read_insights` permission)
- Saves metrics back to the entry; marks `metrics_refreshed_at`

### Other Files

- `news_fetcher.py` — RSS feed fetcher (unused; pipeline uses Gemini Search grounding)
- `poster.py` — low-level Graph API wrappers (reference; `daily_poster.py` calls Graph API directly)
- `config.py` — reads all secrets from env vars / `.env`
- `app.py` — Flask dashboard at `localhost:5000`; `/api/data` returns page stats + last 9 posts with insights (5 min cache)
- `fonts/` — Prompt Bold/Regular + Sarabun Bold/Regular (OFL); `logo.jpg` — page watermark

### Secrets (GitHub Actions / `.env`)

`PAGE_ID`, `PAGE_ACCESS_TOKEN`, `APP_ID`, `APP_SECRET`, `GEMINI_API_KEY`

`PAGE_ACCESS_TOKEN` requires permissions: `pages_manage_posts`, `pages_read_engagement`, `pages_read_insights` (for views/clicks). Token is a long-lived Page Access Token (non-expiring when generated from a long-lived User Token).

### CI (`.github/workflows/post.yml`)

Installs `libraqm0` via apt before pip — required for correct Thai text shaping with Pillow on Ubuntu.

## Key Constraints

- `posted.json` is version-controlled; the workflow commits it after each run. Never reset or truncate manually — it's the live dedup history (last 30 entries with embeddings + metrics).
- Post URL appended to body as `อ่านต่อ: <url>` — cannot use `link` param (OAuth scope limitation) or comments (`pages_manage_engagement` not available).
- Gemini grounding URLs pointing to `vertexaisearch.cloud.google.com` are filtered to empty string (treated as no URL).
- Post content prompt forbids mentioning the URL directly — only the appended suffix carries it.
- `sys.stdout.reconfigure(encoding='utf-8')` is set at the top of `daily_poster.py` — required for Thai output on Windows terminals (cp1252 default).

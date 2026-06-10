# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the poster (posts one article to Facebook now)
python daily_poster.py

# Dry run — generate and preview post without posting
python daily_poster.py --dry-run

# Dashboard (Flask, localhost:5000)
python app.py

# Install dependencies
pip install -r requirements.txt
```

GitHub Actions runs `daily_poster.py` every 3 hours (`0 */3 * * *`) and commits `posted.json` back to the repo after each run. Trigger manually from GitHub UI via `workflow_dispatch`.

## Architecture

### Posting Pipeline (`daily_poster.py`)

Orchestrates the full flow:
1. Loads `posted.json` (last 30 posted entries with embeddings)
2. Calls `content_writer.write_post_with_search()` → returns `(post_text, source_url, topic_label)`
3. Resolves redirect URLs; filters out `vertexaisearch.cloud.google.com` grounding redirects
4. Scrapes OG image from the source page (`og:image` / `twitter:image`)
5. Posts to Facebook Graph API v22.0:
   - With image: upload photo as unpublished → attach via `attached_media[0]` on feed post
   - Without image: plain feed post with link appended to message body
6. Saves entry to `posted.json` (url, topic, embedding, post_id)

### Content Generation (`content_writer.py`)

Uses two Gemini models:
- `gemini-3.5-flash` (`GENERATE_MODEL`) — generates the Facebook post with Google Search grounding
- `gemini-3.1-flash-lite` (`UTIL_MODEL`) — topic label extraction and LLM dedup check
- `text-embedding-004` — cosine similarity dedup

**Dedup system** (3 attempts before giving up):
- Cosine similarity ≥ 0.92 → hard reject (near-identical content)
- Cosine similarity ≥ 0.65 → LLM check (`_is_duplicate()`) to confirm
- Avoid block injected into prompt lists recent topics to steer Gemini away

**Retry on 503**: `_with_retry()` wraps Gemini calls with delays `[30, 60, 120, 180, 300]s`.

Source URL extracted from `grounding_metadata.grounding_chunks` (first web URI).

### Other Files

- `news_fetcher.py` — RSS feed fetcher (not used in current pipeline; `daily_poster.py` uses Gemini Search grounding instead)
- `poster.py` — low-level Graph API wrappers (`post_text`, `post_with_image`, `post_with_local_image`)
- `config.py` — reads all secrets from env vars / `.env`
- `app.py` — Flask dashboard; `/api/data` returns page stats + last 9 posts with insights (cached 5 min)
- `scheduler.py`, `token_checker.py`, `refresh_token.py` — utility scripts

### Secrets (GitHub Actions / `.env`)

`PAGE_ID`, `PAGE_ACCESS_TOKEN`, `APP_ID`, `APP_SECRET`, `GEMINI_API_KEY`

## Key Constraints

- `posted.json` is version-controlled; the workflow commits it after each run. Never reset or truncate it manually — it's the live dedup history.
- OG image is posted via `attached_media[0]` (not the `link` param) due to a Facebook OAuth permission limitation with the `link` field.
- Post content must not mention the source URL (the prompt explicitly forbids it); the URL is appended separately as `อ่านต่อ: <url>`.
- Gemini grounding URLs that point to `vertexaisearch.cloud.google.com` are filtered out and treated as no URL.

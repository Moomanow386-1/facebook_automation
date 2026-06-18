"""
Usage:
  python daily_poster.py          -- post now
  python daily_poster.py --dry-run -- preview without posting
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json
import os
import requests
from bs4 import BeautifulSoup
from content_writer import write_post_with_search, _get_embedding, generate_overlay_text
from image_overlay import compose as compose_overlay
from config import PAGE_ID, PAGE_ACCESS_TOKEN, BASE_URL

POSTED_FILE = "posted.json"


def load_posted_history() -> list[dict]:
    if not os.path.exists(POSTED_FILE):
        return []
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [item for item in data if isinstance(item, dict)]


def save_posted_entry(url: str, topic: str, embedding: list[float] | None = None, post_id: str | None = None):
    from datetime import datetime, timezone
    data = []
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for item in raw:
            if isinstance(item, dict):
                data.append(item)
    entry = {
        "url": url,
        "topic": topic,
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }
    if post_id:
        entry["post_id"] = post_id
    if embedding:
        entry["embedding"] = embedding
    data.append(entry)
    data = data[-30:]
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_url(url: str) -> str:
    if not url:
        return url
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        final = res.url
        if "vertexaisearch.cloud.google.com" in final:
            return ""
        return final
    except Exception:
        return url



def get_og_image(url: str) -> str | None:
    if not url:
        return None
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"})
        print(f"[og] status={res.status_code} url={url[:80]}")
        soup = BeautifulSoup(res.text, "html.parser")
        tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if tag:
            img = tag.get("content")
            print(f"[og] found: {img[:80] if img else None}")
            return img
        print("[og] no og:image/twitter:image tag found")
    except Exception as e:
        print(f"[og] error: {e}")
    return None


def post_comment(post_id: str, message: str):
    res = requests.post(
        f"{BASE_URL}/{post_id}/comments",
        data={"message": message, "access_token": PAGE_ACCESS_TOKEN},
    )
    if res.status_code == 200:
        print(f"Comment posted OK")
    else:
        print(f"Comment skipped (permission not available)")


def refresh_metrics(data: list[dict]) -> tuple[list[dict], bool]:
    """Fetch likes/comments/shares for posts that are 6+ hours old and not yet refreshed."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    changed = False
    for entry in data:
        post_id = entry.get("post_id")
        if not post_id:
            continue
        posted_at = entry.get("posted_at")
        if posted_at:
            try:
                post_dt = datetime.fromisoformat(posted_at)
                if (now - post_dt).total_seconds() < 6 * 3600:
                    continue
            except Exception:
                pass
        last_refresh = entry.get("metrics_refreshed_at")
        if last_refresh:
            try:
                refresh_dt = datetime.fromisoformat(last_refresh)
                if (now - refresh_dt).total_seconds() < 6 * 3600:
                    continue
            except Exception:
                pass
        try:
            res = requests.get(
                f"{BASE_URL}/{post_id}",
                params={
                    "fields": "reactions.summary(true),comments.summary(true),shares",
                    "access_token": PAGE_ACCESS_TOKEN,
                },
                timeout=10,
            )
            if res.status_code == 200:
                d = res.json()
                entry["reactions"] = d.get("reactions", {}).get("summary", {}).get("total_count", 0)
                entry["comments"] = d.get("comments", {}).get("summary", {}).get("total_count", 0)
                entry["shares"] = d.get("shares", {}).get("count", 0)
            # fetch impressions + clicks from insights — requires pages_read_insights
            ins_res = requests.get(
                f"{BASE_URL}/{post_id}/insights",
                params={
                    "metric": "post_impressions_unique,post_clicks",
                    "period": "lifetime",
                    "access_token": PAGE_ACCESS_TOKEN,
                },
                timeout=10,
            )
            if ins_res.status_code == 200:
                for item in ins_res.json().get("data", []):
                    val = item.get("values", [{}])[-1].get("value", 0)
                    if item.get("name") == "post_impressions_unique":
                        entry["views"] = val
                    elif item.get("name") == "post_clicks":
                        entry["clicks"] = val
            entry["metrics_refreshed_at"] = now.isoformat()
            changed = True
            print(f"[metrics] {post_id}: views={entry.get('views','?')} reactions={entry.get('reactions',0)} comments={entry.get('comments',0)} shares={entry.get('shares',0)} clicks={entry.get('clicks','?')}")
        except Exception as e:
            print(f"[metrics] failed for {post_id}: {e}")
    return data, changed


def sync_manual_posts(posted_history: list[dict]) -> tuple[list[dict], bool]:
    """Fetch recent page posts from Facebook and add any not in posted_history."""
    from content_writer import _get_embedding, _extract_topic_label
    known_ids = {e.get("post_id") for e in posted_history if e.get("post_id")}
    try:
        res = requests.get(
            f"{BASE_URL}/{PAGE_ID}/posts",
            params={"fields": "id,message,created_time", "limit": 10, "access_token": PAGE_ACCESS_TOKEN},
        )
        if res.status_code != 200:
            return posted_history, False
        posts = res.json().get("data", [])
    except Exception:
        return posted_history, False

    changed = False
    from datetime import datetime, timezone
    for post in posts:
        pid = post.get("id")
        if not pid or pid in known_ids:
            continue
        message = post.get("message", "").strip()
        if not message:
            continue
        print(f"[sync] found untracked manual post {pid}, adding to dedup history...")
        embedding = _get_embedding(message)
        topic = _extract_topic_label(message)
        entry = {
            "url": "",
            "topic": topic,
            "posted_at": post.get("created_time", datetime.now(timezone.utc).isoformat()),
            "post_id": pid,
            "manual": True,
        }
        if embedding:
            entry["embedding"] = embedding
        posted_history.append(entry)
        posted_history = posted_history[-30:]
        changed = True

    return posted_history, changed


def post_one(dry_run: bool = False):
    print("Searching for latest tech news...")
    posted_history = load_posted_history()
    posted_history, metrics_changed = refresh_metrics(posted_history)
    posted_history, sync_changed = sync_manual_posts(posted_history)
    if metrics_changed or sync_changed:
        with open(POSTED_FILE, "w", encoding="utf-8") as f:
            json.dump(posted_history, f, ensure_ascii=False, indent=2)
        print("[metrics] posted.json updated with engagement data")
    content, url, topic_label = write_post_with_search(posted_history)

    real_url = resolve_url(url)
    full_content = f"{content}\n\nอ่านต่อ: {real_url}" if real_url else content

    print("\n=== GENERATED POST ===")
    print(full_content)
    print("======================")

    if not real_url:
        print("[warn] no URL from grounding — posting text-only")

    og_image = get_og_image(real_url) if real_url else None

    if not og_image:
        print("[warn] no OG image — posting text-only")

    # Build overlay image if OG image exists
    composed_buf = None
    if og_image:
        headline, subtitle = generate_overlay_text(content)
        print(f"[overlay] headline: {headline}")
        print(f"[overlay] subtitle: {subtitle}")
        composed_buf = compose_overlay(og_image, headline, subtitle)
        if not composed_buf:
            print("[overlay] compose failed, will fall back to OG URL")

    if dry_run:
        if composed_buf:
            with open("_dry_run_preview.jpg", "wb") as f:
                f.write(composed_buf.read())
            print("\n[DRY RUN] overlay saved → _dry_run_preview.jpg")
        else:
            print("\n[DRY RUN] no image overlay")
        return

    if og_image:
        photo_id = None
        if composed_buf:
            # Step 1: upload photo silently (published=false keeps it off Photos tab)
            upload = requests.post(
                f"{BASE_URL}/{PAGE_ID}/photos",
                data={"published": "false", "access_token": PAGE_ACCESS_TOKEN},
                files={"source": ("post.jpg", composed_buf, "image/jpeg")},
            )
            if upload.status_code == 200:
                photo_id = upload.json().get("id")
        elif og_image:
            # Upload OG image by URL silently
            upload = requests.post(
                f"{BASE_URL}/{PAGE_ID}/photos",
                data={"url": og_image, "published": "false", "access_token": PAGE_ACCESS_TOKEN},
            )
            if upload.status_code == 200:
                photo_id = upload.json().get("id")

        if photo_id:
            # Step 2: create a feed post with the photo attached — appears in News Feed
            res = requests.post(
                f"{BASE_URL}/{PAGE_ID}/feed",
                data={
                    "message": full_content,
                    "attached_media": json.dumps([{"media_fbid": photo_id}]),
                    "access_token": PAGE_ACCESS_TOKEN,
                },
            )
        else:
            print("[post] photo upload failed, falling back to text post")
            res = requests.post(
                f"{BASE_URL}/{PAGE_ID}/feed",
                data={"message": full_content, "access_token": PAGE_ACCESS_TOKEN},
            )
        if res.status_code != 200:
            print(f"Photo post failed: {res.json()}, falling back to text post")
            res = requests.post(
                f"{BASE_URL}/{PAGE_ID}/feed",
                data={"message": full_content, "access_token": PAGE_ACCESS_TOKEN},
            )
    else:
        res = requests.post(
            f"{BASE_URL}/{PAGE_ID}/feed",
            data={"message": full_content, "published": "true", "access_token": PAGE_ACCESS_TOKEN},
        )
    post_id = res.json().get("id")

    if res.status_code == 200:
        print(f"Posted! ID: {post_id}")
        if post_id:
            detail = requests.get(
                f"{BASE_URL}/{post_id}",
                params={"fields": "privacy,is_published,timeline_visibility", "access_token": PAGE_ACCESS_TOKEN},
            )
            print(f"Post detail: {detail.json()}")
        embedding = _get_embedding(content)
        save_posted_entry(real_url, topic_label, embedding, post_id=post_id)
    else:
        print(f"Error {res.status_code}: {res.json()}")


def add_manual_post(text: str, url: str = "", topic: str = ""):
    """Add a manually-written post to posted.json so the bot won't duplicate it."""
    from content_writer import _get_embedding, _extract_topic_label
    print("[manual] Generating embedding...")
    embedding = _get_embedding(text)
    if not topic:
        topic = _extract_topic_label(text)
    save_posted_entry(url, topic, embedding, post_id=None)
    print(f"[manual] Saved to posted.json — topic: {topic}")


if __name__ == "__main__":
    if "--add-manual" in sys.argv:
        idx = sys.argv.index("--add-manual")
        manual_text = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not manual_text:
            print("Usage: py daily_poster.py --add-manual \"<post text>\" [--url <url>]")
            sys.exit(1)
        manual_url = ""
        if "--url" in sys.argv:
            u_idx = sys.argv.index("--url")
            manual_url = sys.argv[u_idx + 1] if u_idx + 1 < len(sys.argv) else ""
        add_manual_post(manual_text, url=manual_url)
    else:
        dry_run = "--dry-run" in sys.argv
        post_one(dry_run=dry_run)

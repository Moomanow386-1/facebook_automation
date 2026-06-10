"""
Usage:
  python daily_poster.py          -- post now
  python daily_poster.py --dry-run -- preview without posting
"""
import sys
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
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
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


def post_one(dry_run: bool = False):
    print("Searching for latest tech news...")
    posted_history = load_posted_history()
    content, url, topic_label = write_post_with_search(posted_history)

    real_url = resolve_url(url)
    full_content = f"{content}\n\nอ่านต่อ: {real_url}" if real_url else content

    print("\n=== GENERATED POST ===")
    print(full_content)
    print("======================")

    og_image = get_og_image(real_url) if real_url else None

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
        if composed_buf:
            # Upload composed image as file
            upload = requests.post(
                f"{BASE_URL}/{PAGE_ID}/photos",
                data={"published": "false", "access_token": PAGE_ACCESS_TOKEN},
                files={"source": ("post.jpg", composed_buf, "image/jpeg")},
            )
        else:
            # Fallback: upload OG image by URL
            upload = requests.post(
                f"{BASE_URL}/{PAGE_ID}/photos",
                data={"url": og_image, "published": "false", "access_token": PAGE_ACCESS_TOKEN},
            )
        photo_id = upload.json().get("id")
        if photo_id:
            res = requests.post(
                f"{BASE_URL}/{PAGE_ID}/feed",
                data={
                    "message": full_content,
                    "attached_media[0]": json.dumps({"media_fbid": photo_id}),
                    "published": "true",
                    "access_token": PAGE_ACCESS_TOKEN,
                },
            )
        else:
            print(f"Photo upload failed: {upload.json()}, falling back to text post")
            res = requests.post(
                f"{BASE_URL}/{PAGE_ID}/feed",
                data={"message": full_content, "published": "true", "access_token": PAGE_ACCESS_TOKEN},
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


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    post_one(dry_run=dry_run)

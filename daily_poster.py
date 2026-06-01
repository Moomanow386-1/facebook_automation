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
from content_writer import write_post_with_search, _get_embedding
from config import PAGE_ID, PAGE_ACCESS_TOKEN, BASE_URL

POSTED_FILE = "posted.json"


def load_posted_history() -> list[dict]:
    if not os.path.exists(POSTED_FILE):
        return []
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [item for item in data if isinstance(item, dict)]


def save_posted_entry(url: str, topic: str, embedding: list[float] | None = None):
    data = []
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for item in raw:
            if isinstance(item, dict):
                data.append(item)
    entry = {"url": url, "topic": topic}
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
        if "vertexaisearch" in final or "grounding-api-redirect" in final:
            return ""
        return final
    except Exception:
        return url


def get_og_image(url: str) -> str | None:
    if not url:
        return None
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if tag:
            return tag.get("content")
    except Exception:
        pass
    return None


def post_comment(post_id: str, message: str):
    res = requests.post(
        f"{BASE_URL}/{post_id}/comments",
        data={"message": message, "access_token": PAGE_ACCESS_TOKEN},
    )
    print(f"Comment status {res.status_code}: {res.json()}")


def post_one(dry_run: bool = False):
    print("Searching for latest tech news...")
    posted_history = load_posted_history()
    content, url = write_post_with_search(posted_history)

    real_url = resolve_url(url)
    full_content = f"{content}\n\n\n\nอ่านต่อ: {real_url}" if real_url else content

    print("\n=== GENERATED POST ===")
    print(full_content)
    print("======================")

    if dry_run:
        print("\n[DRY RUN] ไม่ได้โพสต์จริง")
        return

    image_url = get_og_image(real_url)

    if image_url:
        res = requests.post(
            f"{BASE_URL}/{PAGE_ID}/photos",
            data={"message": full_content, "url": image_url, "access_token": PAGE_ACCESS_TOKEN},
        )
        post_id = res.json().get("post_id") or res.json().get("id")
    else:
        res = requests.post(
            f"{BASE_URL}/{PAGE_ID}/feed",
            data={"message": full_content, "access_token": PAGE_ACCESS_TOKEN},
        )
        post_id = res.json().get("id")

    if res.status_code == 200:
        print(f"Posted! ID: {post_id}")
        sentences = [s.strip() for s in content.replace("\n", " ").split(".") if s.strip()]
        summary = ". ".join(sentences[:4])[:400]
        embedding = _get_embedding(content)
        save_posted_entry(real_url, summary, embedding)
    else:
        print(f"Error {res.status_code}: {res.json()}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    post_one(dry_run=dry_run)

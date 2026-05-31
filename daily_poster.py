"""
Usage:
  python daily_poster.py          -- post now
  python daily_poster.py --dry-run -- preview without posting
"""
import sys
import requests
from bs4 import BeautifulSoup
from content_writer import write_post_with_search
from config import PAGE_ID, PAGE_ACCESS_TOKEN, BASE_URL


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
    content, url = write_post_with_search()

    print("\n=== GENERATED POST ===")
    print(content)
    if url:
        print(f"\n[comment] อ่านต่อ: {url}")
    print("======================")

    if dry_run:
        print("\n[DRY RUN] ไม่ได้โพสต์จริง")
        return

    real_url = resolve_url(url)
    image_url = get_og_image(real_url)

    if image_url:
        res = requests.post(
            f"{BASE_URL}/{PAGE_ID}/photos",
            data={"message": content, "url": image_url, "access_token": PAGE_ACCESS_TOKEN},
        )
        post_id = res.json().get("post_id") or res.json().get("id")
    else:
        res = requests.post(
            f"{BASE_URL}/{PAGE_ID}/feed",
            data={"message": content, "access_token": PAGE_ACCESS_TOKEN},
        )
        post_id = res.json().get("id")

    if res.status_code == 200:
        print(f"Posted! ID: {post_id}")
        if post_id and url:
            post_comment(post_id, f"อ่านต่อ: {real_url}")
            print("Comment added.")
    else:
        print(f"Error {res.status_code}: {res.json()}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    post_one(dry_run=dry_run)

"""
Usage:
  python daily_poster.py          -- post one article now
  python daily_poster.py --dry-run -- preview without posting
"""
import sys
import requests
from bs4 import BeautifulSoup
from news_fetcher import fetch_articles, load_posted, save_posted
from content_writer import write_post
from config import PAGE_ID, PAGE_ACCESS_TOKEN, BASE_URL


def get_og_image(url: str) -> str | None:
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
    requests.post(
        f"{BASE_URL}/{post_id}/comments",
        data={"message": message, "access_token": PAGE_ACCESS_TOKEN},
    )


def post_one(dry_run: bool = False):
    articles = fetch_articles(limit=10)
    if not articles:
        print("No new articles found")
        return

    article = articles[0]
    print(f"Article: {article['title']}")
    print(f"Source:  {article['source']}")

    content = write_post(article["title"], article["summary"], article["source"])

    print("\n=== GENERATED POST ===")
    print(content)
    print(f"\n[comment] อ่านต่อ: {article['link']}")
    print("======================")

    if dry_run:
        print("\n[DRY RUN] ไม่ได้โพสต์จริง")
        return

    posted = load_posted()

    image_url = article.get("image_url") or get_og_image(article["link"])

    if image_url:
        res = requests.post(
            f"{BASE_URL}/{PAGE_ID}/photos",
            data={
                "message": content,
                "url": image_url,
                "access_token": PAGE_ACCESS_TOKEN,
            },
        )
    else:
        res = requests.post(
            f"{BASE_URL}/{PAGE_ID}/feed",
            data={
                "message": content,
                "access_token": PAGE_ACCESS_TOKEN,
            },
        )

    if res.status_code == 200:
        post_id = res.json().get("id") or res.json().get("post_id")
        posted.add(article["link"])
        save_posted(posted)
        print(f"Posted! ID: {post_id}")
        if post_id:
            post_comment(post_id, f"อ่านต่อ: {article['link']}")
            print("Comment added.")
    else:
        print(f"Error {res.status_code}: {res.json()}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    post_one(dry_run=dry_run)

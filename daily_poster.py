"""
Usage:
  python daily_poster.py          -- post one article now
  python daily_poster.py --dry-run -- preview without posting
"""
import sys
import requests
from news_fetcher import fetch_articles, load_posted, save_posted
from content_writer import write_post
from config import PAGE_ID, PAGE_ACCESS_TOKEN, BASE_URL


def post_one(dry_run: bool = False):
    articles = fetch_articles(limit=10)
    if not articles:
        print("No new articles found")
        return

    article = articles[0]
    print(f"Article: {article['title']}")
    print(f"Source:  {article['source']}")
    print()

    content = write_post(article["title"], article["summary"], article["source"])
    full_message = f"{content}\n\nอ่านต่อ: {article['link']}"

    print("=== GENERATED POST ===")
    print(full_message)
    print("======================")

    if dry_run:
        print("\n[DRY RUN] ไม่ได้โพสต์จริง")
        return

    posted = load_posted()

    if article.get("image_url"):
        res = requests.post(
            f"{BASE_URL}/{PAGE_ID}/photos",
            data={
                "message": full_message,
                "url": article["image_url"],
                "access_token": PAGE_ACCESS_TOKEN,
            },
        )
    else:
        res = requests.post(
            f"{BASE_URL}/{PAGE_ID}/feed",
            data={
                "message": full_message,
                "access_token": PAGE_ACCESS_TOKEN,
            },
        )

    if res.status_code == 200:
        posted.add(article["link"])
        save_posted(posted)
        print(f"Posted! ID: {res.json().get('id')}")
    else:
        print(f"Error {res.status_code}: {res.json()}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    post_one(dry_run=dry_run)

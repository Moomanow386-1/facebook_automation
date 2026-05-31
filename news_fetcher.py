import feedparser
import json
import os
from datetime import datetime, timezone

POSTED_FILE = "posted.json"

RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.wired.com/feed/rss",
]

KEYWORDS = [
    "ai", "artificial intelligence", "claude", "gemini", "chatgpt", "gpt",
    "openai", "anthropic", "google ai", "meta ai", "llm", "machine learning",
    "deep learning", "robot", "automation", "space", "nasa", "spacex",
    "tesla", "chip", "semiconductor", "quantum", "tech", "software",
]


def load_posted() -> set:
    if not os.path.exists(POSTED_FILE):
        return set()
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_posted(posted: set):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(posted), f)


def is_relevant(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(kw in text for kw in KEYWORDS)


def fetch_articles(limit: int = 10) -> list[dict]:
    posted = load_posted()
    articles = []

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                link = entry.get("link", "")
                if link in posted:
                    continue
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                if not is_relevant(title, summary):
                    continue
                image_url = None
                if "media_thumbnail" in entry:
                    image_url = entry.media_thumbnail[0].get("url")
                elif "media_content" in entry:
                    for m in entry.media_content:
                        if m.get("medium") == "image":
                            image_url = m.get("url")
                            break
                articles.append({
                    "title": title,
                    "summary": summary[:500],
                    "link": link,
                    "image_url": image_url,
                    "source": feed.feed.get("title", feed_url),
                })
                if len(articles) >= limit * 3:
                    break
        except Exception as e:
            print(f"Feed error {feed_url}: {e}")

    return articles[:limit]

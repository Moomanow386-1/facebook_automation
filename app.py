import time
import requests
from flask import Flask, render_template, jsonify
from config import PAGE_ID, PAGE_ACCESS_TOKEN, BASE_URL

app = Flask(__name__)

_cache: dict = {}


def _cached(key: str, ttl: int, fn):
    now = time.time()
    if key in _cache and now - _cache[key]["t"] < ttl:
        return _cache[key]["v"]
    result = fn()
    _cache[key] = {"v": result, "t": now}
    return result


def fetch_page_stats() -> dict:
    res = requests.get(
        f"{BASE_URL}/{PAGE_ID}",
        params={"fields": "name,fan_count,followers_count", "access_token": PAGE_ACCESS_TOKEN},
    )
    return res.json()


def fetch_posts() -> list:
    res = requests.get(
        f"{BASE_URL}/{PAGE_ID}/posts",
        params={
            "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
            "limit": 15,
            "access_token": PAGE_ACCESS_TOKEN,
        },
    )
    return res.json().get("data", [])


def fetch_insights(post_id: str) -> dict:
    res = requests.get(
        f"{BASE_URL}/{post_id}/insights",
        params={
            "metric": "post_impressions_unique,post_engaged_users",
            "access_token": PAGE_ACCESS_TOKEN,
        },
    )
    out = {}
    for item in res.json().get("data", []):
        out[item["name"]] = item["values"][0]["value"] if item.get("values") else 0
    return out


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/data")
def api_data():
    stats = _cached("stats", 300, fetch_page_stats)
    posts = _cached("posts", 300, fetch_posts)

    enriched = []
    for p in posts:
        insights = fetch_insights(p["id"])
        enriched.append({
            "id": p["id"],
            "message": p.get("message", "")[:180],
            "created_time": p.get("created_time", ""),
            "likes": p.get("likes", {}).get("summary", {}).get("total_count", 0),
            "comments": p.get("comments", {}).get("summary", {}).get("total_count", 0),
            "shares": p.get("shares", {}).get("count", 0),
            "reach": insights.get("post_impressions_unique", 0),
            "engaged": insights.get("post_engaged_users", 0),
        })

    return jsonify({"page": stats, "posts": enriched})


if __name__ == "__main__":
    app.run(debug=True, port=5000)

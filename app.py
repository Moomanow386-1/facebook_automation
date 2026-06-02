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
            "fields": "id,message,created_time",
            "limit": 10,
            "access_token": PAGE_ACCESS_TOKEN,
        },
    )
    data = res.json()
    if "error" in data:
        print(f"[fetch_posts error] {data['error']}")
    return data.get("data", [])


def fetch_insights(post_id: str) -> dict:
    res = requests.get(
        f"{BASE_URL}/{post_id}/insights",
        params={
            "metric": "post_impressions_unique,post_engaged_users,post_reactions_total",
            "access_token": PAGE_ACCESS_TOKEN,
        },
    )
    out = {}
    for item in res.json().get("data", []):
        out[item["name"]] = item["values"][0]["value"] if item.get("values") else 0
    return out


@app.route("/api/token-check")
def api_token_check():
    from config import APP_ID, APP_SECRET
    res = requests.get(
        f"{BASE_URL}/debug_token",
        params={
            "input_token": PAGE_ACCESS_TOKEN,
            "access_token": f"{APP_ID}|{APP_SECRET}",
        },
    )
    return jsonify({"token_prefix": PAGE_ACCESS_TOKEN[:20] + "...", "debug": res.json()})


@app.route("/api/debug")
def api_debug():
    res = requests.get(
        f"{BASE_URL}/{PAGE_ID}/posts",
        params={"fields": "id,message,created_time", "limit": 5, "access_token": PAGE_ACCESS_TOKEN},
    )
    return jsonify(res.json())


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/data")
def api_data():
    stats = _cached("stats", 300, fetch_page_stats)
    posts = _cached("posts", 300, fetch_posts)

    enriched = []
    for p in posts:
        if not p.get("message"):
            continue
        insights = fetch_insights(p["id"])
        enriched.append({
            "id": p["id"],
            "message": p.get("message", ""),
            "created_time": p.get("created_time", ""),
            "likes": insights.get("post_reactions_total", 0),
            "comments": insights.get("post_engaged_users", 0),
            "shares": 0,
            "reach": insights.get("post_impressions_unique", 0),
            "engaged": insights.get("post_engaged_users", 0),
        })

    return jsonify({"page": stats, "posts": enriched})


if __name__ == "__main__":
    app.run(debug=True, port=5000)

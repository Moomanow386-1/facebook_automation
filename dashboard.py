import json
import os
import requests
import streamlit as st
from datetime import datetime, timezone

from config import PAGE_ID, PAGE_ACCESS_TOKEN, BASE_URL

st.set_page_config(page_title="NextGen Tech Dashboard", page_icon="🤖", layout="wide")

st.title("🤖 NextGen Tech — Bot Dashboard")

POSTED_FILE = "posted.json"


def load_posted_history() -> list[dict]:
    if not os.path.exists(POSTED_FILE):
        return []
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [item for item in raw if isinstance(item, dict)]


@st.cache_data(ttl=300)
def get_page_stats() -> dict:
    res = requests.get(
        f"{BASE_URL}/{PAGE_ID}",
        params={
            "fields": "name,fan_count,followers_count",
            "access_token": PAGE_ACCESS_TOKEN,
        },
    )
    return res.json()


@st.cache_data(ttl=300)
def get_recent_posts() -> list[dict]:
    res = requests.get(
        f"{BASE_URL}/{PAGE_ID}/posts",
        params={
            "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
            "limit": 20,
            "access_token": PAGE_ACCESS_TOKEN,
        },
    )
    return res.json().get("data", [])


@st.cache_data(ttl=300)
def get_post_insights(post_id: str) -> dict:
    res = requests.get(
        f"{BASE_URL}/{post_id}/insights",
        params={
            "metric": "post_impressions_unique,post_engaged_users",
            "access_token": PAGE_ACCESS_TOKEN,
        },
    )
    data = res.json().get("data", [])
    result = {}
    for item in data:
        result[item["name"]] = item["values"][0]["value"] if item.get("values") else 0
    return result


# ── Page Stats ──────────────────────────────────────────────────────────────
stats = get_page_stats()
history = load_posted_history()

last_posted = None
for entry in reversed(history):
    if entry.get("posted_at"):
        last_posted = entry["posted_at"]
        break

col1, col2, col3, col4 = st.columns(4)
col1.metric("Followers", stats.get("followers_count", "—"))
col2.metric("Fan Count", stats.get("fan_count", "—"))
col3.metric("โพสต์ทั้งหมด (history)", len(history))
if last_posted:
    dt = datetime.fromisoformat(last_posted)
    col4.metric("โพสต์ล่าสุด", dt.strftime("%d %b %Y %H:%M UTC"))
else:
    col4.metric("โพสต์ล่าสุด", "—")

st.divider()

# ── Recent Posts + Engagement ────────────────────────────────────────────────
st.subheader("📋 โพสต์ล่าสุดบน Timeline")

posts = get_recent_posts()
if not posts:
    st.info("ไม่พบโพสต์บนเพจ")
else:
    for post in posts:
        created = post.get("created_time", "")
        if created:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            created_str = dt.strftime("%d %b %Y %H:%M")
        else:
            created_str = "—"

        likes = post.get("likes", {}).get("summary", {}).get("total_count", 0)
        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = post.get("shares", {}).get("count", 0)
        message = post.get("message", "")[:120] + ("..." if len(post.get("message", "")) > 120 else "")

        with st.expander(f"📅 {created_str} — {message}"):
            ecol1, ecol2, ecol3 = st.columns(3)
            ecol1.metric("👍 Likes", likes)
            ecol2.metric("💬 Comments", comments)
            ecol3.metric("🔁 Shares", shares)

            insights = get_post_insights(post["id"])
            if insights:
                icol1, icol2 = st.columns(2)
                icol1.metric("👁️ Reach (unique)", insights.get("post_impressions_unique", 0))
                icol2.metric("🖱️ Engaged Users", insights.get("post_engaged_users", 0))

            st.caption(f"Post ID: `{post['id']}`")

st.divider()

# ── Post History from posted.json ────────────────────────────────────────────
st.subheader("📂 ประวัติโพสต์ (posted.json)")

if not history:
    st.info("ยังไม่มีประวัติ")
else:
    rows = []
    for entry in reversed(history):
        posted_at = entry.get("posted_at", "—")
        if posted_at and posted_at != "—":
            dt = datetime.fromisoformat(posted_at)
            posted_at = dt.strftime("%d %b %Y %H:%M UTC")
        rows.append({
            "วันที่": posted_at,
            "Topic": entry.get("topic", "—")[:80],
            "URL": entry.get("url", "—"),
            "Post ID": entry.get("post_id", "—"),
        })
    st.dataframe(rows, use_container_width=True)

st.divider()
st.caption("ข้อมูลอัปเดตทุก 5 นาที · กด R เพื่อ refresh")

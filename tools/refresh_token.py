"""
Run this script to get a permanent Page Access Token.
Steps:
1. Go to Graph API Explorer
2. Generate a User Access Token with: pages_manage_posts, pages_read_engagement, pages_show_list
3. Paste it when prompted
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from dotenv import load_dotenv, set_key
from config import APP_ID, APP_SECRET, PAGE_ID, BASE_URL

load_dotenv()

ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def exchange_long_lived(short_token: str) -> str:
    res = requests.get(
        f"{BASE_URL}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_token,
        },
    )
    res.raise_for_status()
    return res.json()["access_token"]


def get_page_token(long_lived_user_token: str) -> str:
    res = requests.get(
        f"{BASE_URL}/me/accounts",
        params={"access_token": long_lived_user_token},
    )
    res.raise_for_status()
    pages = res.json().get("data", [])
    for page in pages:
        if page["id"] == PAGE_ID:
            return page["access_token"]
    raise ValueError(f"Page {PAGE_ID} not found")


if __name__ == "__main__":
    short_token = input("วาง User Access Token จาก Graph API Explorer: ").strip()
    print("Exchanging for long-lived token...")
    long_token = exchange_long_lived(short_token)
    print("Getting permanent Page token...")
    page_token = get_page_token(long_token)
    set_key(ENV_FILE, "PAGE_ACCESS_TOKEN", page_token)
    print("Done! PAGE_ACCESS_TOKEN ใน .env อัปเดตแล้ว (permanent token)")

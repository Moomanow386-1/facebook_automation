import sys
import os
import io
import requests
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PAGE_ACCESS_TOKEN, BASE_URL

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WARN_DAYS_BEFORE = 7


def check_token():
    res = requests.get(
        f"{BASE_URL}/debug_token",
        params={
            "input_token": PAGE_ACCESS_TOKEN,
            "access_token": PAGE_ACCESS_TOKEN,
        },
    )
    data = res.json().get("data", {})

    expires_at = data.get("expires_at", 0)

    if expires_at == 0:
        print("Token: ไม่มีวันหมดอายุ (permanent)")
        return

    expire_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    days_left = (expire_dt - now).days

    if days_left <= 0:
        print(f"⚠️  Token หมดอายุแล้ว! ต้อง generate ใหม่ทันที")
    elif days_left <= WARN_DAYS_BEFORE:
        print(f"⚠️  Token เหลืออีก {days_left} วัน — ต้อง generate ใหม่เร็วๆ นี้")
        print(f"   หมดอายุ: {expire_dt.strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        print(f"Token OK — เหลืออีก {days_left} วัน (หมด {expire_dt.strftime('%Y-%m-%d')})")


if __name__ == "__main__":
    check_token()

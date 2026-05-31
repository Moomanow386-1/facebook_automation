import requests
from config import PAGE_ID, PAGE_ACCESS_TOKEN, BASE_URL


def post_text(message: str) -> dict:
    url = f"{BASE_URL}/{PAGE_ID}/feed"
    payload = {
        "message": message,
        "access_token": PAGE_ACCESS_TOKEN,
    }
    res = requests.post(url, data=payload)
    res.raise_for_status()
    return res.json()


def post_with_image(message: str, image_url: str) -> dict:
    url = f"{BASE_URL}/{PAGE_ID}/photos"
    payload = {
        "message": message,
        "url": image_url,
        "access_token": PAGE_ACCESS_TOKEN,
    }
    res = requests.post(url, data=payload)
    res.raise_for_status()
    return res.json()


def post_with_local_image(message: str, image_path: str) -> dict:
    url = f"{BASE_URL}/{PAGE_ID}/photos"
    payload = {
        "message": message,
        "access_token": PAGE_ACCESS_TOKEN,
    }
    with open(image_path, "rb") as f:
        res = requests.post(url, data=payload, files={"source": f})
    res.raise_for_status()
    return res.json()

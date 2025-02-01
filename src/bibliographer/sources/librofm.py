import json
import requests

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog

LIBRO_BASE_URL = "https://libro.fm"
LOGIN_ENDPOINT = "/oauth/token"
LIBRARY_ENDPOINT = "/api/v7/library"


def librofm_login(username: str, password: str) -> str:
    """Logs in and returns an auth token."""
    url = f"{LIBRO_BASE_URL}{LOGIN_ENDPOINT}"
    payload = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()["access_token"]


def librofm_retrieve_library(catalog: CardCatalog, token: str):
    """Lists all audiobooks in the account."""

    page = 1
    while True:
        url = f"{LIBRO_BASE_URL}{LIBRARY_ENDPOINT}"
        params = {"page": page}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "okhttp/3.14.9",
        }

        mlogger.debug(f"[LIBROFM] GET library page={page}")
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        if "audiobooks" not in data:
            raise ValueError("No audiobooks found in response")

        for book in data["audiobooks"]:
            mlogger.debug(f"[LIBROFM] Retrieving metadata for ISBN {book['isbn']}")
            catalog.librofmlib.contents[book["isbn"]] = book

        if page >= data["total_pages"]:
            break
        page += 1

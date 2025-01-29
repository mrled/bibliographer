import pathlib
from typing import Optional

import requests

from bibliographer import mlogger
from bibliographer.ratelimiter import RateLimiter
from bibliographer.util.jsonutil import load_json, save_json


@RateLimiter.limit("openlibrary.org", interval=1)
def isbn2olid(isbn2olid_map: pathlib.Path, isbn: str) -> Optional[str]:
    """
    Store the OLID as just "OL12345M", not "/books/OL12345M".
    """
    data = load_json(isbn2olid_map)
    if isbn in data:
        return data[isbn]

    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    mlogger.debug(f"[OPENLIBRARY] GET {url}")
    r = requests.get(url, headers={"User-Agent": "BookishBot/1.0"}, timeout=10)
    mlogger.debug(f"[OPENLIBRARY] => status {r.status_code}")
    if r.status_code != 200:
        return None
    j = r.json()
    key = f"ISBN:{isbn}"
    if key not in j:
        data[isbn] = None
        save_json(isbn2olid_map, data)
        return None

    book_info = j[key]
    olid = None
    if "key" in book_info:
        raw = book_info["key"]  # e.g. "/books/OL12345M"
        if raw.startswith("/books/"):
            raw = raw[len("/books/") :]  # just "OL12345M"
        olid = raw

    data[isbn] = olid
    save_json(isbn2olid_map, data)
    return olid

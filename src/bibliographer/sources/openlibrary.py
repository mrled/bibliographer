from typing import Optional

import requests

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog
from bibliographer.ratelimiter import RateLimiter


@RateLimiter.limit("openlibrary.org", interval=1)
def isbn2olid(catalog: CardCatalog, isbn: str) -> Optional[str]:
    """
    Store the OLID as just "OL12345M", not "/books/OL12345M".
    """
    if isbn in catalog.isbn2olid_map.contents:
        return catalog.isbn2olid_map.contents[isbn]

    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    mlogger.debug(f"[OPENLIBRARY] GET {url}")
    r = requests.get(url, headers={"User-Agent": "BibliograhperBot/1.0"}, timeout=10)
    mlogger.debug(f"[OPENLIBRARY] => status {r.status_code}")
    if r.status_code != 200:
        return None
    j = r.json()
    key = f"ISBN:{isbn}"
    if key not in j:
        catalog.isbn2olid_map.contents[isbn] = None
        return None

    book_info = j[key]
    olid = None
    if "key" in book_info:
        raw = book_info["key"]  # e.g. "/books/OL12345M"
        if raw.startswith("/books/"):
            raw = raw[len("/books/") :]  # just "OL12345M"
        olid = raw

    catalog.isbn2olid_map.contents[isbn] = olid
    return olid

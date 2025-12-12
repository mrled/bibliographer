from typing import Optional

import requests

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog
from bibliographer.ratelimiter import RateLimiter


def normalize_olid(olid: Optional[str]) -> Optional[str]:
    """Normalize an OpenLibrary ID to just the ID part.

    Handles various formats:
    - "/books/OL12345M" -> "OL12345M"
    - "/works/OL12345W" -> "OL12345W"
    - "OL12345M" -> "OL12345M" (unchanged)
    - None -> None

    Returns the normalized OLID or None.
    """
    if not olid:
        return None

    # Strip common OpenLibrary path prefixes
    if olid.startswith("/books/"):
        return olid[len("/books/") :]
    if olid.startswith("/works/"):
        return olid[len("/works/") :]
    if olid.startswith("/authors/"):
        return olid[len("/authors/") :]

    # Return as-is if no prefix found
    return olid


@RateLimiter.limit("openlibrary.org", interval=1)
def _fetch_openlibrary_api(isbn: str) -> Optional[dict]:
    """Fetch book data from OpenLibrary API. Returns None if not found or on error."""
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    mlogger.debug(f"[OPENLIBRARY] GET {url}")
    r = requests.get(url, headers={"User-Agent": "BibliograhperBot/1.0"}, timeout=10)
    mlogger.debug(f"[OPENLIBRARY] => status {r.status_code}")

    if r.status_code != 200:
        return None

    j = r.json()
    key = f"ISBN:{isbn}"
    return j.get(key)


def isbn2olid(catalog: CardCatalog, isbn: str) -> Optional[str]:
    """Look up the OpenLibrary ID for an ISBN.

    The OLID is stored as just "OL12345M", not "/books/OL12345M".
    """
    if isbn in catalog.isbn2olid_map.contents:
        return catalog.isbn2olid_map.contents[isbn]

    book_info = _fetch_openlibrary_api(isbn)
    if not book_info:
        catalog.isbn2olid_map.contents[isbn] = None
        return None

    olid = None
    if "key" in book_info:
        olid = normalize_olid(book_info["key"])

    catalog.isbn2olid_map.contents[isbn] = olid
    return olid

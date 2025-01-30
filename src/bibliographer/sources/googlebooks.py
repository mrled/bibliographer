"""Google Books API info retrieval
"""

import pathlib
from typing import Optional

import requests

from bibliographer import mlogger
from bibliographer.util.jsonutil import load_json, save_json
import urllib
import urllib.parse


def google_books_retrieve(
    key: str, gbooks_volumes: pathlib.Path, bookid: str, overwrite: bool = False
) -> Optional[dict]:
    """
    Check local cache. If not present or 'overwrite' is True, re-fetch from Google Books for volumeID.

    We'll store only the single largest cover in `image_urls[0]`.
    The recognized keys are:
      ["extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail"]
    in that order.
    """
    data = load_json(gbooks_volumes)
    if (bookid in data) and not overwrite:
        return data[bookid]

    url = (
        f"https://www.googleapis.com/books/v1/volumes/{bookid}"
        f"?fields=id,volumeInfo(title,authors,publishedDate,imageLinks,industryIdentifiers)&key={key}"
    )
    mlogger.debug(f"[GBOOKS] GET {url}")
    r = requests.get(url, timeout=10)
    mlogger.debug(f"[GBOOKS] => status {r.status_code}")
    if r.status_code != 200:
        return None
    j = r.json()
    if "error" in j:
        return None

    vi = j.get("volumeInfo", {})
    isbn13 = None
    inds = vi.get("industryIdentifiers", [])
    for ident in inds:
        if ident.get("type") == "ISBN_13":
            isbn13 = ident.get("identifier")

    links = vi.get("imageLinks", {})
    # Try largest-first
    largest_keys = ["extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail"]
    largest_url = None
    for k in largest_keys:
        if k in links:
            largest_url = links[k]
            break

    image_urls = []
    if largest_url:
        image_urls.append(largest_url)

    result = {
        "bookid": bookid,
        "isbn13": isbn13,
        "title": vi.get("title"),
        "authors": vi.get("authors", []),
        "publish_date": vi.get("publishedDate"),
        "image_urls": image_urls,
    }
    data[bookid] = result
    save_json(gbooks_volumes, data)
    return result


def google_books_search(key: str, gbooks_volumes: pathlib.Path, title: str, author: str) -> Optional[dict]:
    """
    Search Google Books by intitle + inauthor. Return the first volume's data, or None.
    """
    query = f"intitle:{title} inauthor:{author}"
    encoded_q = urllib.parse.quote(query)
    url = f"https://www.googleapis.com/books/v1/volumes?q={encoded_q}&key={key}"
    mlogger.debug(f"[GBOOKS] SEARCH {url}")
    r = requests.get(url, timeout=10)
    mlogger.debug(f"[GBOOKS] => status {r.status_code}")
    if r.status_code != 200:
        return None
    j = r.json()
    items = j.get("items", [])
    if not items:
        return None
    first_item = items[0]
    first_id = first_item["id"]
    return google_books_retrieve(key, gbooks_volumes, first_id)


def asin2gbv(
    asin2gbv_map: pathlib.Path, asin: str, title: str, author: str, google_books_key: str, gbooks_volumes: pathlib.Path
) -> Optional[str]:
    data = load_json(asin2gbv_map)
    if asin in data:
        return data[asin]

    search_res = google_books_search(google_books_key, gbooks_volumes, title, author)
    if not search_res:
        data[asin] = None
    else:
        data[asin] = search_res.get("bookid")

    save_json(asin2gbv_map, data)
    return data[asin]

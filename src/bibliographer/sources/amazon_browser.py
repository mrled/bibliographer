import re
from typing import Any

import requests

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog
from bibliographer.ratelimiter import RateLimiter


@RateLimiter.limit("amazon.com", interval=1)
def amazon_browser_search(plus_term: str):
    """Make a request to Amazon search and extract the ASIN from the first result.

    Limit to 1 request per second via RateLimiter.
    """
    url = f"https://www.amazon.com/s?k={plus_term}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "DNT": "1",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Priority": "u=0, i",
    }
    mlogger.debug(f"[AMAZON] GET {url}")
    r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
    mlogger.debug(f"[AMAZON] => status {r.status_code}")
    if r.status_code != 200:
        return None

    match = re.search(r'<div[^>]*data-asin="([^"]+)"[^>]', r.text)
    if match:
        found_asin = match.group(1).strip()
        if found_asin:
            return found_asin

    return None


def amazon_browser_search_cached(catalog: CardCatalog, searchterm: str, force=False):
    """Look up a search term in the search2asin_map cache, and if not present, search Amazon."""
    data = catalog.contents("usermaps_search2asin")
    plus_term = "+".join(searchterm.strip().split())

    if plus_term in data and not force:
        return data[plus_term]

    return amazon_browser_search(plus_term)

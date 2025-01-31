from typing import Dict, List

import requests

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog


def wikipedia_relevant_pages(catalog: CardCatalog, title: str, authors: List[str]) -> Dict[str, str]:
    """
    Try 'title (book)', 'title', and each author. Return dict { "Page Title": "URL" } for existing pages.
    Cache the results in wikipedia_cache to avoid repeated API calls.

    Implementation detail: we only get the first valid match for the book
    but we try all authors, storing all valid matches.
    """
    cache_data = catalog.contents("usermaps_wikipedia_relevant")
    authors = authors or []
    cache_key = f"title={title};authors={'|'.join(authors)}"
    if cache_key in cache_data:
        return cache_data[cache_key]

    def query_wikipedia(article: str):
        baseurl = "https://en.wikipedia.org/w/api.php"
        mlogger.debug(f"[WIKIPEDIA] Checking {article}")
        params = {"action": "query", "titles": article, "format": "json", "prop": "info"}
        r = requests.get(baseurl, params=params, timeout=10)
        mlogger.debug(f"[WIKIPEDIA] => status {r.status_code}")
        if r.status_code == 200:
            j = r.json()
            pages = j["query"]["pages"]
            for pageid, pageinfo in pages.items():
                if "missing" not in pageinfo:
                    normalized_title = pageinfo["title"]
                    url = "https://en.wikipedia.org/wiki/" + normalized_title.replace(" ", "_")
                    return normalized_title, url
        raise ValueError(f"Page not found: {article}")

    result = {}

    # Only find the first valid page for the book title
    title_candidates = [f"{title} (book)", title]
    for cand in title_candidates:
        try:
            normalized_title, url = query_wikipedia(cand)
            result[normalized_title] = url
            break
        except:
            pass

    # Look for all valid pages for the authors
    for author in authors:
        try:
            normalized_title, url = query_wikipedia(author)
            result[normalized_title] = url
        except:
            pass

    cache_data[cache_key] = result
    return result

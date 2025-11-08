from typing import Dict, List

import requests

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog


def wikipedia_relevant_pages(catalog: CardCatalog, title: str, authors: List[str]) -> Dict[str, str]:
    """
    Try 'title (book)', 'title', and each author. Return dict { "Page Title": "URL" } for existing pages.
    Cache individual search results in wikipedia_api_cache to avoid repeated API calls.

    Implementation detail: we only get the first valid match for the book
    but we try all authors, storing all valid matches.
    """
    authors = authors or []

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

    def get_or_query_wikipedia(search_term: str):
        """Get from cache or query Wikipedia and cache the result."""
        if search_term in catalog.wikipedia_api_cache.contents:
            cached_url = catalog.wikipedia_api_cache.contents[search_term]
            if cached_url is None:
                # Previously searched and not found
                return None
            # Extract normalized title from URL
            normalized_title = cached_url.replace("https://en.wikipedia.org/wiki/", "").replace("_", " ")
            return normalized_title, cached_url

        try:
            normalized_title, url = query_wikipedia(search_term)
            catalog.wikipedia_api_cache.contents[search_term] = url
            return normalized_title, url
        except:
            catalog.wikipedia_api_cache.contents[search_term] = None
            return None

    result = {}

    # Only find the first valid page for the book title
    title_candidates = [f"{title} (book)", title]
    for cand in title_candidates:
        page_result = get_or_query_wikipedia(cand)
        if page_result:
            normalized_title, url = page_result
            result[normalized_title] = url
            break

    # Look for all valid pages for the authors
    for author in authors:
        page_result = get_or_query_wikipedia(author)
        if page_result:
            normalized_title, url = page_result
            result[normalized_title] = url

    return result

"""Raindrop.io API integration for retrieving highlights."""

import requests

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog, CatalogArticle
from bibliographer.util.slugify import slugify

RAINDROP_API_BASE = "https://api.raindrop.io/rest/v1"
HIGHLIGHTS_ENDPOINT = "/highlights"
MAX_PER_PAGE = 50


def raindrop_retrieve_highlights(catalog: CardCatalog, token: str) -> int:
    """Retrieve all highlights from raindrop.io and save to the catalog.

    Args:
        catalog: The CardCatalog to save highlights to.
        token: The raindrop.io API access token.

    Returns:
        The number of highlights retrieved.
    """
    page = 0
    total_retrieved = 0

    while True:
        url = f"{RAINDROP_API_BASE}{HIGHLIGHTS_ENDPOINT}"
        params = {"page": page, "perpage": MAX_PER_PAGE}
        headers = {
            "Authorization": f"Bearer {token}",
        }

        mlogger.debug(f"[RAINDROP] GET highlights page={page}")
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("result"):
            raise ValueError(f"Raindrop API returned error: {data}")

        items = data.get("items", [])
        if not items:
            break

        for highlight in items:
            highlight_id = highlight["_id"]
            mlogger.debug(f"[RAINDROP] Retrieved highlight {highlight_id}")
            catalog.raindrop_highlights.contents[highlight_id] = highlight
            total_retrieved += 1

        # If we got fewer items than requested, we've reached the end
        if len(items) < MAX_PER_PAGE:
            break

        page += 1

    mlogger.info(f"[RAINDROP] Retrieved {total_retrieved} highlights")
    return total_retrieved


def process_raindrop_highlights(catalog: CardCatalog):
    """Process raindrop highlights and add unique articles to the combined library.

    Multiple highlights may reference the same article (URL). This function
    creates one CatalogArticle per unique URL and adds it to the combined library.
    """
    # Group highlights by URL to get unique articles
    seen_urls = set()

    for highlight_id, highlight in catalog.raindrop_highlights.contents.items():
        url = highlight.get("link")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        mlogger.debug(f"Processing raindrop highlight for URL {url}")

        article = CatalogArticle()
        article.title = highlight.get("title")
        article.url = url

        # Map URL to slug
        if url not in catalog.raindropslugs.contents:
            catalog.raindropslugs.contents[url] = slugify(highlight.get("title", ""), remove_subtitle=False)
        article.slug = catalog.raindropslugs.contents[url]

        # Only add if not already in combined library
        if article.slug not in catalog.combinedlib.contents:
            catalog.combinedlib.contents[article.slug] = article

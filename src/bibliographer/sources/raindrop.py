"""Raindrop.io API integration for retrieving highlights."""

from urllib.parse import urlparse

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
    creates one CatalogArticle per unique URL, collects all highlights for that URL,
    and adds them to the article's highlights.raindrop list.
    """
    # Group highlights by URL
    highlights_by_url: dict[str, list[dict]] = {}

    for highlight_id, highlight in catalog.raindrop_highlights.contents.items():
        url = highlight.get("link")
        if not url:
            continue

        if url not in highlights_by_url:
            highlights_by_url[url] = []

        # Build highlight entry: _id, text, note, skip (default False), plus other raindrop fields
        highlight_entry = {
            "_id": highlight.get("_id"),
            "text": highlight.get("text"),
            "note": highlight.get("note", ""),
            "skip": False,
        }
        # Add other raindrop fields (excluding link/title which are article-level)
        for key in ["color", "created", "tags", "raindropRef"]:
            if key in highlight:
                highlight_entry[key] = highlight[key]

        highlights_by_url[url].append(highlight_entry)

    # Process each unique URL
    for url, url_highlights in highlights_by_url.items():
        # Get title from the first highlight (they all have the same title for a URL)
        first_highlight = catalog.raindrop_highlights.contents.get(url_highlights[0]["_id"], {})
        title = first_highlight.get("title", "")

        mlogger.debug(f"Processing {len(url_highlights)} raindrop highlights for URL {url}")

        # Map URL to slug: domain/slugified-title-id
        if url not in catalog.raindropslugs.contents:
            domain = urlparse(url).netloc
            highlight_id = url_highlights[0]["_id"]
            title_slug = slugify(title, remove_subtitle=False)
            catalog.raindropslugs.contents[url] = f"{domain}/{title_slug}-{highlight_id}"
        slug = catalog.raindropslugs.contents[url]

        # Find the earliest created date among all highlights for this URL
        created_dates = [h.get("created") for h in url_highlights if h.get("created")]
        earliest_created = min(created_dates) if created_dates else None

        # Get or create article in combined library
        if slug not in catalog.combinedlib.contents:
            article = CatalogArticle()
            article.title = title
            article.url = url
            article.slug = slug
            if earliest_created:
                article.consumed_date = earliest_created
            catalog.combinedlib.contents[slug] = article

        # Add highlights to the article
        work = catalog.combinedlib.contents[slug]
        if work.highlights is None:
            work.highlights = {}
        work.highlights["raindrop"] = url_highlights

        # Set consumed_date if not already set
        if earliest_created and not work.consumed_date:
            work.consumed_date = earliest_created

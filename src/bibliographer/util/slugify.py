from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from bibliographer.cardcatalog import CombinedCatalogWork


def slugify(title: str, remove_subtitle: bool = True) -> str:
    """
    Convert a title into a slug.
    - Optionally remove subtitle (default: True)
    - Lowercase
    - Remove punctuation
    - Replace spaces with hyphens
    - Remove leading 'the' if present
    """
    out = title.lower()
    if remove_subtitle:
        out = re.sub(r"\:.*", "", out)  # remove subtitle
    out = re.sub(r"[^\w\s-]", "", out)  # remove punctuation
    out = re.sub(r"^the\s+", "", out)  # remove leading 'the '
    out = re.sub(r"^a\s+", "", out)  # remove leading 'a '
    out = re.sub(r"\s+", "-", out)  # convert spaces to hyphens
    out = re.sub(r"-+", "-", out)  # collapse multiple hyphens
    return out.strip("-")


def generate_raindrop_slug(url: str, title: str, highlight_id: str) -> str:
    """Generate a slug for a raindrop-imported article.

    Format: {domain}/{title_slug}-{highlight_id}
    """
    domain = urlparse(url).netloc
    title_slug = slugify(title, remove_subtitle=False)
    return f"{domain}/{title_slug}-{highlight_id}"


def extract_raindrop_highlight_id(slug: str) -> str | None:
    """Extract the highlight ID from a raindrop slug.

    Raindrop slugs have format: {domain}/{title_slug}-{highlight_id}
    Returns None if the slug doesn't match the expected format.
    """
    # Raindrop highlight IDs are 24-character hex strings (MongoDB ObjectIds)
    match = re.search(r"-([a-f0-9]{24})$", slug)
    return match.group(1) if match else None


def generate_slug_for_work(
    item: CombinedCatalogWork,
    current_slug: str = "",
) -> str:
    """Generate a slug for a catalog item.

    Automatically detects raindrop items by checking the current slug for a
    highlight ID pattern, or by looking in the item's highlights data.

    Args:
        item: The catalog item to generate a slug for.
        current_slug: The current slug (used to detect and extract highlight ID for raindrop items).
            Optional for non-raindrop items.

    Returns:
        The generated slug.
    """
    highlight_id = extract_raindrop_highlight_id(current_slug)
    url = getattr(item, "url", None)

    # If no highlight ID in slug, check item's highlights data
    if not highlight_id:
        highlights = getattr(item, "highlights", None)
        if highlights and "raindrop" in highlights and highlights["raindrop"]:
            first_highlight = highlights["raindrop"][0]
            highlight_id = first_highlight.get("_id")

    # If we have a highlight ID and URL, generate raindrop-style slug
    if highlight_id and url:
        if item.title is None:
            raise ValueError("Cannot generate raindrop slug: item has no title")
        return generate_raindrop_slug(url, item.title, highlight_id)

    # Books remove subtitles, other types keep them
    remove_subtitle = item.work_type == "book"

    # Use title if available, otherwise fall back to URL for non-book types
    if item.title:
        return slugify(item.title, remove_subtitle=remove_subtitle)
    elif url:
        return slugify(url, remove_subtitle=False)
    else:
        raise ValueError("Cannot generate slug: item has no title or URL")

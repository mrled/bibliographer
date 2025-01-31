from typing import Optional

from bibliographer.cardcatalog import CardCatalog
from bibliographer.hugo import slugify


def manual_add(
    catalog: CardCatalog,
    title: Optional[str],
    authors: Optional[list[str]],
    isbn: Optional[str],
    purchase_date: Optional[str],
    read_date: Optional[str],
    slug: Optional[str],
):
    """
    Add a new manual book entry to manual.json.

    We'll store them in a shape similar to the "enriched" data from audible/kindle:
    {
      "<slug>": {
        "title": "...",
        "authors": [...],
        "isbn": "...",
        "purchase_date": "...",
        "read_date": "...",
        "slug": "...",
        "gbooks_volid": "...",
        "openlibrary_id": "...",
        "book_asin": "...",
        "skip": false
      }
    }
    """
    data = catalog.contents("usermaps_manual_library")

    # If no title, we try to pick something from ISBN or "untitled"
    if not title and not isbn:
        raise Exception("Must specify at least --title or --isbn")

    # We'll create a slug from either the title or the ISBN
    if not slug:
        if title:
            slug = slugify(title)
        else:
            slug = f"book-{isbn}"

    if slug in data:
        raise ValueError(f"Slug {slug} already exists in manual data, edit that entry or choose a different slug")

    record = {
        "title": title if title else f"Untitled {isbn}",
        "authors": authors,
        "isbn": isbn,
        "purchase_date": purchase_date,
        "read_date": read_date,
        "slug": slug,
        "gbooks_volid": None,
        "openlibrary_id": None,
        "book_asin": None,
        "skip": False,
    }
    data[slug] = record
    print(f"Added manual entry {slug}")

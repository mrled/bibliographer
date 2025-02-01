from typing import Optional

from bibliographer.cardcatalog import CardCatalog, CombinedCatalogBook
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
    """Add a new manual book entry to the combined library."""

    if not title and not isbn:
        raise Exception("Must specify at least --title or --isbn")

    if isbn:
        isbn = isbn.replace("-", "").replace(" ", "")

    # We'll create a slug from either the title or the ISBN
    if not slug:
        if title:
            slug = slugify(title)
        else:
            slug = f"book-{isbn}"

    if slug in catalog.combinedlib.contents:
        raise ValueError(f"Slug {slug} already exists in manual data, edit that entry or choose a different slug")

    book = CombinedCatalogBook(
        title=title,
        authors=authors or [],
        isbn=isbn,
        purchase_date=purchase_date,
        read_date=read_date,
        slug=slug,
    )
    catalog.combinedlib.contents[slug] = book
    print(f"Added manual entry {slug}")

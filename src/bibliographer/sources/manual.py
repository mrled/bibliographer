from typing import Optional

from bibliographer.cardcatalog import CardCatalog, CombinedCatalogBook, CombinedWork, ManualWork
from bibliographer.hugo import slugify
from bibliographer.util.isbnutil import normalize_isbn


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
        isbn = normalize_isbn(isbn)

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


def manual_add_work(
    catalog: CardCatalog,
    work_type: str,
    slug: str,
    title: Optional[str] = None,
    url: Optional[str] = None,
    authors: Optional[list[str]] = None,
    read_date: Optional[str] = None,
    publish_date: Optional[str] = None,
    isbn: Optional[str] = None,
    purchase_date: Optional[str] = None,
):
    """Add a new manual work entry (article, etc.) to the manual works and combined works."""

    if not title and not url:
        raise Exception("Must specify at least --title or --url")

    if isbn:
        isbn = normalize_isbn(isbn)

    # Check if slug already exists in either manual works or combined works
    if slug in catalog.manualworks.contents:
        raise ValueError(f"Slug {slug} already exists in manual works, edit that entry or choose a different slug")
    if slug in catalog.combinedworks.contents:
        raise ValueError(f"Slug {slug} already exists in combined works, edit that entry or choose a different slug")

    # Create manual work entry
    manual_work = ManualWork(
        slug=slug,
        work_type=work_type,
        title=title,
        url=url,
        authors=authors or [],
        read_date=read_date,
        publish_date=publish_date,
        isbn=isbn,
        purchase_date=purchase_date,
    )
    catalog.manualworks.contents[slug] = manual_work

    # Also create a combined work entry (initially identical to the manual work)
    combined_work = CombinedWork(
        slug=slug,
        work_type=work_type,
        title=title,
        url=url,
        authors=authors or [],
        read_date=read_date,
        publish_date=publish_date,
        isbn=isbn,
        purchase_date=purchase_date,
    )
    catalog.combinedworks.contents[slug] = combined_work

    print(f"Added {work_type} entry: {slug}")

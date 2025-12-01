from typing import Optional

from bibliographer.cardcatalog import (
    CardCatalog,
    CatalogArticle,
    CatalogBook,
    CatalogPodcastEpisode,
    CatalogVideo,
)
from bibliographer.util.slugify import slugify
from bibliographer.util.isbnutil import normalize_isbn


def add_book(
    catalog: CardCatalog,
    title: Optional[str],
    authors: Optional[list[str]],
    isbn: Optional[str],
    purchase_date: Optional[str],
    read_date: Optional[str],
    slug: Optional[str],
):
    """Add a new book entry to the combined library."""

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
        raise ValueError(f"Slug {slug} already exists, edit that entry or choose a different slug")

    book = CatalogBook(
        title=title,
        authors=authors or [],
        isbn=isbn,
        purchase_date=purchase_date,
        consumed_date=read_date,
        slug=slug,
    )
    catalog.combinedlib.contents[slug] = book
    print(f"Added book {slug}")


def add_article(
    catalog: CardCatalog,
    title: Optional[str],
    authors: Optional[list[str]],
    url: Optional[str],
    publication: Optional[str],
    purchase_date: Optional[str],
    consumed_date: Optional[str],
    slug: Optional[str],
):
    """Add a new article entry to the combined library."""

    if not title and not url:
        raise Exception("Must specify at least --title or --url")

    if not slug:
        if title:
            slug = slugify(title, remove_subtitle=False)
        elif url:
            slug = slugify(url, remove_subtitle=False)

    if slug in catalog.combinedlib.contents:
        raise ValueError(f"Slug {slug} already exists, edit that entry or choose a different slug")

    article = CatalogArticle(
        title=title,
        authors=authors or [],
        url=url,
        publication=publication,
        purchase_date=purchase_date,
        consumed_date=consumed_date,
        slug=slug,
    )
    catalog.combinedlib.contents[slug] = article
    print(f"Added article {slug}")


def add_podcast(
    catalog: CardCatalog,
    title: Optional[str],
    authors: Optional[list[str]],
    url: Optional[str],
    podcast_name: Optional[str],
    episode_number: Optional[int],
    purchase_date: Optional[str],
    consumed_date: Optional[str],
    slug: Optional[str],
):
    """Add a new podcast episode entry to the combined library."""

    if not title and not url:
        raise Exception("Must specify at least --title or --url")

    if not slug:
        if title:
            slug = slugify(title, remove_subtitle=False)
        elif url:
            slug = slugify(url, remove_subtitle=False)

    if slug in catalog.combinedlib.contents:
        raise ValueError(f"Slug {slug} already exists, edit that entry or choose a different slug")

    podcast = CatalogPodcastEpisode(
        title=title,
        authors=authors or [],
        url=url,
        podcast_name=podcast_name,
        episode_number=episode_number,
        purchase_date=purchase_date,
        consumed_date=consumed_date,
        slug=slug,
    )
    catalog.combinedlib.contents[slug] = podcast
    print(f"Added podcast episode {slug}")


def add_video(
    catalog: CardCatalog,
    title: Optional[str],
    authors: Optional[list[str]],
    url: Optional[str],
    purchase_date: Optional[str],
    consumed_date: Optional[str],
    slug: Optional[str],
):
    """Add a new video entry to the combined library."""

    if not title and not url:
        raise Exception("Must specify at least --title or --url")

    if not slug:
        if title:
            slug = slugify(title, remove_subtitle=False)
        elif url:
            slug = slugify(url, remove_subtitle=False)

    if slug in catalog.combinedlib.contents:
        raise ValueError(f"Slug {slug} already exists, edit that entry or choose a different slug")

    video = CatalogVideo(
        title=title,
        authors=authors or [],
        url=url,
        purchase_date=purchase_date,
        consumed_date=consumed_date,
        slug=slug,
    )
    catalog.combinedlib.contents[slug] = video
    print(f"Added video {slug}")

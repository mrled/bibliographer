import json
import pathlib
import shutil
from typing import List, Optional

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog
from bibliographer.hugo import slugify
from bibliographer.sources.amazon_browser import amazon_browser_search_cached
from bibliographer.sources.covers import lookup_cover
from bibliographer.sources.googlebooks import google_books_retrieve, google_books_search
from bibliographer.sources.openlibrary import isbn2olid, normalize_olid
from bibliographer.sources.wikipedia import wikipedia_relevant_pages


def enrich_combined_library(
    catalog: CardCatalog,
    google_books_key: str,
    slug_filter: Optional[List[str]] = None,
):
    """Enrich all entries in the combined library, or specific ones if slug_filter is provided."""
    mlogger.debug("Enriching combined library...")

    for slug, book in catalog.combinedlib.contents.items():
        if slug_filter and slug not in slug_filter:
            continue
        if book.skip:
            mlogger.debug(f"Skipping {slug}")
            continue
        mlogger.debug(f"Enriching combined library... processing {slug}")

        if not book.gbooks_volid:
            if book.title and book.authors:
                gbook = google_books_search(catalog, google_books_key, book.title, book.authors[0])
                if gbook:
                    book.gbooks_volid = gbook.get("bookid")

        if not book.isbn:
            if book.gbooks_volid:
                gbook = google_books_retrieve(catalog, google_books_key, book.gbooks_volid)
                if gbook:
                    book.isbn = gbook.get("isbn13")

        if book.publish_date is None:
            if book.gbooks_volid:
                gbook = google_books_retrieve(catalog, google_books_key, book.gbooks_volid)
                if gbook:
                    book.publish_date = gbook.get("publishedDate")

        # Normalize any existing OLID and fetch if missing
        if book.openlibrary_id:
            book.openlibrary_id = normalize_olid(book.openlibrary_id)
        elif book.isbn:
            book.openlibrary_id = isbn2olid(catalog, book.isbn)

        if not book.book_asin:
            if book.title and book.authors:
                searchterm = " ".join([book.title] + book.authors)
                book.book_asin = amazon_browser_search_cached(catalog, searchterm)

        if book.urls_wikipedia is None:
            book.urls_wikipedia = wikipedia_relevant_pages(catalog, book.title, book.authors)

    return


def retrieve_covers(catalog: CardCatalog, cover_assets_root: pathlib.Path, slug_filter: Optional[List[str]] = None):
    """Retrieve cover images for all entries in the combined library, or specific ones if slug_filter is provided."""
    for book in catalog.combinedlib.contents.values():
        if slug_filter and book.slug not in slug_filter:
            continue
        if book.skip:
            mlogger.debug(f"Skipping cover retrieval for {book.slug}")
            continue
        mlogger.debug(f"Retrieving cover for {book.slug}...")
        book_dir = cover_assets_root / book.slug
        fallback_asin = book.book_asin or book.kindle_asin or book.audible_asin
        lookup_cover(
            catalog=catalog,
            gbooks_volid=book.gbooks_volid,
            fallback_asin=fallback_asin,
            book_dir=book_dir,
        )


def write_index_md_files(catalog: CardCatalog, books_root: pathlib.Path, slug_filter: Optional[List[str]] = None):
    """Create index.md files for all entries in the combined library, or specific ones if slug_filter is provided.

    Never overwrite an existing index.md file.
    """
    for book in catalog.combinedlib.contents.values():
        if slug_filter and book.slug not in slug_filter:
            continue
        if book.skip:
            mlogger.debug(f"[index.md] skipping for {book.slug}")
            continue
        book_dir = books_root / book.slug
        index_md_path = book_dir / "index.md"
        if index_md_path.exists():
            mlogger.debug(f"[index.md] already exists for {book.slug}, skipping...")
            continue
        mlogger.debug(f"[index.md] writing for {book.slug}...")
        book_dir.mkdir(exist_ok=True, parents=True)
        if not index_md_path.exists():
            date_str = book.purchase_date or ""
            quoted_title = book.title.replace('"', '\\"')
            frontmatter_lines = []
            frontmatter_lines.append("---")
            frontmatter_lines.append(f'title: "{quoted_title}"')
            frontmatter_lines.append("draft: true")
            if date_str:
                frontmatter_lines.append(f"date: {date_str}")
            else:
                frontmatter_lines.append("# date:")
            frontmatter_lines.append("---")
            frontmatter = "\n".join(frontmatter_lines) + "\n"
            index_md_path.write_text(frontmatter, encoding="utf-8")


def write_bibliographer_json_files(catalog: CardCatalog, books_root: pathlib.Path, slug_filter: Optional[List[str]] = None):
    """Create bibliographer.json files for all entries in the combined library, or specific ones if slug_filter is provided.

    Always overwrite bibliographer.json files.
    """
    for book in catalog.combinedlib.contents.values():
        if slug_filter and book.slug not in slug_filter:
            continue
        if book.skip:
            mlogger.debug(f"[bibliographer.json] skipping for {book.slug}")
            continue
        mlogger.debug(f"[bibliographer.json] writing for {book.slug}...")
        book_dir = books_root / book.slug
        book_dir.mkdir(exist_ok=True, parents=True)
        bibliographer_json_path = book_dir / "bibliographer.json"
        bibliographer_json_path.write_text(json.dumps(book.asdict, indent=2, sort_keys=True), encoding="utf-8")


def rename_slug(catalog: CardCatalog, books_root: pathlib.Path, old_slug: str, new_slug: str):
    """Change the slug of a book in the combined library.

    This function will:
    - Change the slug in the combined library.
    - Move the book directory to the new slug.
    - Update the index.md and bibliographer.json files.
    """

    mlogger.debug(f"Renaming slug {old_slug} to {new_slug}")

    for asin, slug in catalog.audibleslugs.contents.items():
        if slug == old_slug:
            catalog.audibleslugs.contents[asin] = new_slug

    for asin, slug in catalog.kindleslugs.contents.items():
        if slug == old_slug:
            catalog.kindleslugs.contents[asin] = new_slug

    for librofm_isbn, slug in catalog.librofmslugs.contents.items():
        if slug == old_slug:
            catalog.librofmslugs.contents[librofm_isbn] = new_slug

    book = catalog.combinedlib.contents[old_slug]
    book.slug = new_slug

    if new_slug not in catalog.combinedlib.contents:
        catalog.combinedlib.contents[new_slug] = catalog.combinedlib.contents[old_slug]
    del catalog.combinedlib.contents[old_slug]

    old_slug_path = books_root / old_slug
    new_slug_path = books_root / new_slug
    if new_slug_path.exists() and old_slug_path.exists():
        shutil.rmtree(old_slug_path)
    elif not new_slug_path.exists() and old_slug_path.exists():
        old_slug_path.rename(new_slug_path)

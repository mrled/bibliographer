import datetime
import json
import pathlib
import shutil
from typing import Dict, List, Optional

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog, CatalogBook, WorkType
from bibliographer.sources.amazon_browser import amazon_browser_search_cached
from bibliographer.sources.covers import lookup_cover
from bibliographer.sources.googlebooks import google_books_retrieve, google_books_search
from bibliographer.sources.openlibrary import isbn2olid, normalize_olid
from bibliographer.sources.wikipedia import wikipedia_relevant_pages


def get_slug_root_for_work(work_type: WorkType, slug_roots: Dict[str, pathlib.Path]) -> pathlib.Path:
    """Get the appropriate slug root for a work type.

    Args:
        work_type: The type of work (book, article, podcast, video, other)
        slug_roots: A dictionary mapping work types to their slug roots.
            Must contain at least a 'default' key.

    Returns:
        The slug root path for the given work type.
    """
    return slug_roots.get(work_type, slug_roots["default"])


def enrich_combined_library(
    catalog: CardCatalog,
    google_books_key: str,
    slug_filter: Optional[List[str]] = None,
):
    """Enrich all entries in the combined library, or specific ones if slug_filter is provided.

    Book-specific enrichment (Google Books, ISBN, OpenLibrary, Amazon ASIN) is only
    performed for CatalogBook entries. Wikipedia enrichment applies to all work types.
    """
    mlogger.debug("Enriching combined library...")

    for slug, work in catalog.combinedlib.contents.items():
        if slug_filter and slug not in slug_filter:
            continue
        if work.skip:
            mlogger.debug(f"Skipping {slug}")
            continue
        mlogger.debug(f"Enriching combined library... processing {slug}")

        # Book-specific enrichment (ISBN, ASIN, Google Books, OpenLibrary)
        if isinstance(work, CatalogBook):
            if not work.gbooks_volid:
                if work.title and work.authors:
                    gbook = google_books_search(catalog, google_books_key, work.title, work.authors[0])
                    if gbook:
                        work.gbooks_volid = gbook.get("bookid")

            if not work.isbn:
                if work.gbooks_volid:
                    gbook = google_books_retrieve(catalog, google_books_key, work.gbooks_volid)
                    if gbook:
                        work.isbn = gbook.get("isbn13")

            if work.publish_date is None:
                if work.gbooks_volid:
                    gbook = google_books_retrieve(catalog, google_books_key, work.gbooks_volid)
                    if gbook:
                        work.publish_date = gbook.get("publishedDate")

            # Normalize any existing OLID and fetch if missing
            if work.openlibrary_id:
                work.openlibrary_id = normalize_olid(work.openlibrary_id)
            elif work.isbn:
                work.openlibrary_id = isbn2olid(catalog, work.isbn)

            if not work.book_asin:
                if work.title and work.authors:
                    searchterm = " ".join([work.title] + work.authors)
                    work.book_asin = amazon_browser_search_cached(catalog, searchterm)

        # Wikipedia enrichment applies to all work types
        if work.urls_wikipedia is None:
            work.urls_wikipedia = wikipedia_relevant_pages(catalog, work.title, work.authors)

    return


def retrieve_covers(
    catalog: CardCatalog,
    slug_roots: Dict[str, pathlib.Path],
    slug_filter: Optional[List[str]] = None,
):
    """Retrieve cover images for book entries in the combined library, or specific ones if slug_filter is provided.

    Only CatalogBook entries have cover fields (gbooks_volid, book_asin, kindle_asin, audible_asin).
    Non-book work types are skipped.

    Args:
        catalog: The CardCatalog containing library data.
        slug_roots: A dictionary mapping work types to their slug roots.
            Must contain at least a 'default' key.
        slug_filter: Optional list of slugs to filter to.
    """
    for work in catalog.combinedlib.contents.values():
        if slug_filter and work.slug not in slug_filter:
            continue
        if work.skip:
            mlogger.debug(f"Skipping cover retrieval for {work.slug}")
            continue
        # Only books have cover-related fields
        if not isinstance(work, CatalogBook):
            mlogger.debug(f"Skipping cover retrieval for non-book {work.slug} (work_type={work.work_type})")
            continue
        if not work.slug:
            mlogger.debug("Skipping cover retrieval for work without slug")
            continue
        mlogger.debug(f"Retrieving cover for {work.slug}...")
        content_root = get_slug_root_for_work(work.work_type, slug_roots)
        book_dir = content_root / work.slug
        fallback_asin = work.book_asin or work.kindle_asin or work.audible_asin
        lookup_cover(
            catalog=catalog,
            gbooks_volid=work.gbooks_volid,
            fallback_asin=fallback_asin,
            book_dir=book_dir,
        )


def write_index_md_files(
    catalog: CardCatalog,
    slug_roots: Dict[str, pathlib.Path],
    slug_filter: Optional[List[str]] = None,
    draft: bool = False,
):
    """Create index.md files for all entries in the combined library, or specific ones if slug_filter is provided.

    Works for all work types (books, articles, podcasts, videos, etc.).
    Never overwrites an existing index.md file.

    Args:
        catalog: The CardCatalog containing library data.
        slug_roots: A dictionary mapping work types to their slug roots.
            Must contain at least a 'default' key.
        slug_filter: Optional list of slugs to filter to.
        draft: If True, include 'draft: true' in the frontmatter.
    """
    for work in catalog.combinedlib.contents.values():
        if slug_filter and work.slug not in slug_filter:
            continue
        if work.skip:
            mlogger.debug(f"[index.md] skipping for {work.slug}")
            continue
        content_root = get_slug_root_for_work(work.work_type, slug_roots)
        work_dir = content_root / work.slug
        index_md_path = work_dir / "index.md"
        if index_md_path.exists():
            mlogger.debug(f"[index.md] already exists for {work.slug}, skipping...")
            continue
        mlogger.debug(f"[index.md] writing for {work.slug}...")
        work_dir.mkdir(exist_ok=True, parents=True)
        if not index_md_path.exists():
            date_str = work.purchase_date or work.consumed_date or ""
            quoted_title = work.title.replace('"', '\\"')
            frontmatter_lines = []
            frontmatter_lines.append("---")
            frontmatter_lines.append(f'title: "{quoted_title}"')
            frontmatter_lines.append(f'BibliographerKey: "{work.slug}"')
            if draft:
                frontmatter_lines.append("draft: true")
            if date_str:
                frontmatter_lines.append(f"date: {date_str}")
            else:
                frontmatter_lines.append("# date:")
            frontmatter_lines.append("---")
            frontmatter = "\n".join(frontmatter_lines) + "\n"
            index_md_path.write_text(frontmatter, encoding="utf-8")


def write_bibliographer_json_files(
    catalog: CardCatalog,
    slug_roots: Dict[str, pathlib.Path],
    slug_filter: Optional[List[str]] = None,
):
    """Create bibliographer.json files for all entries in the combined library, or specific ones if slug_filter is provided.

    Works for all work types (books, articles, podcasts, videos, etc.).
    Always overwrites bibliographer.json files.

    Args:
        catalog: The CardCatalog containing library data.
        slug_roots: A dictionary mapping work types to their slug roots.
            Must contain at least a 'default' key.
        slug_filter: Optional list of slugs to filter to.
    """
    for work in catalog.combinedlib.contents.values():
        if slug_filter and work.slug not in slug_filter:
            continue
        if work.skip:
            mlogger.debug(f"[bibliographer.json] skipping for {work.slug}")
            continue
        mlogger.debug(f"[bibliographer.json] writing for {work.slug}...")
        content_root = get_slug_root_for_work(work.work_type, slug_roots)
        work_dir = content_root / work.slug
        work_dir.mkdir(exist_ok=True, parents=True)
        bibliographer_json_path = work_dir / "bibliographer.json"
        bibliographer_json_path.write_text(json.dumps(work.asdict, indent=2, sort_keys=True), encoding="utf-8")


def rename_slug(
    catalog: CardCatalog,
    slug_roots: Dict[str, pathlib.Path],
    old_slug: str,
    new_slug: str,
):
    """Change the slug of a work in the combined library.

    Works for all work types (books, articles, podcasts, videos, etc.).

    This function will:
    - Change the slug in the combined library.
    - Update slug mappings for book sources (Audible, Kindle, Libro.fm) if applicable.
    - Move the work directory to the new slug.

    Args:
        catalog: The CardCatalog containing library data.
        slug_roots: A dictionary mapping work types to their slug roots.
            Must contain at least a 'default' key.
        old_slug: The current slug to rename.
        new_slug: The new slug name.
    """

    mlogger.debug(f"Renaming slug {old_slug} to {new_slug}")

    # Update book-specific slug mappings (only relevant for books, but harmless for other types)
    for asin, slug in catalog.audibleslugs.contents.items():
        if slug == old_slug:
            catalog.audibleslugs.contents[asin] = new_slug

    for asin, slug in catalog.kindleslugs.contents.items():
        if slug == old_slug:
            catalog.kindleslugs.contents[asin] = new_slug

    for librofm_isbn, slug in catalog.librofmslugs.contents.items():
        if slug == old_slug:
            catalog.librofmslugs.contents[librofm_isbn] = new_slug

    work = catalog.combinedlib.contents[old_slug]
    work.slug = new_slug

    if new_slug not in catalog.combinedlib.contents:
        catalog.combinedlib.contents[new_slug] = catalog.combinedlib.contents[old_slug]
    del catalog.combinedlib.contents[old_slug]

    content_root = get_slug_root_for_work(work.work_type, slug_roots)
    old_slug_path = content_root / old_slug
    new_slug_path = content_root / new_slug
    if new_slug_path.exists() and old_slug_path.exists():
        shutil.rmtree(old_slug_path)
    elif not new_slug_path.exists() and old_slug_path.exists():
        # Create parent directories if needed (for slugs with / like gwern.net/foo)
        parent_dir = new_slug_path.parent
        if parent_dir != content_root:
            parent_dir.mkdir(parents=True, exist_ok=True)
            # Create _index.md for domain directories if it doesn't exist
            index_path = parent_dir / "_index.md"
            if not index_path.exists():
                domain_name = parent_dir.name
                local_now = datetime.datetime.now().astimezone()
                tz_offset = local_now.strftime("%z")
                tz_formatted = tz_offset[:3] + ":" + tz_offset[3:]
                now = local_now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + tz_formatted
                index_content = f"""---
title: "{domain_name} annotations"
date: {now}
---
"""
                index_path.write_text(index_content)
        old_slug_path.rename(new_slug_path)

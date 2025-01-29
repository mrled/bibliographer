import pathlib

from bibliographer import mlogger
from bibliographer.sources.covers import lookup_cover
from bibliographer.enrich import enrich_audible_library, enrich_kindle_library, enrich_manual_books
from bibliographer.sources.wikipedia import wikipedia_relevant_pages
from bibliographer.util.jsonutil import load_json, save_json


def populate_all_sources(
    # Audible
    audible_library_metadata: pathlib.Path,
    audible_library_metadata_enriched: pathlib.Path,
    # Kindle
    kindle_library_metadata: pathlib.Path,
    kindle_library_enriched: pathlib.Path,
    # Manual
    manual_file: pathlib.Path,
    # Common
    asin2gbv_map: pathlib.Path,
    gbooks_volumes: pathlib.Path,
    isbn2olid_map: pathlib.Path,
    search2asin_map: pathlib.Path,
    book_slug_root: pathlib.Path,
    wikipedia_cache: pathlib.Path,
    google_books_key: str,
):
    """
    Loop over Audible, Kindle, and Manual data sources:
    1) Enrich each
    2) Populate each (cover, bibliographer.json, index.md)
    Replaces old separate populate functions.
    """
    # 1) Audible
    enrich_audible_library(
        audible_library_metadata=audible_library_metadata,
        audible_library_metadata_enriched=audible_library_metadata_enriched,
        search2asin_map_path=search2asin_map,
        google_books_key=google_books_key,
        gbooks_volumes=gbooks_volumes,
        asin2gbv_map_path=asin2gbv_map,
        isbn2olid_map_path=isbn2olid_map,
    )
    # Reuse the same approach as the old populate_books_from_audible
    _populate_source(
        base_metadata=audible_library_metadata,
        enriched_metadata=audible_library_metadata_enriched,
        gbooks_volumes=gbooks_volumes,
        isbn2olid_map=isbn2olid_map,
        book_slug_root=book_slug_root,
        wikipedia_cache=wikipedia_cache,
    )

    # 2) Kindle
    enrich_kindle_library(
        kindle_library_metadata=kindle_library_metadata,
        kindle_library_enriched=kindle_library_enriched,
        search2asin_map_path=search2asin_map,
        google_books_key=google_books_key,
        gbooks_volumes=gbooks_volumes,
        asin2gbv_map_path=asin2gbv_map,
        isbn2olid_map_path=isbn2olid_map,
    )
    _populate_source(
        base_metadata=kindle_library_metadata,
        enriched_metadata=kindle_library_enriched,
        gbooks_volumes=gbooks_volumes,
        isbn2olid_map=isbn2olid_map,
        book_slug_root=book_slug_root,
        wikipedia_cache=wikipedia_cache,
    )

    # Step 3: Manual
    enrich_manual_books(
        manual_file=manual_file,
        gbooks_volumes=gbooks_volumes,
        isbn2olid_map=isbn2olid_map,
        search2asin_map=search2asin_map,
        wikipedia_cache=wikipedia_cache,
        google_books_key=google_books_key,
    )
    _populate_source(
        base_metadata=manual_file,
        enriched_metadata=manual_file,
        gbooks_volumes=gbooks_volumes,
        isbn2olid_map=isbn2olid_map,
        book_slug_root=book_slug_root,
        wikipedia_cache=wikipedia_cache,
    )


def _populate_source(
    base_metadata: pathlib.Path,
    enriched_metadata: pathlib.Path,
    gbooks_volumes: pathlib.Path,
    isbn2olid_map: pathlib.Path,
    book_slug_root: pathlib.Path,
    wikipedia_cache: pathlib.Path,
):
    """
    A helper used by populate_all_sources to handle each data source that has
    distinct base_metadata + enriched_metadata. Or for manual, we pass the same file for both.
    """
    base_data = load_json(base_metadata)
    enriched_data = load_json(enriched_metadata)
    book_slug_root.mkdir(parents=True, exist_ok=True)

    mlogger.debug(f"Populating {base_metadata}...")
    for key, info in base_data.items():
        mlogger.debug(f"Populating {base_metadata}... processing {key}")
        e = enriched_data.get(key)
        if not e or e.get("skip"):
            continue

        slug = e.get("slug")
        if not slug:
            continue

        book_dir = book_slug_root / slug
        book_dir.mkdir(exist_ok=True, parents=True)

        fallback_asin = e.get("book_asin") or info.get("kindle_asin") or info.get("audible_asin")
        lookup_cover(
            gbooks_volumes=gbooks_volumes,
            gbooks_volid=e.get("gbooks_volid"),
            fallback_asin=fallback_asin,
            book_dir=book_dir,
        )

        # Create bibliographer.json
        out_json = {}
        out_json["title"] = info["title"]
        out_json["authors"] = info["authors"]

        # if there's a google volume, see if we can set published
        pub = None
        gvid = e.get("gbooks_volid")
        if gvid:
            volinfo = load_json(gbooks_volumes).get(gvid, {})
            pub = volinfo.get("publish_date")
        out_json["published"] = pub
        out_json["isbn"] = e.get("isbn")

        out_json["purchase_date"] = e.get("purchase_date")

        # Build links section
        out_json["links"] = {"metadata": {}, "affiliate": {}, "other": []}
        olid = e.get("openlibrary_id")
        if olid:
            out_json["links"]["metadata"]["openlibrary"] = f"https://openlibrary.org/books/{olid}"
        if gvid:
            out_json["links"]["metadata"]["googlebooks"] = f"https://books.google.com/books?id={gvid}"

        # book_asin is looked up from the search2asin_map;
        # if we have that, we can use it.
        # If not, and there is a kindle_asin set, we can use that.
        if e.get("book_asin"):
            out_json["links"]["affiliate"]["amazon"] = f"https://www.amazon.com/dp/{ e['book_asin'] }"
        elif info.get("kindle_asin"):
            out_json["links"]["affiliate"]["amazon"] = f"https://www.amazon.com/dp/{info['kindle_asin']}"

        # audible_asin is always set for audible items
        if info.get("audible_asin"):
            out_json["links"]["affiliate"]["audible"] = f"https://www.audible.com/pd/{info["audible_asin"]}"

        # Wikipedia
        wdata = wikipedia_relevant_pages(info["title"], info["authors"], wikipedia_cache)
        for k, v in wdata.items():
            out_json["links"]["other"].append({"title": f"{k} - Wikipedia", "url": v})

        # Save
        save_json(book_dir / "bibliographer.json", out_json)

        # Create index.md if it doesn't already exist
        index_md_path = book_dir / "index.md"
        if not index_md_path.exists():
            date_str = e.get("purchase_date") or ""
            quoted_title = info["title"].replace('"', '\\"')
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

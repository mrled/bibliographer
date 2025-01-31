import pathlib

from bibliographer import mlogger
from bibliographer.sources.covers import lookup_cover
from bibliographer.enrich import enrich_audible_library, enrich_kindle_library, enrich_manual_books
from bibliographer.sources.wikipedia import wikipedia_relevant_pages
from bibliographer.util.jsonutil import load_json, save_json
from bibliographer.cardcatalog import CardCatalog, CardCatalogKey


def populate_all_sources(
    catalog: CardCatalog,
    book_slug_root: pathlib.Path,
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
        catalog=catalog,
        google_books_key=google_books_key,
    )
    # Reuse the same approach as the old populate_books_from_audible
    _populate_source(
        catalog=catalog,
        base_key="apicache_audible_library",
        enriched_key="usermaps_audible_library_enriched",
        book_slug_root=book_slug_root,
    )

    # 2) Kindle
    enrich_kindle_library(
        catalog=catalog,
        google_books_key=google_books_key,
    )
    _populate_source(
        catalog=catalog,
        base_key="apicache_kindle_library",
        enriched_key="usermaps_kindle_library_enriched",
        book_slug_root=book_slug_root,
    )

    # Step 3: Manual
    enrich_manual_books(
        catalog=catalog,
        google_books_key=google_books_key,
    )
    _populate_source(
        catalog=catalog,
        base_key="usermaps_manual_library",
        enriched_key="usermaps_manual_library",
        book_slug_root=book_slug_root,
    )


def _populate_source(
    catalog: CardCatalog,
    base_key: CardCatalogKey,
    enriched_key: CardCatalogKey,
    book_slug_root: pathlib.Path,
):
    """
    A helper used by populate_all_sources to handle each data source that has
    distinct base_metadata + enriched_metadata. Or for manual, we pass the same file for both.
    """
    base_data = catalog.contents(base_key)
    enriched_data = catalog.contents(enriched_key)
    book_slug_root.mkdir(parents=True, exist_ok=True)

    mlogger.debug(f"Populating {base_key}...")
    for key, info in base_data.items():
        mlogger.debug(f"Populating {base_key}... processing {key}")
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
            catalog=catalog,
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
            volinfo = catalog.contents("apicache_gbooks_volumes").get(gvid, {})
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
        wdata = wikipedia_relevant_pages(catalog, info["title"], info["authors"])
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

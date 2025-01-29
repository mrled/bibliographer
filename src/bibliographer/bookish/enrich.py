import pathlib

from bibliographer import mlogger
from bibliographer.bookish.amazon_browser import amazon_browser_search_cached
from bibliographer.bookish.googlebooks import asin2gbv, google_books_search
from bibliographer.bookish.openlibrary import isbn2olid
from bibliographer.hugo import slugify
from bibliographer.util.jsonutil import load_json, save_json


def enrich_audible_library(
    audible_library_metadata: pathlib.Path,
    audible_library_metadata_enriched: pathlib.Path,
    search2asin_map_path: pathlib.Path,
    google_books_key: str,
    gbooks_volumes: pathlib.Path,
    asin2gbv_map_path: pathlib.Path,
    isbn2olid_map_path: pathlib.Path,
):
    """
    For each item, ensure we have { slug, gbooks_volid, openlibrary_id, isbn, book_asin, skip, purchase_date }.
    """
    base_data = load_json(audible_library_metadata)
    enriched_data = load_json(audible_library_metadata_enriched)

    mlogger.debug(f"Enriching Audible library...")
    for asin, info in base_data.items():
        mlogger.debug(f"Enriching Audible library... processing {asin}")
        if asin not in enriched_data:
            enriched_data[asin] = {}
        edata = enriched_data[asin]
        if edata.get("skip") is True:
            continue
        if "purchase_date" not in edata:
            edata["purchase_date"] = info.get("purchase_date", None)
        if edata.get("slug") is None:
            try:
                edata["slug"] = slugify(info["title"])
            except:
                edata["slug"] = None
        if edata.get("gbooks_volid") is None:
            try:
                gvid = asin2gbv(
                    asin2gbv_map=asin2gbv_map_path,
                    asin=asin,
                    title=info["title"],
                    author=info["authors"][0] if info["authors"] else "",
                    google_books_key=google_books_key,
                    gbooks_volumes=gbooks_volumes,
                )
                edata["gbooks_volid"] = gvid
            except:
                edata["gbooks_volid"] = None

        if edata.get("isbn") is None and edata.get("gbooks_volid"):
            volinfo = load_json(gbooks_volumes).get(edata["gbooks_volid"], {})
            if volinfo.get("isbn13"):
                edata["isbn"] = volinfo["isbn13"]

        if edata.get("openlibrary_id") is None and edata.get("isbn"):
            isbn = edata["isbn"]
            olid = isbn2olid(isbn2olid_map_path, isbn)
            edata["openlibrary_id"] = olid

        if edata.get("book_asin") is None:
            authors = " ".join(info.get("authors", []))
            st = f"{info['title']} {authors}"
            found_asin = amazon_browser_search_cached(search2asin_map_path, st)
            edata["book_asin"] = found_asin

        if "skip" not in edata:
            edata["skip"] = False

    save_json(audible_library_metadata_enriched, enriched_data)


def enrich_kindle_library(
    kindle_library_metadata: pathlib.Path,
    kindle_library_enriched: pathlib.Path,
    search2asin_map_path: pathlib.Path,
    google_books_key: str,
    gbooks_volumes: pathlib.Path,
    asin2gbv_map_path: pathlib.Path,
    isbn2olid_map_path: pathlib.Path,
):
    base_data = load_json(kindle_library_metadata)
    enriched_data = load_json(kindle_library_enriched)

    mlogger.debug(f"Enriching Kindle library...")
    for asin, info in base_data.items():
        mlogger.debug(f"Enriching Kindle library... processing {asin}")
        if asin not in enriched_data:
            enriched_data[asin] = {}
        edata = enriched_data[asin]
        if edata.get("skip") is True:
            continue

        if edata.get("slug") is None:
            edata["slug"] = slugify(info["title"])

        # store purchase date
        if "purchase_date" not in edata:
            date_val = info.get("purchaseDate")  # might be "YYYY-MM-DD" or None
            edata["purchase_date"] = date_val

        if edata.get("gbooks_volid") is None:
            gvid = asin2gbv(
                asin2gbv_map=asin2gbv_map_path,
                asin=asin,
                title=info["title"],
                author=info["authors"][0] if info["authors"] else "",
                google_books_key=google_books_key,
                gbooks_volumes=gbooks_volumes,
            )
            edata["gbooks_volid"] = gvid

        if edata.get("isbn") is None and edata.get("gbooks_volid"):
            volinfo = load_json(gbooks_volumes).get(edata["gbooks_volid"], {})
            if volinfo.get("isbn13"):
                edata["isbn"] = volinfo["isbn13"]

        if edata.get("openlibrary_id") is None and edata.get("isbn"):
            isbn = edata["isbn"]
            olid = isbn2olid(isbn2olid_map_path, isbn)
            edata["openlibrary_id"] = olid

        if edata.get("book_asin") is None:
            searchterm = f"{info['title']} {info['authors'][0] if info['authors'] else ''}"
            found_asin = amazon_browser_search_cached(search2asin_map_path, searchterm)
            edata["book_asin"] = found_asin

        if "skip" not in edata:
            edata["skip"] = False

    save_json(kindle_library_enriched, enriched_data)


def enrich_manual_books(
    manual_file: pathlib.Path,
    gbooks_volumes: pathlib.Path,
    isbn2olid_map: pathlib.Path,
    search2asin_map: pathlib.Path,
    wikipedia_cache: pathlib.Path,
    google_books_key: str,
):
    manual_data = load_json(manual_file)
    changed = False

    mlogger.debug("Enriching manual books...")
    for slug, info in manual_data.items():
        mlogger.debug(f"Enriching manual books... processing {slug}")
        if info.get("skip"):
            continue

        if not info.get("gbooks_volid"):
            if info.get("title") and info.get("authors"):
                title = info["title"]
                auth = info["authors"][0] if info["authors"] else ""
                sr = google_books_search(google_books_key, gbooks_volumes, title, auth)
                if sr:
                    info["gbooks_volid"] = sr.get("bookid")
                    if sr.get("isbn13"):
                        info["isbn"] = sr["isbn13"]
                    changed = True

        if info.get("isbn") and not info.get("openlibrary_id"):
            olid = isbn2olid(isbn2olid_map, info["isbn"])
            if olid:
                info["openlibrary_id"] = olid
                changed = True

        if not info.get("book_asin") and info.get("title") and info.get("authors"):
            searchterm = f"{info['title']} {info['authors'][0]}"
            found_asin = amazon_browser_search_cached(search2asin_map, searchterm)
            if found_asin:
                info["book_asin"] = found_asin
                changed = True

    if changed:
        save_json(manual_file, manual_data)

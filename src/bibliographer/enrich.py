from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog
from bibliographer.sources.amazon_browser import amazon_browser_search_cached
from bibliographer.sources.googlebooks import asin2gbv, google_books_search
from bibliographer.sources.openlibrary import isbn2olid
from bibliographer.hugo import slugify


def enrich_audible_library(
    catalog: CardCatalog,
    google_books_key: str,
):
    """
    For each item, ensure we have { slug, gbooks_volid, openlibrary_id, isbn, book_asin, skip, purchase_date }.
    """
    mlogger.debug(f"Enriching Audible library...")
    base_data = catalog.contents("apicache_audible_library")
    enriched_data = catalog.contents("usermaps_audible_library_enriched")

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
                    catalog=catalog,
                    asin=asin,
                    title=info["title"],
                    author=info["authors"][0] if info["authors"] else "",
                    google_books_key=google_books_key,
                )
                edata["gbooks_volid"] = gvid
            except:
                edata["gbooks_volid"] = None

        if edata.get("isbn") is None and edata.get("gbooks_volid"):
            volinfo = catalog.contents("apicache_gbooks_volumes").get(edata["gbooks_volid"], {})
            if volinfo.get("isbn13"):
                edata["isbn"] = volinfo["isbn13"]

        if edata.get("openlibrary_id") is None and edata.get("isbn"):
            isbn = edata["isbn"]
            olid = isbn2olid(catalog, isbn)
            edata["openlibrary_id"] = olid

        if edata.get("book_asin") is None:
            authors = " ".join(info.get("authors", []))
            st = f"{info['title']} {authors}"
            found_asin = amazon_browser_search_cached(catalog, st)
            edata["book_asin"] = found_asin

        if "skip" not in edata:
            edata["skip"] = False


def enrich_kindle_library(
    catalog: CardCatalog,
    google_books_key: str,
):
    base_data = catalog.contents("apicache_kindle_library")
    enriched_data = catalog.contents("usermaps_kindle_library_enriched")

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
                catalog=catalog,
                asin=asin,
                title=info["title"],
                author=info["authors"][0] if info["authors"] else "",
                google_books_key=google_books_key,
            )
            edata["gbooks_volid"] = gvid

        if edata.get("isbn") is None and edata.get("gbooks_volid"):
            volinfo = catalog.contents("apicache_gbooks_volumes").get(edata["gbooks_volid"], {})
            if volinfo.get("isbn13"):
                edata["isbn"] = volinfo["isbn13"]

        if edata.get("openlibrary_id") is None and edata.get("isbn"):
            isbn = edata["isbn"]
            olid = isbn2olid(catalog, isbn)
            edata["openlibrary_id"] = olid

        if edata.get("book_asin") is None:
            searchterm = f"{info['title']} {info['authors'][0] if info['authors'] else ''}"
            found_asin = amazon_browser_search_cached(catalog, searchterm)
            edata["book_asin"] = found_asin

        if "skip" not in edata:
            edata["skip"] = False


def enrich_manual_books(
    catalog: CardCatalog,
    google_books_key: str,
):
    manual_data = catalog.contents("usermaps_manual_library")

    mlogger.debug("Enriching manual books...")
    for slug, info in manual_data.items():
        mlogger.debug(f"Enriching manual books... processing {slug}")
        if info.get("skip"):
            continue

        if not info.get("gbooks_volid"):
            if info.get("title") and info.get("authors"):
                title = info["title"]
                auth = info["authors"][0] if info["authors"] else ""
                sr = google_books_search(catalog, google_books_key, title, auth)
                if sr:
                    info["gbooks_volid"] = sr.get("bookid")
                    if sr.get("isbn13"):
                        info["isbn"] = sr["isbn13"]
                    changed = True

        if info.get("isbn") and not info.get("openlibrary_id"):
            olid = isbn2olid(catalog, info["isbn"])
            if olid:
                info["openlibrary_id"] = olid
                changed = True

        if not info.get("book_asin") and info.get("title") and info.get("authors"):
            searchterm = f"{info['title']} {info['authors'][0]}"
            found_asin = amazon_browser_search_cached(catalog, searchterm)
            if found_asin:
                info["book_asin"] = found_asin
                changed = True

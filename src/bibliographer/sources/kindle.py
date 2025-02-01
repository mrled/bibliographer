import pathlib

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog, CombinedCatalogBook
from bibliographer.util.jsonutil import load_json
from bibliographer.hugo import slugify


def ingest_kindle_library(
    catalog: CardCatalog,
    export_json: pathlib.Path,
):
    """Ingest a new Kindle library export and save to the Kindle library apicache."""
    kindlelib = catalog.contents("apicache_kindle_library")
    new_data = load_json(export_json)

    for item in new_data:
        asin = item.get("asin")
        if not asin:
            mlogger.error(f"Missing ASIN in Kindle item {item}")
            continue
        kindlelib[asin] = item


def process_kindle_library(
    catalog: CardCatalog,
):
    """Process existing Kindle library data and save to the combined library.

    Modify the raw data as required:
    - The authors list always seems to have just a single element,
      even for multi-author works,
      and the single element contains each authors name terminated by a colon.
    - Set the 'kindle_asin' key to the original 'asin' key.
    """
    kindlelib = catalog.contents("apicache_kindle_library")
    kindleslugs = catalog.contents("usermaps_kindle_slugs")

    for asin, item in kindlelib.items():
        mlogger.debug(f"Processing Kindle library ASIN {asin}")
        book = CombinedCatalogBook()
        book.kindle_asin = asin
        book.title = item.get("title")
        book.authors = item["authors"][0].rstrip(":").split(":")
        book.kindle_cover_url = item.get("productUrl")

        if asin not in kindleslugs:
            kindleslugs[asin] = slugify(item["title"])
        book.slug = kindleslugs[asin]

        if book.slug in catalog.combinedlib.contents:
            catalog.combinedlib.contents[book.slug].merge(book)
        else:
            catalog.combinedlib.contents[book.slug] = book

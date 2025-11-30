import pathlib

from bibliographer import mlogger
from bibliographer.cardcatalog import CardCatalog, CatalogBook
from bibliographer.util.jsonutil import load_json
from bibliographer.hugo import slugify


def ingest_kindle_library(
    catalog: CardCatalog,
    export_json: pathlib.Path,
):
    """Ingest a new Kindle library export and save to the Kindle library apicache."""
    new_data = load_json(export_json)

    for item in new_data:
        asin = item.get("asin")
        if not asin:
            mlogger.error(f"Missing ASIN in Kindle item {item}")
            continue
        catalog.kindlelib.contents[asin] = item


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
    for asin, item in catalog.kindlelib.contents.items():
        mlogger.debug(f"Processing Kindle library ASIN {asin}")
        book = CatalogBook()
        book.kindle_asin = asin
        book.title = item.get("title")
        book.authors = item["authors"][0].rstrip(":").split(":")
        book.kindle_cover_url = item.get("productUrl")

        if asin not in catalog.kindleslugs.contents:
            catalog.kindleslugs.contents[asin] = slugify(item["title"])
        book.slug = catalog.kindleslugs.contents[asin]

        if book.slug in catalog.combinedlib.contents:
            catalog.combinedlib.contents[book.slug].merge(book)
        else:
            catalog.combinedlib.contents[book.slug] = book

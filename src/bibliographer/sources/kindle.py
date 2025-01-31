import pathlib

from bibliographer.cardcatalog import CardCatalog
from bibliographer.util.jsonutil import load_json


def ingest_kindle_library(
    catalog: CardCatalog,
    export_json: pathlib.Path,
):
    """
    Load old_data, load new_data from export_json, ensure each new item has 'purchaseDate', merge, and save.

    Old data is a JSON dict where keys are ASINs and values are dicts.
    New data is a JSON list of dicts.

    Modify the new data as required:
    - The authors list always seems to have just a single element,
      even for multi-author works,
      and the single element contains each authors name terminated by a colon.
    - Set the 'kindle_asin' key to the original 'asin' key.
    """
    kindlelib = catalog.contents("apicache_kindle_library")
    new_data = load_json(export_json)

    for item in new_data:
        asin = item.get("asin")
        if not asin:
            continue
        authors = item["authors"][0].rstrip(":").split(":")
        item["authors"] = authors
        kindle_asin = item.get("asin")
        del item["asin"]
        item["kindle_asin"] = kindle_asin
        kindlelib[asin] = item

"""Data stores for bibliographer."""

import dataclasses
import pathlib
from typing import Literal

from bibliographer.util.jsonutil import load_json, save_json


# CardCatalogKey is a type hint for the keys of the CardCatalog.files dictionary.
CardCatalogKey = Literal[
    "apicache_audible_library",
    "apicache_kindle_library",
    "apicache_gbooks_volumes",
    "usermaps_asin2gbv_map",
    "usermaps_isbn2olid_map",
    "usermaps_search2asin",
    "usermaps_wikipedia_relevant",
    "usermaps_audible_library_enriched",
    "usermaps_kindle_library_enriched",
    "usermaps_manual_library",
]


@dataclasses.dataclass
class CardCatalogEntry:
    """A single entry in the card catalog."""

    name: str
    path: pathlib.Path
    contents: dict | None = None


class CardCatalog:
    """CardCatalog: all data stores for bibliographer."""

    files: dict[CardCatalogKey, CardCatalogEntry] = {}

    def __init__(self, data_root: pathlib.Path):
        self.data_root = data_root

        self.dir_apicache = data_root / "apicache"
        self.dir_usermaps = data_root / "usermaps"
        self.dir_apicache.mkdir(parents=True, exist_ok=True)
        self.dir_usermaps.mkdir(parents=True, exist_ok=True)

        self.files = {
            # apicache
            "apicache_audible_library": CardCatalogEntry(
                name="audible_library_metadata",
                path=self.dir_apicache / "audible_library_metadata.json",
            ),
            "apicache_kindle_library": CardCatalogEntry(
                name="kindle_library_metadata",
                path=self.dir_apicache / "kindle_library_metadata.json",
            ),
            "apicache_gbooks_volumes": CardCatalogEntry(
                name="gbooks_volumes",
                path=self.dir_apicache / "gbooks_volumes.json",
            ),
            # usermaps
            "usermaps_asin2gbv_map": CardCatalogEntry(
                name="asin2gbv_map",
                path=self.dir_usermaps / "asin2gbv_map.json",
            ),
            "usermaps_isbn2olid_map": CardCatalogEntry(
                name="isbn2olid_map",
                path=self.dir_usermaps / "isbn2olid_map.json",
            ),
            "usermaps_search2asin": CardCatalogEntry(
                name="search2asin",
                path=self.dir_usermaps / "search2asin.json",
            ),
            "usermaps_wikipedia_relevant": CardCatalogEntry(
                name="wikipedia_relevant",
                path=self.dir_usermaps / "wikipedia_relevant.json",
            ),
            "usermaps_audible_library_enriched": CardCatalogEntry(
                name="audible_library_metadata_enriched",
                path=self.dir_usermaps / "audible_library_metadata_enriched.json",
            ),
            "usermaps_kindle_library_enriched": CardCatalogEntry(
                name="kindle_library_metadata_enriched",
                path=self.dir_usermaps / "kindle_library_metadata_enriched.json",
            ),
            "usermaps_manual_library": CardCatalogEntry(
                name="manual",
                path=self.dir_usermaps / "manual.json",
            ),
        }

    def contents(self, key: CardCatalogKey):
        """Get the contents of a specific file."""
        entry = self.files[key]
        if entry.contents is None:
            entry.contents = load_json(entry.path)
        return entry.contents

    def save(self, key: CardCatalogKey, data: dict):
        """Save data to a specific file."""
        entry = self.files[key]
        entry.contents = data

    def persist(self):
        """Save all data to disk."""
        for entry in self.files.values():
            if entry.contents is not None:
                save_json(entry.path, entry.contents)
                entry.contents = None

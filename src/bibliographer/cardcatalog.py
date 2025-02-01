"""Data stores for bibliographer."""

import dataclasses
import pathlib
from typing import Dict, Generic, Literal, Optional, TypedDict, TypeVar

from bibliographer.util.jsonutil import load_json, save_json


@dataclasses.dataclass
class CombinedCatalogBook:
    """A single book entry in the combined library."""

    title: str | None = None
    authors: list[str] = dataclasses.field(default_factory=list)
    isbn: str | None = None
    slug: str | None = None
    skip: bool = False

    publish_date: Optional[str] = None
    purchase_date: str | None = None
    read_date: str | None = None

    gbooks_volid: str | None = None
    openlibrary_id: str | None = None

    book_asin: str | None = None
    kindle_asin: str | None = None
    audible_asin: str | None = None

    audible_cover_url: str | None = None
    kindle_cover_url: str | None = None

    urls_wikipedia: Optional[Dict[str, str]] = None

    def merge(self, other: "CombinedCatalogBook"):
        """Merge another CombinedCatalogBook2 into this one.

        Do not overwrite any existing values;
        only add new values from the other object.
        """
        for key in dataclasses.fields(self):
            if getattr(self, key.name) is None:
                setattr(self, key.name, getattr(other, key.name))

    @property
    def asdict(self):
        """Return a JSON-serializable dict of this object."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """Create a new CombinedCatalogBook from a dict."""
        return cls(**data)


# CardCatalogKey is a type hint for the keys of the CardCatalog.files dictionary.
CardCatalogKey = Literal[
    "apicache_audible_library",
    "apicache_kindle_library",
    "apicache_gbooks_volumes",
    "usermaps_audible_slugs",
    "usermaps_kindle_slugs",
    "usermaps_asin2gbv_map",
    "usermaps_isbn2olid_map",
    "usermaps_search2asin",
    "usermaps_wikipedia_relevant",
]


T = TypeVar("T", bound=object)


@dataclasses.dataclass
class TypedCardCatalogEntry(Generic[T]):
    """A single entry in the card catalog."""

    name: str
    path: pathlib.Path
    _contents: Dict[str, T] | None = None

    @property
    def contents(self):
        """Get the contents of this entry."""
        if self._contents is None:
            loaded = load_json(self.path)
            self._contents = {k: CombinedCatalogBook.from_dict(v) for k, v in loaded.items()}
        return self._contents

    def save(self):
        """Save the in-memory data to disk."""
        if self._contents is not None:
            serializable = {k: v.asdict for k, v in self._contents.items()}
            save_json(self.path, serializable)
            self._contents = None


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

        self.combinedlib = TypedCardCatalogEntry[CombinedCatalogBook](
            name="combined_library",
            path=self.dir_usermaps / "combined_library.json",
        )

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
            "usermaps_audible_slugs": CardCatalogEntry(
                name="audible_slugs",
                path=self.dir_usermaps / "audible_slugs.json",
            ),
            "usermaps_kindle_slugs": CardCatalogEntry(
                name="kindle_slugs",
                path=self.dir_usermaps / "kindle_slugs.json",
            ),
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
        self.combinedlib.save()

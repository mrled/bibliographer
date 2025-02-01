"""Data stores for bibliographer."""

import dataclasses
import pathlib
from typing import Any, Dict, Generic, Literal, Optional, Type, TypedDict, TypeVar

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


T = TypeVar("T", bound=object)


@dataclasses.dataclass
class TypedCardCatalogEntry(Generic[T]):
    """A single entry in the card catalog."""

    path: pathlib.Path
    contents_type: Type[T]
    _contents: Dict[str, T] | None = None

    @property
    def contents(self):
        """Get the contents of this entry."""
        if self._contents is None:
            if self.contents_type is CombinedCatalogBook:
                loaded = load_json(self.path)
                self._contents = {k: CombinedCatalogBook.from_dict(v) for k, v in loaded.items()}
            else:
                self._contents = load_json(self.path)
        return self._contents

    def save(self):
        """Save the in-memory data to disk."""
        if self._contents is not None:
            if self.contents_type is CombinedCatalogBook:
                serializable = {k: v.asdict for k, v in self._contents.items()}
            else:
                serializable = self._contents
            save_json(self.path, serializable)
            self._contents = None


class CardCatalog:
    """CardCatalog: all data stores for bibliographer."""

    def __init__(self, data_root: pathlib.Path):
        self.data_root = data_root

        self.dir_apicache = data_root / "apicache"
        self.dir_usermaps = data_root / "usermaps"
        self.dir_apicache.mkdir(parents=True, exist_ok=True)
        self.dir_usermaps.mkdir(parents=True, exist_ok=True)

        # apicache
        self.audiblelib = TypedCardCatalogEntry[dict](
            path=self.dir_apicache / "audible_library_metadata.json",
            contents_type=dict,
        )
        self.kindlelib = TypedCardCatalogEntry[dict](
            path=self.dir_apicache / "kindle_library_metadata.json",
            contents_type=dict,
        )
        self.gbooks_volumes = TypedCardCatalogEntry[dict](
            path=self.dir_apicache / "gbooks_volumes.json",
            contents_type=dict,
        )
        self.librofmlib = TypedCardCatalogEntry[dict](
            path=self.dir_apicache / "librofm_library.json",
            contents_type=dict,
        )

        # usermaps
        self.combinedlib = TypedCardCatalogEntry[CombinedCatalogBook](
            path=self.dir_usermaps / "combined_library.json",
            contents_type=CombinedCatalogBook,
        )
        self.audibleslugs = TypedCardCatalogEntry[str](
            path=self.dir_usermaps / "audible_slugs.json",
            contents_type=str,
        )
        self.kindleslugs = TypedCardCatalogEntry[str](
            path=self.dir_usermaps / "kindle_slugs.json",
            contents_type=str,
        )
        self.asin2gbv_map = TypedCardCatalogEntry[str](
            path=self.dir_usermaps / "asin2gbv_map.json",
            contents_type=str,
        )
        self.isbn2olid_map = TypedCardCatalogEntry[str](
            path=self.dir_usermaps / "isbn2olid_map.json",
            contents_type=str,
        )
        self.search2asin = TypedCardCatalogEntry[str](
            path=self.dir_usermaps / "search2asin.json",
            contents_type=str,
        )
        self.wikipedia_relevant = TypedCardCatalogEntry[Dict[str, str]](
            path=self.dir_usermaps / "wikipedia_relevant.json",
            contents_type=Dict[str, str],
        )

        self.allentries: list[TypedCardCatalogEntry] = [
            self.audiblelib,
            self.kindlelib,
            self.librofmlib,
            self.gbooks_volumes,
            self.combinedlib,
            self.audibleslugs,
            self.kindleslugs,
            self.asin2gbv_map,
            self.isbn2olid_map,
            self.search2asin,
            self.wikipedia_relevant,
        ]

    def persist(self):
        """Save all data to disk."""
        for entry in self.allentries:
            entry.save()

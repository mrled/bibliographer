"""Data stores for bibliographer."""

import dataclasses
import pathlib
from typing import Any, Dict, Generic, Literal, Optional, Type, TypedDict, TypeVar

from bibliographer.util.jsonutil import load_json, save_json


@dataclasses.dataclass
class CombinedCatalogBook:
    """A single book entry in the combined library."""

    title: Optional[str] = None
    """The book title."""

    authors: list[str] = dataclasses.field(default_factory=list)
    """A list of authors"""

    isbn: Optional[str] = None
    """The ISBN of the best* print edition of the book.

    Best* meaning something like the first edition,
    or the easiest to buy new.
    """

    slug: Optional[str] = None
    """A slugified version of the title for use in URLs."""

    skip: bool = False
    """Whether to skip the book.

    If true, don't generate any content pages retrieve API results or covers for the book.
    """

    publish_date: Optional[str] = None
    """The publication date of the original edition of the book."""

    purchase_date: Optional[str] = None
    """The date the book was purchased."""

    read_date: Optional[str] = None
    """The date the user read the book."""

    gbooks_volid: Optional[str] = None
    """The Google Books volume ID."""

    openlibrary_id: Optional[str] = None
    """The OpenLibrary OLID."""

    book_asin: Optional[str] = None
    """The Amazon ASIN of a currently-available print edition of the book."""

    kindle_asin: Optional[str] = None
    """The Amazon ASIN of the Kindle edition of the book."""

    audible_asin: Optional[str] = None
    """The Amazon ASIN of the Audible edition of the book."""

    librofm_isbn: Optional[str] = None
    """The ISBN of the Libro.fm edition of the book.

    It appears that Libro.fm ISBNs are unique to Libro.fm;
    there isn't a generic audio ISBN. ?
    """

    librofm_publish_date: Optional[str] = None
    """The publication date of the Libro.fm edition of the book."""

    audible_cover_url: Optional[str] = None
    """The URL of the Audible cover image."""

    kindle_cover_url: Optional[str] = None
    """The URL of the Kindle cover image."""

    librofm_cover_url: Optional[str] = None
    """The URL of the Libro.fm cover image."""

    urls_wikipedia: Optional[Dict[str, str]] = None
    """URLs to Wikipedia pages for the book and its authors, if any."""

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
    _contents: Optional[Dict[str, T]] = None

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
        self.wikipedia_api_cache = TypedCardCatalogEntry[str](
            path=self.dir_apicache / "wikipedia_api_cache.json",
            contents_type=str,
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
        self.librofmslugs = TypedCardCatalogEntry[str](
            path=self.dir_usermaps / "librofm_slugs.json",
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
        self.wikipedia_usermap = TypedCardCatalogEntry[Dict[str, str]](
            path=self.dir_usermaps / "wikipedia_usermap.json",
            contents_type=Dict[str, str],
        )

        self.allentries: list[TypedCardCatalogEntry] = [
            self.audiblelib,
            self.kindlelib,
            self.librofmlib,
            self.gbooks_volumes,
            self.wikipedia_api_cache,
            self.combinedlib,
            self.audibleslugs,
            self.librofmslugs,
            self.kindleslugs,
            self.isbn2olid_map,
            self.search2asin,
            self.wikipedia_usermap,
        ]

    def persist(self):
        """Save all data to disk."""
        for entry in self.allentries:
            entry.save()

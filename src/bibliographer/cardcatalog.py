"""Data stores for bibliographer."""

import dataclasses
import pathlib
from typing import Any, Dict, Generic, Literal, Optional, Type, TypedDict, TypeVar

from bibliographer.util.jsonutil import load_json, save_json


@dataclasses.dataclass
class ManualWork:
    """A manually added work entry (article, book, etc.)."""

    slug: str
    """A slugified identifier for use in URLs (mandatory)."""

    work_type: str = "article"
    """The type of work (article, book, etc.)."""

    title: Optional[str] = None
    """The work title."""

    authors: list[str] = dataclasses.field(default_factory=list)
    """A list of authors."""

    url: Optional[str] = None
    """The URL of the work (for articles and web-based works)."""

    read_date: Optional[str] = None
    """The date the user read/consumed the work."""

    publish_date: Optional[str] = None
    """The publication date of the work."""

    isbn: Optional[str] = None
    """The ISBN (for books)."""

    purchase_date: Optional[str] = None
    """The date the work was purchased (for books)."""

    @property
    def asdict(self):
        """Return a JSON-serializable dict of this object."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """Create a new ManualWork from a dict."""
        return cls(**data)


@dataclasses.dataclass
class CombinedWork:
    """A combined work entry that can represent any type of content."""

    slug: str
    """A slugified identifier for use in URLs."""

    work_type: str = "article"
    """The type of work (article, book, etc.)."""

    title: Optional[str] = None
    """The work title."""

    authors: list[str] = dataclasses.field(default_factory=list)
    """A list of authors."""

    url: Optional[str] = None
    """The URL of the work (for articles and web-based works)."""

    read_date: Optional[str] = None
    """The date the user read/consumed the work."""

    publish_date: Optional[str] = None
    """The publication date of the work."""

    isbn: Optional[str] = None
    """The ISBN (for books)."""

    purchase_date: Optional[str] = None
    """The date the work was purchased (for books)."""

    skip: bool = False
    """Whether to skip the work.

    If true, don't generate any content pages for the work.
    """

    def merge(self, other: "CombinedWork"):
        """Merge another CombinedWork into this one.

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
        """Create a new CombinedWork from a dict."""
        return cls(**data)


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
            elif self.contents_type is ManualWork:
                loaded = load_json(self.path)
                self._contents = {k: ManualWork.from_dict(v) for k, v in loaded.items()}
            elif self.contents_type is CombinedWork:
                loaded = load_json(self.path)
                self._contents = {k: CombinedWork.from_dict(v) for k, v in loaded.items()}
            else:
                self._contents = load_json(self.path)
        return self._contents

    def save(self):
        """Save the in-memory data to disk."""
        if self._contents is not None:
            if self.contents_type in (CombinedCatalogBook, ManualWork, CombinedWork):
                serializable = {k: v.asdict for k, v in self._contents.items()}
            else:
                serializable = self._contents
            save_json(self.path, serializable)
            self._contents = None


class CardCatalog:
    """CardCatalog: all data stores for bibliographer."""

    @classmethod
    def from_data_root(cls, data_root: pathlib.Path) -> "CardCatalog":
        """Create a CardCatalog from a data root directory.

        This is a convenience method for backward compatibility and testing.
        It uses the default directory structure:
        - data_root/apicache/ for API cache files
        - data_root/usermaps/ for user mapping files
        """
        apicache_dir = data_root / "apicache"
        usermaps_dir = data_root / "usermaps"

        return cls(
            audible_library_file=apicache_dir / "audible_library_metadata.json",
            kindle_library_file=apicache_dir / "kindle_library_metadata.json",
            gbooks_volumes_file=apicache_dir / "gbooks_volumes.json",
            librofm_library_file=apicache_dir / "librofm_library.json",
            combined_library_file=usermaps_dir / "combined_library.json",
            audible_slugs_file=usermaps_dir / "audible_slugs.json",
            kindle_slugs_file=usermaps_dir / "kindle_slugs.json",
            librofm_slugs_file=usermaps_dir / "librofm_slugs.json",
            isbn2olid_map_file=usermaps_dir / "isbn2olid_map.json",
            search2asin_file=usermaps_dir / "search2asin.json",
            wikipedia_relevant_file=usermaps_dir / "wikipedia_relevant.json",
            manual_works_file=usermaps_dir / "manual_works.json",
            combined_works_file=usermaps_dir / "combined_works.json",
        )

    def __init__(
        self,
        # Individual file paths
        audible_library_file: pathlib.Path,
        kindle_library_file: pathlib.Path,
        gbooks_volumes_file: pathlib.Path,
        librofm_library_file: pathlib.Path,
        combined_library_file: pathlib.Path,
        audible_slugs_file: pathlib.Path,
        kindle_slugs_file: pathlib.Path,
        librofm_slugs_file: pathlib.Path,
        isbn2olid_map_file: pathlib.Path,
        search2asin_file: pathlib.Path,
        wikipedia_relevant_file: pathlib.Path,
        manual_works_file: pathlib.Path,
        combined_works_file: pathlib.Path,
    ):
        # Create parent directories for all files
        for filepath in [
            audible_library_file,
            kindle_library_file,
            gbooks_volumes_file,
            librofm_library_file,
            combined_library_file,
            audible_slugs_file,
            kindle_slugs_file,
            librofm_slugs_file,
            isbn2olid_map_file,
            search2asin_file,
            wikipedia_relevant_file,
            manual_works_file,
            combined_works_file,
        ]:
            filepath.parent.mkdir(parents=True, exist_ok=True)

        # apicache
        self.audiblelib = TypedCardCatalogEntry[dict](
            path=audible_library_file,
            contents_type=dict,
        )
        self.kindlelib = TypedCardCatalogEntry[dict](
            path=kindle_library_file,
            contents_type=dict,
        )
        self.gbooks_volumes = TypedCardCatalogEntry[dict](
            path=gbooks_volumes_file,
            contents_type=dict,
        )
        self.librofmlib = TypedCardCatalogEntry[dict](
            path=librofm_library_file,
            contents_type=dict,
        )

        # usermaps
        self.combinedlib = TypedCardCatalogEntry[CombinedCatalogBook](
            path=combined_library_file,
            contents_type=CombinedCatalogBook,
        )
        self.audibleslugs = TypedCardCatalogEntry[str](
            path=audible_slugs_file,
            contents_type=str,
        )
        self.kindleslugs = TypedCardCatalogEntry[str](
            path=kindle_slugs_file,
            contents_type=str,
        )
        self.librofmslugs = TypedCardCatalogEntry[str](
            path=librofm_slugs_file,
            contents_type=str,
        )
        self.isbn2olid_map = TypedCardCatalogEntry[str](
            path=isbn2olid_map_file,
            contents_type=str,
        )
        self.search2asin = TypedCardCatalogEntry[str](
            path=search2asin_file,
            contents_type=str,
        )
        self.wikipedia_relevant = TypedCardCatalogEntry[Dict[str, str]](
            path=wikipedia_relevant_file,
            contents_type=Dict[str, str],
        )
        self.manualworks = TypedCardCatalogEntry[ManualWork](
            path=manual_works_file,
            contents_type=ManualWork,
        )
        self.combinedworks = TypedCardCatalogEntry[CombinedWork](
            path=combined_works_file,
            contents_type=CombinedWork,
        )

        self.allentries: list[TypedCardCatalogEntry] = [
            self.audiblelib,
            self.kindlelib,
            self.librofmlib,
            self.gbooks_volumes,
            self.combinedlib,
            self.audibleslugs,
            self.librofmslugs,
            self.kindleslugs,
            self.isbn2olid_map,
            self.search2asin,
            self.wikipedia_relevant,
            self.manualworks,
            self.combinedworks,
        ]

    def persist(self):
        """Save all data to disk."""
        for entry in self.allentries:
            entry.save()

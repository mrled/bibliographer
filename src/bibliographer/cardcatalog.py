"""Data stores for bibliographer."""

import dataclasses
import pathlib
import warnings
from typing import Any, Dict, Generic, Literal, Optional, Type, TypedDict, TypeVar, Union

from bibliographer.util.jsonutil import load_json, save_json


# Work type discriminator
WorkType = Literal["book", "article", "podcast", "video", "other"]


@dataclasses.dataclass
class CombinedCatalogWork:
    """Base class for all work types in the combined library.

    This is the base class for books, articles, podcasts, videos, and other works.
    """

    title: Optional[str] = None
    """The work title."""

    authors: list[str] = dataclasses.field(default_factory=list)
    """A list of authors/creators."""

    slug: Optional[str] = None
    """A slugified version of the title for use in URLs."""

    skip: bool = False
    """Whether to skip the work.

    If true, don't generate any content pages, retrieve API results, or covers for the work.
    """

    publish_date: Optional[str] = None
    """The publication date of the original edition of the work."""

    purchase_date: Optional[str] = None
    """The date the work was purchased/acquired."""

    consumed_date: Optional[str] = None
    """The date the user consumed the work (read/watched/listened)."""

    urls_wikipedia: Optional[Dict[str, str]] = None
    """URLs to Wikipedia pages for the work and its authors, if any."""

    work_type: WorkType = "other"
    """The type of work (book, article, podcast, video, other)."""

    def merge(self, other: "CombinedCatalogWork"):
        """Merge another work into this one.

        This base implementation raises NotImplementedError.
        Only CatalogBook supports merging.
        """
        raise NotImplementedError(
            f"merge() is not supported for {self.__class__.__name__}. "
            "Only CatalogBook supports merging from multiple sources."
        )

    @property
    def asdict(self) -> dict:
        """Return a JSON-serializable dict of this object."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CombinedCatalogWork":
        """Factory method that creates the appropriate subclass based on work_type.

        If called on CombinedCatalogWork, dispatches to the correct subclass.
        If called on a subclass, creates an instance of that subclass.
        """
        # If called on a specific subclass, create that type directly
        if cls is not CombinedCatalogWork:
            # Filter to only fields that exist on this class
            valid_fields = {f.name for f in dataclasses.fields(cls)}
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}
            return cls(**filtered_data)

        # Factory dispatch based on work_type
        work_type = data.get("work_type", "book")  # Default to "book" for backward compatibility

        if work_type == "book":
            return CatalogBook.from_dict(data)
        elif work_type == "article":
            return CatalogArticle.from_dict(data)
        elif work_type == "podcast":
            return CatalogPodcastEpisode.from_dict(data)
        elif work_type == "video":
            return CatalogVideo.from_dict(data)
        else:
            # For "other" or unknown types, create base class instance
            valid_fields = {f.name for f in dataclasses.fields(CombinedCatalogWork)}
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}
            return CombinedCatalogWork(**filtered_data)


@dataclasses.dataclass
class CatalogBook(CombinedCatalogWork):
    """A book entry in the combined library.

    Books can be merged from multiple sources (Kindle, Audible, OpenLibrary, etc.).
    """

    work_type: WorkType = "book"
    """The type of work - always 'book' for this class."""

    isbn: Optional[str] = None
    """The ISBN of the best* print edition of the book.

    Best* meaning something like the first edition,
    or the easiest to buy new.
    """

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

    gbooks_volid: Optional[str] = None
    """The Google Books volume ID."""

    openlibrary_id: Optional[str] = None
    """The OpenLibrary OLID."""

    audible_cover_url: Optional[str] = None
    """The URL of the Audible cover image."""

    kindle_cover_url: Optional[str] = None
    """The URL of the Kindle cover image."""

    librofm_cover_url: Optional[str] = None
    """The URL of the Libro.fm cover image."""

    @property
    def read_date(self) -> Optional[str]:
        """Backward compatibility alias for consumed_date."""
        return self.consumed_date

    @read_date.setter
    def read_date(self, value: Optional[str]):
        """Backward compatibility alias for consumed_date."""
        self.consumed_date = value

    def merge(self, other: "CombinedCatalogWork"):
        """Merge another CatalogBook into this one.

        Do not overwrite any existing values;
        only add new values from the other object.

        Note: Although the type signature accepts CombinedCatalogWork for LSP compliance,
        this method is intended for merging books and will only copy fields that exist on both.
        """
        for field in dataclasses.fields(self):
            if getattr(self, field.name) is None:
                # Only copy if the other object has this field
                if hasattr(other, field.name):
                    setattr(self, field.name, getattr(other, field.name))

    @classmethod
    def from_dict(cls, data: dict) -> "CatalogBook":
        """Create a new CatalogBook from a dict.

        Handles backward compatibility for read_date -> consumed_date rename.
        """
        # Handle read_date -> consumed_date migration
        if "read_date" in data and "consumed_date" not in data:
            data = data.copy()
            data["consumed_date"] = data.pop("read_date")
        elif "read_date" in data and "consumed_date" in data:
            # Both present - prefer consumed_date, remove read_date
            data = data.copy()
            del data["read_date"]

        # Filter to only fields that exist on this class
        valid_fields = {f.name for f in dataclasses.fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


@dataclasses.dataclass
class CatalogArticle(CombinedCatalogWork):
    """An article entry in the combined library."""

    work_type: WorkType = "article"
    """The type of work - always 'article' for this class."""

    url: Optional[str] = None
    """The canonical URL of the article."""

    publication: Optional[str] = None
    """The name of the journal, blog, magazine, or publication."""


@dataclasses.dataclass
class CatalogPodcastEpisode(CombinedCatalogWork):
    """A podcast episode entry in the combined library."""

    work_type: WorkType = "podcast"
    """The type of work - always 'podcast' for this class."""

    url: Optional[str] = None
    """The episode URL."""

    podcast_name: Optional[str] = None
    """The name of the podcast."""

    episode_number: Optional[int] = None
    """The episode number, if applicable."""


@dataclasses.dataclass
class CatalogVideo(CombinedCatalogWork):
    """A video entry in the combined library."""

    work_type: WorkType = "video"
    """The type of work - always 'video' for this class."""

    url: Optional[str] = None
    """The video URL."""


# Backward compatibility alias
CombinedCatalogBook = CatalogBook


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
            if self.contents_type is CombinedCatalogBook or self.contents_type is CatalogBook:
                loaded = load_json(self.path)
                # Use the factory method to create the appropriate subclass
                self._contents = {k: CombinedCatalogWork.from_dict(v) for k, v in loaded.items()}
            else:
                self._contents = load_json(self.path)
        return self._contents

    def save(self):
        """Save the in-memory data to disk."""
        if self._contents is not None:
            if self.contents_type is CombinedCatalogBook or self.contents_type is CatalogBook:
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
            raindrop_highlights_file=apicache_dir / "raindrop_highlights.json",
            combined_library_file=usermaps_dir / "combined_library.json",
            audible_slugs_file=usermaps_dir / "audible_slugs.json",
            kindle_slugs_file=usermaps_dir / "kindle_slugs.json",
            librofm_slugs_file=usermaps_dir / "librofm_slugs.json",
            raindrop_slugs_file=usermaps_dir / "raindrop_slugs.json",
            isbn2olid_map_file=usermaps_dir / "isbn2olid_map.json",
            search2asin_file=usermaps_dir / "search2asin.json",
            wikipedia_relevant_file=usermaps_dir / "wikipedia_relevant.json",
        )

    def __init__(
        self,
        # Individual file paths
        audible_library_file: pathlib.Path,
        kindle_library_file: pathlib.Path,
        gbooks_volumes_file: pathlib.Path,
        librofm_library_file: pathlib.Path,
        raindrop_highlights_file: pathlib.Path,
        combined_library_file: pathlib.Path,
        audible_slugs_file: pathlib.Path,
        kindle_slugs_file: pathlib.Path,
        librofm_slugs_file: pathlib.Path,
        raindrop_slugs_file: pathlib.Path,
        isbn2olid_map_file: pathlib.Path,
        search2asin_file: pathlib.Path,
        wikipedia_relevant_file: pathlib.Path,
    ):
        # Create parent directories for all files
        for filepath in [
            audible_library_file,
            kindle_library_file,
            gbooks_volumes_file,
            librofm_library_file,
            raindrop_highlights_file,
            combined_library_file,
            audible_slugs_file,
            kindle_slugs_file,
            librofm_slugs_file,
            raindrop_slugs_file,
            isbn2olid_map_file,
            search2asin_file,
            wikipedia_relevant_file,
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
        self.raindrop_highlights = TypedCardCatalogEntry[dict](
            path=raindrop_highlights_file,
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
        self.raindropslugs = TypedCardCatalogEntry[str](
            path=raindrop_slugs_file,
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

        self.allentries: list[TypedCardCatalogEntry] = [
            self.audiblelib,
            self.kindlelib,
            self.librofmlib,
            self.raindrop_highlights,
            self.gbooks_volumes,
            self.combinedlib,
            self.audibleslugs,
            self.librofmslugs,
            self.kindleslugs,
            self.raindropslugs,
            self.isbn2olid_map,
            self.search2asin,
            self.wikipedia_relevant,
        ]

    def persist(self):
        """Save all data to disk."""
        for entry in self.allentries:
            entry.save()

#!/usr/bin/env python3
import argparse
import dataclasses
import pathlib
import sys
import tomllib
from typing import Callable, Generic, List, Optional, Type, TypeVar
import logging
import subprocess

from bibliographer import add_console_handler, mlogger
from bibliographer.cardcatalog import CardCatalog
from bibliographer.cli.util import (
    AutoDescriptionArgumentParser,
    exceptional_exception_handler,
    get_argparse_help_string,
    idb_excepthook,
)
from bibliographer.enrich import (
    rename_slug,
    enrich_combined_library,
    retrieve_covers,
    write_bibliographer_json_files,
    write_index_md_files,
)
from bibliographer.hugo import slugify
from bibliographer.sources.amazon_browser import amazon_browser_search_cached
from bibliographer.sources.audible import (
    audible_login,
    decrypt_credentials,
    encrypt_credentials,
    process_audible_library,
    retrieve_audible_library,
)
from bibliographer.sources.covers import cover_path, download_cover_from_url
from bibliographer.sources.googlebooks import google_books_retrieve
from bibliographer.sources.kindle import ingest_kindle_library, process_kindle_library
from bibliographer.sources.librofm import librofm_login, librofm_retrieve_library, process_librofm_library
from bibliographer.sources.raindrop import raindrop_retrieve_highlights
from bibliographer.sources.add import (
    add_book,
    add_article,
    add_podcast,
    add_video,
)


def find_repo_root() -> Optional[pathlib.Path]:
    """Find the root of the repo by searching for a .git directory

    Returns None if not found.
    """
    current = pathlib.Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def get_version() -> str:
    """Get the version string

    If the package is installed editable, return the git revision with "-dirty" if dirty.
    Otherwise, return the version from pyproject.toml.
    """
    # Check if we're in an editable install by looking for the package source
    try:
        import bibliographer

        package_path = pathlib.Path(bibliographer.__file__).parent

        # Look for .git directory starting from the package directory
        git_dir = None
        current = package_path
        while current != current.parent:
            if (current / ".git").exists():
                git_dir = current
                break
            current = current.parent

        if git_dir:
            # We found a git repository, so this is likely an editable install
            # Get the git revision
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], cwd=git_dir, capture_output=True, text=True, check=True
            )
            revision = result.stdout.strip()

            # Check if the working tree is dirty
            result = subprocess.run(
                ["git", "status", "--porcelain"], cwd=git_dir, capture_output=True, text=True, check=True
            )
            is_dirty = bool(result.stdout.strip())

            if is_dirty:
                return f"{revision}-dirty"
            return revision
    except Exception:
        # If anything goes wrong, fall through to reading from pyproject.toml
        pass

    # Not an editable install or git detection failed, read from pyproject.toml
    try:
        # Find pyproject.toml relative to the package
        import bibliographer

        package_path = pathlib.Path(bibliographer.__file__).parent
        pyproject_path = package_path.parent.parent / "pyproject.toml"

        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)
                return pyproject_data.get("project", {}).get("version", "unknown")
    except Exception:
        pass

    return "unknown"


def makeparser() -> argparse.ArgumentParser:
    """Return the argument parser"""
    parser = AutoDescriptionArgumentParser(
        description="Manage Audible/Kindle libraries, enrich them, and populate local book repos."
    )
    parser.add_argument(
        "-D",
        "--debug",
        action="store_true",
        help="Drop into an interactive debugger on unhandled exceptions.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=pathlib.Path,
        help="Path to TOML config file, defaulting to a file called .bibliographer.toml in the repo root",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging of API calls.")
    # These options are hidden from --help; use 'help-file-paths' subcommand to see them
    parser.add_argument("-b", "--bibliographer-data-root", help=argparse.SUPPRESS)
    parser.add_argument("-s", "--default-slug-root", help=argparse.SUPPRESS)
    parser.add_argument("--book-slug-root", help=argparse.SUPPRESS)
    parser.add_argument("--article-slug-root", help=argparse.SUPPRESS)
    parser.add_argument("--podcast-slug-root", help=argparse.SUPPRESS)
    parser.add_argument("--video-slug-root", help=argparse.SUPPRESS)

    # Individual file overrides for apicache
    # These options are hidden from --help; use 'help-file-paths' subcommand to see them
    parser.add_argument("--audible-library-file", help=argparse.SUPPRESS)
    parser.add_argument("--kindle-library-file", help=argparse.SUPPRESS)
    parser.add_argument("--gbooks-volumes-file", help=argparse.SUPPRESS)
    parser.add_argument("--librofm-library-file", help=argparse.SUPPRESS)
    parser.add_argument("--raindrop-highlights-file", help=argparse.SUPPRESS)

    # Individual file overrides for usermaps
    parser.add_argument("--combined-library-file", help=argparse.SUPPRESS)
    parser.add_argument("--audible-slugs-file", help=argparse.SUPPRESS)
    parser.add_argument("--kindle-slugs-file", help=argparse.SUPPRESS)
    parser.add_argument("--librofm-slugs-file", help=argparse.SUPPRESS)
    parser.add_argument("--raindrop-slugs-file", help=argparse.SUPPRESS)
    parser.add_argument("--isbn2olid-map-file", help=argparse.SUPPRESS)
    parser.add_argument("--search2asin-file", help=argparse.SUPPRESS)
    parser.add_argument("--wikipedia-relevant-file", help=argparse.SUPPRESS)
    parser.add_argument(
        "-i",
        "--individual-bibliographer-json",
        action="store_true",
        help="Write out each work to its own JSON file (in addition to the combined bibliographer.json), under the appropriate slug root/SLUG/bibliographer.json",
    )
    # Service-related options are hidden from --help; use 'help-services' subcommand to see them
    parser.add_argument("-a", "--audible-login-file", help=argparse.SUPPRESS)
    parser.add_argument("--audible-auth-password", help=argparse.SUPPRESS)
    parser.add_argument("--audible-auth-password-cmd", help=argparse.SUPPRESS)
    parser.add_argument("-g", "--google-books-key", help=argparse.SUPPRESS)
    parser.add_argument("-G", "--google-books-key-cmd", help=argparse.SUPPRESS)
    parser.add_argument("--librofm-username", help=argparse.SUPPRESS)
    parser.add_argument("--librofm-password", help=argparse.SUPPRESS)
    parser.add_argument("--librofm-password-cmd", help=argparse.SUPPRESS)
    parser.add_argument("--raindrop-token", help=argparse.SUPPRESS)
    parser.add_argument("--raindrop-token-cmd", help=argparse.SUPPRESS)

    # Take care to add help AND description to each subparser.
    # Help is shown by the parent parser
    # e.g. "bibliographer --help" shows the help string for each subparser;
    # description is shown by the subparser itself
    # e.g. "bibliographer audible --help" shows the description for the audible subparser.

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Populate
    sp_pop = subparsers.add_parser("populate", help="Populate bibliographer.json files")
    sp_pop.add_argument("--slug", nargs="*", help="Populate only specific books by slug (can specify multiple)")

    # Audible
    sp_audible = subparsers.add_parser("audible", help="Audible operations")
    sp_audible_sub = sp_audible.add_subparsers(dest="audible_subcommand", required=True)
    sp_audible_sub.add_parser("retrieve", help="Retrieve the Audible library")

    # Audible credentials subcommand
    sp_audible_cred = sp_audible_sub.add_parser("credentials", help="Manage Audible credentials")
    sp_audible_cred_sub = sp_audible_cred.add_subparsers(dest="credentials_subcommand", required=True)
    sp_audible_cred_enc = sp_audible_cred_sub.add_parser("encrypt", help="Load unencrypted credentials and output to terminal")
    sp_audible_cred_enc.add_argument("source", type=pathlib.Path, help="Path to unencrypted credentials file")
    sp_audible_cred_dec = sp_audible_cred_sub.add_parser("decrypt", help="Load encrypted credentials and output to terminal")
    sp_audible_cred_dec.add_argument("source", type=pathlib.Path, help="Path to encrypted credentials file")

    # Kindle
    sp_kindle = subparsers.add_parser("kindle", help="Kindle operations")
    sp_kindle_sub = sp_kindle.add_subparsers(dest="kindle_subcommand", required=True)
    sp_ki_ing = sp_kindle_sub.add_parser("ingest", help="Ingest a new Kindle library export JSON")
    sp_ki_ing.add_argument("export_json", type=pathlib.Path, help="Path to the Kindle library export JSON")

    # Googlebook subcommand
    sp_gb = subparsers.add_parser("googlebook", help="Operate on Google Books data")
    sp_gb_sub = sp_gb.add_subparsers(dest="googlebook_subcommand", required=True)
    # subcommand "requery"
    sp_gb_req = sp_gb_sub.add_parser("requery", help="Overwrite the local Google Books cache for a volume ID")
    sp_gb_req.add_argument("volume_ids", nargs="+", help="One or more volume IDs to re-download")

    # Amazon subcommand
    sp_amazon = subparsers.add_parser("amazon", help="Amazon forced re-scrape")
    sp_amazon_sub = sp_amazon.add_subparsers(dest="amazon_subcommand", required=True)
    sp_amazon_req = sp_amazon_sub.add_parser("requery", help="Force re-scrape for one or more search terms.")
    sp_amazon_req.add_argument("searchterms", nargs="+", help="Search terms to re-scrape from Amazon")

    # Libro.fm subcommand
    sp_librofm = subparsers.add_parser("librofm", help="Libro.fm operations")
    sp_librofm_sub = sp_librofm.add_subparsers(dest="librofm_subcommand", required=True)
    sp_librofm_sub.add_parser("retrieve", help="Retrieve the Libro.fm library")

    # Raindrop.io subcommand
    sp_raindrop = subparsers.add_parser("raindrop", help="Raindrop.io operations")
    sp_raindrop_sub = sp_raindrop.add_subparsers(dest="raindrop_subcommand", required=True)
    sp_raindrop_highlights = sp_raindrop_sub.add_parser("highlights", help="Raindrop.io highlights operations")
    sp_raindrop_highlights_sub = sp_raindrop_highlights.add_subparsers(
        dest="raindrop_highlights_subcommand", required=True
    )
    sp_raindrop_highlights_sub.add_parser("retrieve", help="Retrieve all highlights from Raindrop.io")

    # Add subcommand
    sp_add = subparsers.add_parser("add", help="Add works to the library")
    sp_add_sub = sp_add.add_subparsers(dest="add_subcommand", required=True)

    # add book
    sp_add_book = sp_add_sub.add_parser("book", help="Add a book")
    sp_add_book.add_argument("--title", help="Book title")
    sp_add_book.add_argument("--authors", nargs="+", help="Authors (allows multiple)")
    sp_add_book.add_argument("--isbn", help="ISBN if known")
    sp_add_book.add_argument("--purchase-date", help="Purchase date if any (YYYY-MM-DD)")
    sp_add_book.add_argument("--read-date", help="Read/consumed date if any (YYYY-MM-DD)")
    sp_add_book.add_argument("--slug", help="Slug for URL (set to a slugified title by default)")

    # add article
    sp_add_article = sp_add_sub.add_parser("article", help="Add an article")
    sp_add_article.add_argument("--title", help="Article title")
    sp_add_article.add_argument("--authors", nargs="+", help="Authors (allows multiple)")
    sp_add_article.add_argument("--url", help="Article URL")
    sp_add_article.add_argument("--publication", help="Publication name (journal, blog, magazine)")
    sp_add_article.add_argument("--purchase-date", help="Purchase/acquired date if any (YYYY-MM-DD)")
    sp_add_article.add_argument("--read-date", help="Read date if any (YYYY-MM-DD)")
    sp_add_article.add_argument("--slug", help="Slug for URL (set to a slugified title by default)")

    # add podcast
    sp_add_podcast = sp_add_sub.add_parser("podcast", help="Add a podcast episode")
    sp_add_podcast.add_argument("--title", help="Episode title")
    sp_add_podcast.add_argument("--authors", nargs="+", help="Hosts/authors (allows multiple)")
    sp_add_podcast.add_argument("--url", help="Episode URL")
    sp_add_podcast.add_argument("--podcast-name", help="Name of the podcast")
    sp_add_podcast.add_argument("--episode-number", type=int, help="Episode number")
    sp_add_podcast.add_argument("--purchase-date", help="Purchase/acquired date if any (YYYY-MM-DD)")
    sp_add_podcast.add_argument("--listened-date", help="Listened date if any (YYYY-MM-DD)")
    sp_add_podcast.add_argument("--slug", help="Slug for URL (set to a slugified title by default)")

    # add video
    sp_add_video = sp_add_sub.add_parser("video", help="Add a video")
    sp_add_video.add_argument("--title", help="Video title")
    sp_add_video.add_argument("--authors", nargs="+", help="Creators (allows multiple)")
    sp_add_video.add_argument("--url", help="Video URL")
    sp_add_video.add_argument("--purchase-date", help="Purchase/acquired date if any (YYYY-MM-DD)")
    sp_add_video.add_argument("--watched-date", help="Watched date if any (YYYY-MM-DD)")
    sp_add_video.add_argument("--slug", help="Slug for URL (set to a slugified title by default)")

    # slug subcommand
    sp_slug = subparsers.add_parser("slug", help="Manage slugs")
    sp_slug_sub = sp_slug.add_subparsers(dest="slug_subcommand", required=True)

    # slug show
    sp_slug_show = sp_slug_sub.add_parser("show", help="Show what slug would be generated for a given title")
    sp_slug_show.add_argument("title", help="Title to slugify")

    # slug rename
    sp_slug_rename = sp_slug_sub.add_parser("rename", help="Renamed a slug")
    sp_slug_rename.add_argument("old_slug", help="Old slug")
    sp_slug_rename.add_argument("new_slug", help="New slug")

    # slug regenerate
    sp_slug_regen = sp_slug_sub.add_parser("regenerate", help="Regenerate a slug")
    sp_slug_regen.add_argument("slug", help="Slug to regenerate")
    sp_slug_regen.add_argument("--interactive", "-i", action="store_true", help="Prompt before taking any action")

    # cover subcommand
    sp_cover = subparsers.add_parser("cover", help="Cover operations")
    sp_cover_sub = sp_cover.add_subparsers(dest="cover_subcommand", required=True)
    sp_cover_set = sp_cover_sub.add_parser("set", help="Set a cover image")
    sp_cover_set.add_argument("slug", help="Book slug")
    sp_cover_set.add_argument("url", help="URL for a cover image")

    # cover retrieve
    sp_cover_sub.add_parser("retrieve", help="Retrieve cover images for all books that don't have them")

    # cover list-missing
    sp_cover_sub.add_parser("list-missing", help="List books missing cover images")

    # version subcommand
    subparsers.add_parser("version", help="Show version information")

    # help-file-paths subcommand
    subparsers.add_parser("help-file-paths", help="Show data file path options")

    # help-services subcommand
    subparsers.add_parser("help-services", help="Show service authentication options")

    return parser


def get_help_string() -> str:
    """Get a string containing program help"""
    return get_argparse_help_string("bibliographer", makeparser())


def print_file_paths_help() -> None:
    """Print help for data file path options."""
    print("""Data File Path Options
======================

These options allow you to override the default paths for data files.

Root Directories:
  -b, --bibliographer-data-root  Root directory for bibliographer data
                                 (default: ./bibliographer/data)
  -s, --default-slug-root        Default root directory for slug folders
                                 (default: ./bibliographer/books)
  --book-slug-root               Override slug root for books only
                                 (defaults to --default-slug-root)
  --article-slug-root            Override slug root for articles only
                                 (defaults to --default-slug-root)
  --podcast-slug-root            Override slug root for podcasts only
                                 (defaults to --default-slug-root)
  --video-slug-root              Override slug root for videos only
                                 (defaults to --default-slug-root)

API Cache Files:
  --audible-library-file       Path to Audible library metadata file
  --kindle-library-file        Path to Kindle library metadata file
  --gbooks-volumes-file        Path to Google Books volumes cache file
  --librofm-library-file       Path to Libro.fm library metadata file
  --raindrop-highlights-file   Path to Raindrop.io highlights cache file

User Map Files:
  --combined-library-file   Path to combined library file
  --audible-slugs-file      Path to Audible slugs mapping file
  --kindle-slugs-file       Path to Kindle slugs mapping file
  --librofm-slugs-file      Path to Libro.fm slugs mapping file
  --raindrop-slugs-file     Path to Raindrop.io URL to slug mapping file
  --isbn2olid-map-file      Path to ISBN to OpenLibrary ID mapping file
  --search2asin-file        Path to search term to ASIN mapping file
  --wikipedia-relevant-file Path to Wikipedia relevant pages file

These options can also be set in the config file (.bibliographer.toml).
""")


def print_services_help() -> None:
    """Print help for service authentication options."""
    print("""Service Authentication Options
==============================

These options configure authentication for external services.

Audible:
  -a, --audible-login-file       Path to Audible credentials file
                                 (default: ./.bibliographer-audible-auth.json)
  --audible-auth-password        Password to encrypt/decrypt the Audible
                                 authentication file
  --audible-auth-password-cmd    Command to retrieve the Audible auth password
                                 (e.g. from a password manager)

Google Books:
  -g, --google-books-key         Google Books API key
  -G, --google-books-key-cmd     Command to retrieve the Google Books API key
                                 (e.g. from a password manager)

Libro.fm:
  --librofm-username             Libro.fm username (email address)
  --librofm-password             Libro.fm password
  --librofm-password-cmd         Command to retrieve the Libro.fm password
                                 (e.g. from a password manager)

Raindrop.io:
  --raindrop-token               Raindrop.io API access token
  --raindrop-token-cmd           Command to retrieve the Raindrop.io token
                                 (e.g. from a password manager)

These options can also be set in the config file (.bibliographer.toml).
""")


def get_example_config() -> str:
    """Get a string containing an example TOML config file

    This is kind of hacky,
    and a better solution might be to use the configparser module for the config file
    because unlike TOML Python can write it natively.
    """
    result = ""
    for param in ConfigurationParameterSet.scalars():
        value = param.default
        if isinstance(value, str):
            value = f'"{value}"'
        elif isinstance(value, bool):
            # Make this look right for TOML
            value = str(value).lower()
        result += f"{param.key} = {value}\n"
    for param in ConfigurationParameterSet.paths():
        # Skip parameters with None defaults (these are optional file overrides)
        if param.default is not None:
            result += f'{param.key} = "{param.default}"\n'
    return result


def find_file_in_parents(filenames: list[str]) -> Optional[pathlib.Path]:
    """Find a file in the current directory or any parent directory"""
    current = pathlib.Path.cwd()
    while current != current.parent:
        for filename in filenames:
            filepath = current / filename
            if filepath.exists():
                return filepath
        current = current.parent
    return None


T = TypeVar("T")


@dataclasses.dataclass
class ConfigurationParameter(Generic[T]):
    """A generic class for parameters set in the config file"""

    key: str
    vtype: Type[T]
    default: T


class SecretValueGetter:
    """A class for getting secrets

    The user can provide either the value directly,
    or a command to run to get the value.
    """

    _getter: Callable[[], str]

    def __init__(self, getcmd: Optional[str] = None, key: Optional[str] = None):
        self._key = None
        self._getter = lambda: self._key or ""
        if key:
            self._key = key
        elif getcmd:
            self._getter = (
                lambda: subprocess.run(getcmd, shell=True, check=True, capture_output=True).stdout.decode().strip()
            )

    def get(self) -> str:
        if not self._key:
            self._key = self._getter()
        return self._key or ""


class ConfigurationParameterSet:
    """All parameters set in the config file"""

    @staticmethod
    def scalars() -> List[ConfigurationParameter]:
        """Scalar parameters are set directly"""
        return [
            ConfigurationParameter("debug", bool, False),
            ConfigurationParameter("verbose", bool, False),
            ConfigurationParameter("google_books_key", str, ""),
            ConfigurationParameter("google_books_key_cmd", str, ""),
            ConfigurationParameter("audible_auth_password", str, ""),
            ConfigurationParameter("audible_auth_password_cmd", str, ""),
            ConfigurationParameter("librofm_username", str, ""),
            ConfigurationParameter("librofm_password", str, ""),
            ConfigurationParameter("librofm_password_cmd", str, ""),
            ConfigurationParameter("raindrop_token", str, ""),
            ConfigurationParameter("raindrop_token_cmd", str, ""),
            ConfigurationParameter("individual_bibliographer_json", bool, False),
        ]

    @staticmethod
    def paths() -> List[ConfigurationParameter]:
        """Path parameters are handled specially

        Relative paths set on the command-line are resolved relative to $PWD,
        while relative paths set in the config file are resolved relative to the config file's directory.
        """
        return [
            ConfigurationParameter("default_slug_root", pathlib.Path, pathlib.Path("./bibliographer/books")),
            ConfigurationParameter("book_slug_root", pathlib.Path, None),
            ConfigurationParameter("article_slug_root", pathlib.Path, None),
            ConfigurationParameter("podcast_slug_root", pathlib.Path, None),
            ConfigurationParameter("video_slug_root", pathlib.Path, None),
            ConfigurationParameter(
                "audible_login_file", pathlib.Path, pathlib.Path("./.bibliographer-audible-auth.json")
            ),
            ConfigurationParameter("bibliographer_data_root", pathlib.Path, pathlib.Path("./bibliographer/data")),
            # Individual file overrides for apicache
            ConfigurationParameter("audible_library_file", pathlib.Path, None),
            ConfigurationParameter("kindle_library_file", pathlib.Path, None),
            ConfigurationParameter("gbooks_volumes_file", pathlib.Path, None),
            ConfigurationParameter("librofm_library_file", pathlib.Path, None),
            ConfigurationParameter("raindrop_highlights_file", pathlib.Path, None),
            # Individual file overrides for usermaps
            ConfigurationParameter("combined_library_file", pathlib.Path, None),
            ConfigurationParameter("audible_slugs_file", pathlib.Path, None),
            ConfigurationParameter("kindle_slugs_file", pathlib.Path, None),
            ConfigurationParameter("librofm_slugs_file", pathlib.Path, None),
            ConfigurationParameter("raindrop_slugs_file", pathlib.Path, None),
            ConfigurationParameter("isbn2olid_map_file", pathlib.Path, None),
            ConfigurationParameter("search2asin_file", pathlib.Path, None),
            ConfigurationParameter("wikipedia_relevant_file", pathlib.Path, None),
        ]


def resolve_path_if_relative(path: pathlib.Path | str, root: pathlib.Path | str) -> pathlib.Path:
    """Return a resolved path

    If the path is relative, resolve it relative to the root.
    """
    path = pathlib.Path(path) if isinstance(path, str) else path
    root = pathlib.Path(root) if isinstance(root, str) else root
    if not path.is_absolute():
        return root / path
    return path


def parseargs(arguments: List[str]):
    """Parse command-line arguments

    NOTE: Defaults in this function will override defaults in the TOML config file.
    """
    parser = makeparser()

    parsed = parser.parse_args(arguments)

    if not parsed.config:
        parsed.config = find_file_in_parents(["bibliographer.toml", ".bibliographer.toml"])

    if parsed.config and parsed.config.exists():
        with open(parsed.config, "rb") as f:
            config_data = tomllib.load(f)
    else:
        config_data = {}

    # Handle scalars directly
    for param in ConfigurationParameterSet.scalars():
        clival = getattr(parsed, param.key)
        if clival:
            setattr(parsed, param.key, clival)
        elif param.key in config_data:
            setattr(parsed, param.key, param.vtype(config_data[param.key]))
        else:
            setattr(parsed, param.key, param.default)

    # Handle paths specially,
    # so that relative paths in the config file are resolved relative to the config file's directory
    for param in ConfigurationParameterSet.paths():
        # Set the path to the default value first (may be None)
        path = None
        if param.default is not None:
            path = resolve_path_if_relative(param.default, pathlib.Path.cwd())

        clival = getattr(parsed, param.key)
        if clival:
            # This is a command-line argument, so resolve it relative to $PWD
            path = resolve_path_if_relative(getattr(parsed, param.key), pathlib.Path.cwd())
        elif parsed.config and param.key in config_data:
            # The value was set in the config file, so resolve it relative to the config file's directory
            path = resolve_path_if_relative(config_data[param.key], parsed.config.parent)
        setattr(parsed, param.key, path)

    # Now compute derived paths for files that weren't explicitly set
    # Individual file overrides take precedence, otherwise derive from bibliographer_data_root
    data_root = parsed.bibliographer_data_root
    apicache_dir = data_root / "apicache"
    usermaps_dir = data_root / "usermaps"

    # Set individual file defaults based on data_root if not explicitly set
    if parsed.audible_library_file is None:
        parsed.audible_library_file = apicache_dir / "audible_library_metadata.json"
    if parsed.kindle_library_file is None:
        parsed.kindle_library_file = apicache_dir / "kindle_library_metadata.json"
    if parsed.gbooks_volumes_file is None:
        parsed.gbooks_volumes_file = apicache_dir / "gbooks_volumes.json"
    if parsed.librofm_library_file is None:
        parsed.librofm_library_file = apicache_dir / "librofm_library.json"
    if parsed.raindrop_highlights_file is None:
        parsed.raindrop_highlights_file = apicache_dir / "raindrop_highlights.json"

    if parsed.combined_library_file is None:
        parsed.combined_library_file = usermaps_dir / "combined_library.json"
    if parsed.audible_slugs_file is None:
        parsed.audible_slugs_file = usermaps_dir / "audible_slugs.json"
    if parsed.kindle_slugs_file is None:
        parsed.kindle_slugs_file = usermaps_dir / "kindle_slugs.json"
    if parsed.librofm_slugs_file is None:
        parsed.librofm_slugs_file = usermaps_dir / "librofm_slugs.json"
    if parsed.raindrop_slugs_file is None:
        parsed.raindrop_slugs_file = usermaps_dir / "raindrop_slugs.json"
    if parsed.isbn2olid_map_file is None:
        parsed.isbn2olid_map_file = usermaps_dir / "isbn2olid_map.json"
    if parsed.search2asin_file is None:
        parsed.search2asin_file = usermaps_dir / "search2asin.json"
    if parsed.wikipedia_relevant_file is None:
        parsed.wikipedia_relevant_file = usermaps_dir / "wikipedia_relevant.json"

    return parser, parsed


###############################################################################
# Main Entry
###############################################################################


def main(arguments: list[str]) -> int:
    parser, args = parseargs(arguments)

    log_level = logging.INFO
    if args.debug:
        sys.excepthook = idb_excepthook
    if args.verbose:
        log_level = logging.DEBUG
    add_console_handler(log_level)

    google_books_key = SecretValueGetter(
        getcmd=args.google_books_key_cmd,
        key=args.google_books_key,
    )
    audible_auth_password = SecretValueGetter(
        getcmd=args.audible_auth_password_cmd,
        key=args.audible_auth_password,
    )
    librofm_password = SecretValueGetter(getcmd=args.librofm_password_cmd, key=args.librofm_password)
    raindrop_token = SecretValueGetter(getcmd=args.raindrop_token_cmd, key=args.raindrop_token)

    catalog = CardCatalog(
        audible_library_file=args.audible_library_file,
        kindle_library_file=args.kindle_library_file,
        gbooks_volumes_file=args.gbooks_volumes_file,
        librofm_library_file=args.librofm_library_file,
        raindrop_highlights_file=args.raindrop_highlights_file,
        combined_library_file=args.combined_library_file,
        audible_slugs_file=args.audible_slugs_file,
        kindle_slugs_file=args.kindle_slugs_file,
        librofm_slugs_file=args.librofm_slugs_file,
        raindrop_slugs_file=args.raindrop_slugs_file,
        isbn2olid_map_file=args.isbn2olid_map_file,
        search2asin_file=args.search2asin_file,
        wikipedia_relevant_file=args.wikipedia_relevant_file,
    )

    # Build slug_roots dict - type-specific roots fall back to default_slug_root
    slug_roots = {
        "default": args.default_slug_root,
        "book": args.book_slug_root or args.default_slug_root,
        "article": args.article_slug_root or args.default_slug_root,
        "podcast": args.podcast_slug_root or args.default_slug_root,
        "video": args.video_slug_root or args.default_slug_root,
        "other": args.default_slug_root,
    }

    # Dispatch
    try:
        if args.subcommand == "populate":
            slug_filter = getattr(args, 'slug', None)
            # Convert empty list to None for consistency
            if slug_filter is not None and len(slug_filter) == 0:
                slug_filter = None

            # If slug filters are provided, validate they all exist
            if slug_filter:
                invalid_slugs = [slug for slug in slug_filter if slug not in catalog.combinedlib.contents]
                if invalid_slugs:
                    print(f"Error: the following slugs were not found in combined library: {', '.join(invalid_slugs)}", file=sys.stderr)
                    return 1
                mlogger.info(f"Populating only slugs: {', '.join(slug_filter)}")

            # Only process libraries if no slug filter (we don't want to re-process everything)
            if not slug_filter:
                process_audible_library(catalog)
                process_kindle_library(catalog)
                process_librofm_library(catalog)

            enrich_combined_library(catalog, google_books_key.get(), slug_filter)
            retrieve_covers(catalog, slug_roots, slug_filter)
            write_index_md_files(catalog, slug_roots, slug_filter)
            if args.individual_bibliographer_json:
                write_bibliographer_json_files(catalog, slug_roots, slug_filter)

        elif args.subcommand == "audible":
            if args.audible_subcommand == "retrieve":
                client = audible_login(args.audible_login_file, audible_auth_password)
                retrieve_audible_library(catalog, client)
            elif args.audible_subcommand == "credentials":
                if args.credentials_subcommand == "encrypt":
                    encrypted = encrypt_credentials(args.source, audible_auth_password)
                    print(encrypted)
                elif args.credentials_subcommand == "decrypt":
                    decrypted = decrypt_credentials(args.source, audible_auth_password)
                    print(decrypted)

        elif args.subcommand == "kindle":
            if args.kindle_subcommand == "ingest":
                ingest_kindle_library(catalog, args.export_json)

        elif args.subcommand == "librofm":
            if args.librofm_subcommand == "retrieve":
                token = librofm_login(args.librofm_username, librofm_password.get())
                result = librofm_retrieve_library(catalog, token)

        elif args.subcommand == "raindrop":
            if args.raindrop_subcommand == "highlights":
                if args.raindrop_highlights_subcommand == "retrieve":
                    token = raindrop_token.get()
                    if not token:
                        print("Error: Raindrop token is required. Set --raindrop-token or --raindrop-token-cmd.", file=sys.stderr)
                        return 1
                    count = raindrop_retrieve_highlights(catalog, token)
                    print(f"Retrieved {count} highlights from Raindrop.io")
                else:
                    raise parser.error("Unknown raindrop highlights subcommand")
            else:
                raise parser.error("Unknown raindrop subcommand")

        elif args.subcommand == "googlebook":
            # We have "requery" subcommand
            if args.googlebook_subcommand == "requery":
                # Overwrite existing data with fresh from the server
                volume_ids = args.volume_ids
                for vid in volume_ids:
                    mlogger.info(f"Forcing re-query of volume ID {vid}")
                    # forcibly re-download
                    google_books_retrieve(catalog=catalog, key=google_books_key.get(), bookid=vid, overwrite=True)
                print("Requery complete.")

        elif args.subcommand == "add":
            if args.add_subcommand == "book":
                add_book(
                    catalog=catalog,
                    title=args.title,
                    authors=args.authors,
                    isbn=args.isbn,
                    purchase_date=args.purchase_date,
                    read_date=args.read_date,
                    slug=args.slug,
                )
            elif args.add_subcommand == "article":
                add_article(
                    catalog=catalog,
                    title=args.title,
                    authors=args.authors,
                    url=args.url,
                    publication=args.publication,
                    purchase_date=args.purchase_date,
                    consumed_date=args.read_date,
                    slug=args.slug,
                )
            elif args.add_subcommand == "podcast":
                add_podcast(
                    catalog=catalog,
                    title=args.title,
                    authors=args.authors,
                    url=args.url,
                    podcast_name=args.podcast_name,
                    episode_number=args.episode_number,
                    purchase_date=args.purchase_date,
                    consumed_date=args.listened_date,
                    slug=args.slug,
                )
            elif args.add_subcommand == "video":
                add_video(
                    catalog=catalog,
                    title=args.title,
                    authors=args.authors,
                    url=args.url,
                    purchase_date=args.purchase_date,
                    consumed_date=args.watched_date,
                    slug=args.slug,
                )

        elif args.subcommand == "amazon":
            # We have "requery" for forced re-scrape
            if args.amazon_subcommand == "requery":
                for st in args.searchterms:
                    mlogger.info(f"Forced requery for Amazon search term: {st}")
                    new_asin = amazon_browser_search_cached(catalog, st, force=True)
                    mlogger.info(f" => found ASIN: {new_asin}")
                print("Amazon requery complete.")

        elif args.subcommand == "cover":
            if args.cover_subcommand == "set":
                # Set a cover image for a book
                book_slug = args.slug
                book_dir = slug_roots["book"] / book_slug
                cover_data = download_cover_from_url(args.url)
                cover_dest = book_dir / cover_data.filename
                with cover_dest.open("wb") as f:
                    f.write(cover_data.image_data)
                print(f"Cover image set for {book_slug}")
            elif args.cover_subcommand == "retrieve":
                # Retrieve cover images for all books that don't have them
                retrieve_covers(catalog, slug_roots)
                print("Cover retrieval complete.")
            elif args.cover_subcommand == "list-missing":
                # List books missing cover images
                missing_covers = []
                for book_dir in slug_roots["book"].iterdir():
                    if book_dir.is_dir():
                        if cover_path(book_dir) is None:
                            missing_covers.append(book_dir.name)
                if missing_covers:
                    print("Books missing cover images:")
                    for slug in sorted(missing_covers):
                        print(f"  {slug}")
                else:
                    print("All books have cover images.")

        elif args.subcommand == "slug":
            if args.slug_subcommand == "show":
                print(slugify(args.title))
            elif args.slug_subcommand == "rename":
                rename_slug(catalog, slug_roots, args.old_slug, args.new_slug)
            elif args.slug_subcommand == "regenerate":
                new_slug = slugify(catalog.combinedlib.contents[args.slug].title)
                if new_slug == args.slug:
                    print(f"Slug for {args.slug} is already {new_slug}")
                    return 0
                if args.interactive:
                    if input(f"Change slug from {args.slug} to {new_slug}? [y/N] ").strip().lower() != "y":
                        return 1
                rename_slug(catalog, slug_roots, args.slug, new_slug)

        elif args.subcommand == "version":
            print(get_version())

        elif args.subcommand == "help-file-paths":
            print_file_paths_help()

        elif args.subcommand == "help-services":
            print_services_help()

        else:
            print("Unknown subcommand", file=sys.stderr)
            return 1

        return 0

    finally:
        catalog.persist()


def wrapped_main():
    sys.exit(exceptional_exception_handler(main, sys.argv[1:]))

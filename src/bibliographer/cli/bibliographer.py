#!/usr/bin/env python3
import argparse
import dataclasses
import pathlib
import sys
import tomllib
from typing import Generic, List, Optional, Type, TypeVar
import logging

from bibliographer.sources.amazon_browser import amazon_browser_search_cached
from bibliographer.sources.audible import audible_login, retrieve_audible_library

from bibliographer import add_console_handler, mlogger
from bibliographer.sources.covers import download_cover_from_url
from bibliographer.enrich import enrich_audible_library, enrich_kindle_library
from bibliographer.sources.googlebooks import google_books_retrieve
from bibliographer.sources.kindle import ingest_kindle_library
from bibliographer.sources.manual import manual_add
from bibliographer.populate import populate_all_sources
from bibliographer.cli.util import AutoDescriptionArgumentParser, exceptional_exception_handler, get_argparse_help_string, idb_excepthook


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
    parser.add_argument("-b", "--bibliographer-data", help="Defaults to ./bibliographer_data")
    parser.add_argument("-s", "--book-slug-root", help="Defaults to ./books")
    parser.add_argument("-a", "--audible-login-file", help="Defaults to ./.bibliographer-audible-auth-INSECURE.json")
    parser.add_argument("-g", "--google-books-key", help="Google Books API key")

    # Take care to add help AND description to each subparser.
    # Help is shown by the parent parser
    # e.g. "bibliographer --help" shows the help string for each subparser;
    # description is shown by the subparser itself
    # e.g. "bibliographer audible --help" shows the description for the audible subparser.

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Populate
    #sp_pop =
    subparsers.add_parser("populate", help="Populate bibliographer.json files")

    # Audible
    sp_audible = subparsers.add_parser("audible", help="Audible operations")
    sp_audible_sub = sp_audible.add_subparsers(dest="audible_subcommand", required=True)
    sp_audible_sub.add_parser("retrieve", help="Retrieve the Audible library")

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

    # Manual subcommand
    sp_manual = subparsers.add_parser("manual", help="Manage manually-entered books")
    sp_manual_sub = sp_manual.add_subparsers(dest="manual_subcommand", required=True)

    # manual add
    sp_ma_add = sp_manual_sub.add_parser("add", help="Add a manually-entered book")
    sp_ma_add.add_argument("--title", help="Book title")
    sp_ma_add.add_argument("--authors", nargs="+", help="Authors (allows multiple)")
    sp_ma_add.add_argument("--isbn", help="ISBN if known")
    sp_ma_add.add_argument("--purchase-date", help="Purchase date if any (YYYY-MM-DD)")
    sp_ma_add.add_argument("--read-date", help="Read date if any (YYYY-MM-DD)")
    sp_ma_add.add_argument("--slug", help="Slug for URL (set to a slugified title by default)")

    # cover subcommand
    sp_cover = subparsers.add_parser("cover", help="Cover operations")
    sp_cover_sub = sp_cover.add_subparsers(dest="cover_subcommand", required=True)
    sp_cover_set = sp_cover_sub.add_parser("set", help="Set a cover image")
    sp_cover_set.add_argument("slug", help="Book slug")
    sp_cover_set.add_argument("url", help="URL for a cover image")

    return parser


def get_help_string() -> str:
    """Get a string containing program help"""
    return get_argparse_help_string("bibliographer", makeparser())


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
            value = f"\"{value}\""
        elif isinstance(value, bool):
            # Make this look right for TOML
            value = str(value).lower()
        result += f"{param.key} = {value}\n"
    for param in ConfigurationParameterSet.paths():
        result += f"{param.key} = \"{param.default}\"\n"
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


T = TypeVar('T')


@dataclasses.dataclass
class ConfigurationParameter(Generic[T]):
    """A generic class for parameters set in the config file"""
    key: str
    vtype: Type[T]
    default: T


class ConfigurationParameterSet:
    """All parameters set in the config file5"""

    @staticmethod
    def scalars() -> List[ConfigurationParameter]:
        """Scalar parameters are set directly"""
        return [
            ConfigurationParameter("debug", bool, False),
            ConfigurationParameter("verbose", bool, False),
            ConfigurationParameter("google_books_key", str, ""),
        ]

    @staticmethod
    def paths() -> List[ConfigurationParameter]:
        """Path parameters are handled specially

        Relative paths set on the command-line are resolved relative to $PWD,
        while relative paths set in the config file are resolved relative to the config file's directory.
        """
        return [
            ConfigurationParameter("book_slug_root", pathlib.Path, pathlib.Path("./books")),
            ConfigurationParameter("audible_login_file", pathlib.Path, pathlib.Path("./.bibliographer-audible-auth-INSECURE.json")),
            ConfigurationParameter("bibliographer_data", pathlib.Path, pathlib.Path("./bibliographer_data")),
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
        # Set the path to the default value first
        path = resolve_path_if_relative(param.default, pathlib.Path.cwd())
        clival = getattr(parsed, param.key)
        if clival:
            # This is a command-line argument, so resolve it relative to $PWD
            path = resolve_path_if_relative(getattr(parsed, param.key), pathlib.Path.cwd())
        elif parsed.config and param.key in config_data:
            # The value was set in the config file, so resolve it relative to the config file's directory
            path = resolve_path_if_relative(config_data[param.key], parsed.config.parent)
        setattr(parsed, param.key, path)

    return parsed


###############################################################################
# Main Entry
###############################################################################


def main(arguments: list[str]) -> int:
    args = parseargs(sys.argv[1:])

    log_level = logging.INFO
    if args.debug:
        sys.excepthook = idb_excepthook
    if args.verbose:
        log_level = logging.DEBUG
    add_console_handler(log_level)

    google_books_key = args.google_books_key or ""

    # Directory structure: we store API cache in "bibliographer_data/apicache" and user mappings in "bibliographer_data/usermappings"
    apicache = args.bibliographer_data / "apicache"
    usermappings = args.bibliographer_data / "usermappings"
    apicache.mkdir(parents=True, exist_ok=True)
    usermappings.mkdir(parents=True, exist_ok=True)

    # apicache files
    audible_library_metadata = apicache / "audible_library_metadata.json"
    kindle_library_metadata = apicache / "kindle_library_metadata.json"
    gbooks_volumes = apicache / "gbooks_volumes.json"

    # usermappings files
    asin2gbv_map_path = usermappings / "asin2gbv_map.json"
    isbn2olid_map_path = usermappings / "isbn2olid_map.json"
    search2asin_map_path = usermappings / "search2asin.json"
    wikipedia_cache = usermappings / "wikipedia_relevant.json"

    audible_library_metadata_enriched = usermappings / "audible_library_metadata_enriched.json"
    kindle_library_enriched = usermappings / "kindle_library_metadata_enriched.json"

    # manual file
    manual_file = usermappings / "manual.json"

    # Dispatch
    if args.subcommand == "populate":
        populate_all_sources(
            audible_library_metadata=audible_library_metadata,
            audible_library_metadata_enriched=audible_library_metadata_enriched,
            kindle_library_metadata=kindle_library_metadata,
            kindle_library_enriched=kindle_library_enriched,
            manual_file=manual_file,
            asin2gbv_map=asin2gbv_map_path,
            gbooks_volumes=gbooks_volumes,
            isbn2olid_map=isbn2olid_map_path,
            search2asin_map=search2asin_map_path,
            book_slug_root=args.book_slug_root,
            wikipedia_cache=wikipedia_cache,
            google_books_key=google_books_key,
        )

    elif args.subcommand == "audible":
        client = audible_login(args.audible_login_file)
        if args.audible_subcommand == "retrieve":
            retrieve_audible_library(client, audible_library_metadata)
            enrich_audible_library(
                audible_library_metadata=audible_library_metadata,
                audible_library_metadata_enriched=audible_library_metadata_enriched,
                search2asin_map_path=search2asin_map_path,
                google_books_key=google_books_key,
                gbooks_volumes=gbooks_volumes,
                asin2gbv_map_path=asin2gbv_map_path,
                isbn2olid_map_path=isbn2olid_map_path,
            )

    elif args.subcommand == "kindle":
        if args.kindle_subcommand == "ingest":
            ingest_kindle_library(kindle_library_metadata, args.export_json)
            enrich_kindle_library(
                kindle_library_metadata=kindle_library_metadata,
                kindle_library_enriched=kindle_library_enriched,
                search2asin_map_path=search2asin_map_path,
                google_books_key=google_books_key,
                gbooks_volumes=gbooks_volumes,
                asin2gbv_map_path=asin2gbv_map_path,
                isbn2olid_map_path=isbn2olid_map_path,
            )

    elif args.subcommand == "googlebook":
        # We have "requery" subcommand
        if args.googlebook_subcommand == "requery":
            # Overwrite existing data with fresh from the server
            volume_ids = args.volume_ids
            for vid in volume_ids:
                mlogger.info(f"Forcing re-query of volume ID {vid}")
                # forcibly re-download
                google_books_retrieve(key=google_books_key, gbooks_volumes=gbooks_volumes, bookid=vid, overwrite=True)
            print("Requery complete.")

    elif args.subcommand == "manual":
        if args.manual_subcommand == "add":
            manual_add(
                manual_file=manual_file,
                title=args.title,
                authors=args.authors,
                isbn=args.isbn,
                purchase_date=args.purchase_date,
                read_date=args.read_date,
                slug=args.slug,
            )

    elif args.subcommand == "amazon":
        # We have "requery" for forced re-scrape
        if args.amazon_subcommand == "requery":
            for st in args.searchterms:
                mlogger.info(f"Forced requery for Amazon search term: {st}")
                new_asin = amazon_browser_search_cached(search2asin_map_path, st, force=True)
                mlogger.info(f" => found ASIN: {new_asin}")
            print("Amazon requery complete.")

    elif args.subcommand == "cover":
        if args.cover_subcommand == "set":
            # Set a cover image for a book
            book_slug = args.slug
            book_dir = args.book_slug_root / book_slug
            cover_data = download_cover_from_url(args.url)
            cover_dest = book_dir / cover_data.filename
            with cover_dest.open("wb") as f:
                f.write(cover_data.image_data)
            print(f"Cover image set for {book_slug}")

    else:
        print("Unknown subcommand", file=sys.stderr)
        return 1

    return 0


def wrapped_main():
    sys.exit(exceptional_exception_handler(main, sys.argv[1:]))

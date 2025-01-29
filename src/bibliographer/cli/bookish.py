#!/usr/bin/env python3
import argparse
import pathlib
import sys
import tomllib
from typing import Optional, List
import logging

from bibliographer.bookish.amazon_browser import amazon_browser_search_cached
from bibliographer.bookish.audible import audible_login, retrieve_audible_library

from bibliographer import add_console_handler, mlogger
from bibliographer.bookish.covers import download_cover_from_url
from bibliographer.bookish.enrich import enrich_audible_library, enrich_kindle_library
from bibliographer.bookish.googlebooks import google_books_retrieve
from bibliographer.bookish.kindle import ingest_kindle_library
from bibliographer.bookish.manual import manual_add
from bibliographer.bookish.populate import populate_all_sources
from bibliographer.cli.util import exceptional_exception_handler, idb_excepthook


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


def parseargs(arguments: List[str]):
    """Parse command-line arguments

    NOTE: Defaults in this function will override defaults in the TOML config file.
    """
    parser = argparse.ArgumentParser(
        description="Manage Audible/Kindle libraries, enrich them, and populate local book repos."
    )
    parser.add_argument(
        "-D",
        "--debug",
        action="store_true",
        help="Drop into an interactive debugger on unhandled exceptions.",
    )
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        help="Path to TOML config file, defaulting to a file called .bookish.toml in the repo root",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging of API calls.")
    parser.add_argument(
        "--repo-root",
        default=find_repo_root(),
        type=pathlib.Path,
        help="Defaults to the ancestor directory containing a .git folder.",
    )
    parser.add_argument("--book-slug-root", help="Defaults to {repo-root}/content/books")
    parser.add_argument("--google-books-key", help="Google Books API key")

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Populate
    sp_pop = subparsers.add_parser("populate", help="Populate bookish.json files")

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

    parsed = parser.parse_args(arguments)

    if not parsed.config:
        parsed.config = parsed.repo_root / ".bookish.toml"

    if parsed.config.exists():
        with open(parsed.config, "rb") as f:
            config_data = tomllib.load(f)
        if parsed.debug is None:
            parsed.debug = config_data.get("debug", False)
        if parsed.verbose is None:
            parsed.verbose = config_data.get("verbose", False)
        if parsed.book_slug_root is None:
            parsed.book_slug_root = config_data.get("book_slug_root")
        if parsed.google_books_key is None:
            parsed.google_books_key = config_data.get("google_books_key")

    return parsed


###############################################################################
# Main Entry
###############################################################################


def main():
    args = parseargs(sys.argv[1:])

    log_level = logging.INFO
    if args.debug:
        sys.excepthook = idb_excepthook
    if args.verbose:
        log_level = logging.DEBUG
    add_console_handler(log_level)

    google_books_key = args.google_books_key or ""

    # Book slug root
    if args.book_slug_root:
        book_slug_root = pathlib.Path(args.book_slug_root)
    else:
        book_slug_root = args.repo_root / "content" / "books"

    # Directory structure: we store API cache in "bookish_data/apicache" and user mappings in "bookish_data/usermappings"
    bookish_data = args.repo_root / "bookish_data"
    apicache = bookish_data / "apicache"
    usermappings = bookish_data / "usermappings"
    apicache.mkdir(parents=True, exist_ok=True)
    usermappings.mkdir(parents=True, exist_ok=True)

    # Audible uses .audible-auth-INSECURE.json in repo root
    audible_login_file = args.repo_root / ".audible-auth-INSECURE.json"

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
            book_slug_root=book_slug_root,
            wikipedia_cache=wikipedia_cache,
            google_books_key=google_books_key,
        )

    elif args.subcommand == "audible":
        client = audible_login(audible_login_file)
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
            book_dir = book_slug_root / book_slug
            cover_data = download_cover_from_url(args.url)
            cover_dest = book_dir / cover_data.filename
            with cover_dest.open("wb") as f:
                f.write(cover_data.image_data)
            print(f"Cover image set for {book_slug}")

    else:
        print("Unknown subcommand", file=sys.stderr)
        sys.exit(1)


def wrapped_main():
    sys.exit(exceptional_exception_handler(main))

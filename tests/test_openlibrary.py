"""Test OpenLibrary integration."""

import json
import pathlib
import tempfile
from unittest.mock import patch

from bibliographer.cardcatalog import CardCatalog, CombinedCatalogBook
from bibliographer.enrich import enrich_combined_library
from bibliographer.sources.openlibrary import isbn2olid, normalize_olid


def test_isbn2olid_success_and_caching():
    """Test successful OLID lookup with real API data, prefix stripping, and cache reuse."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = pathlib.Path(tmpdir)
        catalog = CardCatalog.from_data_root(data_root)

        # Load real OpenLibrary API response
        test_data_path = pathlib.Path(__file__).parent / "data" / "openlibrary" / "valid_isbn_9780316769174.json"
        with open(test_data_path) as f:
            api_response = json.load(f)

        isbn = "9780316769174"
        book_data = api_response[f"ISBN:{isbn}"]

        with patch("bibliographer.sources.openlibrary._fetch_openlibrary_api") as mock_fetch:
            mock_fetch.return_value = book_data

            # First call - should hit API and strip /books/ prefix
            result = isbn2olid(catalog, isbn)
            assert result == "OL18290341M", f"Expected 'OL18290341M', got '{result}'"
            assert mock_fetch.call_count == 1, "Should call API once"

            # Second call - should use cache, no API call
            result2 = isbn2olid(catalog, isbn)
            assert result2 == "OL18290341M", f"Expected cached 'OL18290341M', got '{result2}'"
            assert mock_fetch.call_count == 1, "Should NOT call API again (cached)"


def test_isbn2olid_not_found_caches_none():
    """Test that missing ISBNs cache None to prevent repeated failed queries.

    Note: Many invalid-looking ISBNs like "0000000000" actually return data on OpenLibrary.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = pathlib.Path(tmpdir)
        catalog = CardCatalog.from_data_root(data_root)

        # Load real OpenLibrary API response for not found case (empty object)
        test_data_path = pathlib.Path(__file__).parent / "data" / "openlibrary" / "not_found_isbn.json"
        with open(test_data_path) as f:
            api_response = json.load(f)

        isbn = "00"  # ISBN "00" returns {} from OpenLibrary
        book_data = api_response.get(f"ISBN:{isbn}")  # Returns None for empty {}

        with patch("bibliographer.sources.openlibrary._fetch_openlibrary_api") as mock_fetch:
            mock_fetch.return_value = book_data

            # First call - API returns None
            result = isbn2olid(catalog, isbn)
            assert result is None, f"Expected None for missing ISBN, got '{result}'"
            assert mock_fetch.call_count == 1, "Should call API once"

            # Second call - should use cached None, no API call
            result2 = isbn2olid(catalog, isbn)
            assert result2 is None, f"Expected cached None, got '{result2}'"
            assert mock_fetch.call_count == 1, "Should NOT call API again (None cached)"


def test_normalize_olid_strips_prefixes():
    """Test that normalize_olid strips all common OpenLibrary prefixes."""
    # Books/editions prefix
    assert normalize_olid("/books/OL12345M") == "OL12345M"
    assert normalize_olid("/editions/OL12345M") == "/editions/OL12345M"  # Not implemented yet

    # Works prefix
    assert normalize_olid("/works/OL67890W") == "OL67890W"

    # Authors prefix
    assert normalize_olid("/authors/OL99999A") == "OL99999A"


def test_normalize_olid_handles_already_normalized():
    """Test that normalize_olid leaves already-normalized IDs unchanged."""
    assert normalize_olid("OL12345M") == "OL12345M"
    assert normalize_olid("OL67890W") == "OL67890W"
    assert normalize_olid("OL99999A") == "OL99999A"


def test_normalize_olid_handles_edge_cases():
    """Test that normalize_olid handles None and empty strings."""
    assert normalize_olid(None) is None
    assert normalize_olid("") is None
    assert normalize_olid("   ") == "   "  # Whitespace is returned as-is


def test_enrich_normalizes_existing_olids():
    """Test that enrichment normalizes existing OLIDs in combined library."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = pathlib.Path(tmpdir)
        catalog = CardCatalog.from_data_root(data_root)

        # Create a book with a prefixed OLID (simulating manual edit or old data)
        book = CombinedCatalogBook(
            title="Test Book",
            authors=["Test Author"],
            slug="test-book",
            openlibrary_id="/books/OL12345M",  # Prefixed OLID
        )
        catalog.combinedlib.contents["test-book"] = book

        # Run enrichment with empty google_books_key (we don't need Google Books for this test)
        enrich_combined_library(catalog, google_books_key="", slug_filter=["test-book"])

        # Verify OLID was normalized
        assert book.openlibrary_id == "OL12345M", f"Expected normalized 'OL12345M', got '{book.openlibrary_id}'"


def test_enrich_normalizes_work_ids():
    """Test that enrichment normalizes work IDs from OpenLibrary."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = pathlib.Path(tmpdir)
        catalog = CardCatalog.from_data_root(data_root)

        # Create a book with a work ID (another possible prefix)
        book = CombinedCatalogBook(
            title="Test Book",
            authors=["Test Author"],
            slug="test-work",
            openlibrary_id="/works/OL67890W",  # Work ID with prefix
        )
        catalog.combinedlib.contents["test-work"] = book

        # Run enrichment
        enrich_combined_library(catalog, google_books_key="", slug_filter=["test-work"])

        # Verify work ID was normalized
        assert book.openlibrary_id == "OL67890W", f"Expected normalized 'OL67890W', got '{book.openlibrary_id}'"

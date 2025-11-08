"""Test OpenLibrary integration."""

import json
import pathlib
import tempfile
from unittest.mock import patch

from bibliographer.cardcatalog import CardCatalog
from bibliographer.sources.openlibrary import isbn2olid


def test_isbn2olid_success_and_caching():
    """Test successful OLID lookup with real API data, prefix stripping, and cache reuse."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = pathlib.Path(tmpdir)
        catalog = CardCatalog(data_root)

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
        catalog = CardCatalog(data_root)

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

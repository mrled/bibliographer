"""Test Kindle library ingestion."""

import pathlib
import tempfile

from bibliographer.cardcatalog import CardCatalog
from bibliographer.sources.kindle import ingest_kindle_library, process_kindle_library


def test_kindle_library_ingest():
    """Test that we can ingest a Kindle library and process one book correctly."""
    # Setup: Create a temporary directory for test data
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = pathlib.Path(tmpdir)
        catalog = CardCatalog(data_root)

        # Get the path to the test data
        test_data_path = pathlib.Path(__file__).parent / "data" / "kindle-library.json"

        # Ingest the Kindle library
        ingest_kindle_library(catalog, test_data_path)

        # Process the Kindle library
        process_kindle_library(catalog)

        # Verify that at least one book was processed
        assert len(catalog.combinedlib.contents) > 0, "No books were processed"

        # Test a specific book - using the first book from the JSON
        # ASIN: B004GKMP3U - "How and Why I Taught My Toddler to Read" by Larry Sanger
        expected_asin = "B004GKMP3U"
        expected_title = "How and Why I Taught My Toddler to Read"
        expected_authors = ["Sanger, Larry"]
        expected_cover_url = "https://m.media-amazon.com/images/I/41nbucEm+dL._SY400_.jpg"

        # Find the book by its kindle_asin
        book = None
        for slug, b in catalog.combinedlib.contents.items():
            if b.kindle_asin == expected_asin:
                book = b
                break

        # Verify the book was found and has correct data
        assert book is not None, f"Book with ASIN {expected_asin} not found"
        assert book.title == expected_title, f"Expected title '{expected_title}', got '{book.title}'"
        assert book.authors == expected_authors, f"Expected authors {expected_authors}, got {book.authors}"
        assert book.kindle_asin == expected_asin, f"Expected ASIN {expected_asin}, got {book.kindle_asin}"
        assert book.kindle_cover_url == expected_cover_url, f"Expected cover URL {expected_cover_url}, got {book.kindle_cover_url}"
        assert book.slug is not None, "Book should have a slug"

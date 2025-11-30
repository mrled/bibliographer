"""Tests for the enrich module and work type handling."""

import json
import pathlib
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from bibliographer.cardcatalog import (
    CardCatalog,
    CatalogArticle,
    CatalogBook,
    CatalogPodcastEpisode,
    CatalogVideo,
)
from bibliographer.enrich import (
    enrich_combined_library,
    retrieve_covers,
    write_bibliographer_json_files,
    write_index_md_files,
)


@pytest.fixture
def temp_catalog():
    """Create a temporary CardCatalog for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = pathlib.Path(tmpdir)
        catalog = CardCatalog.from_data_root(data_root)
        yield catalog


class TestEnrichCombinedLibrary:
    """Tests for enrich_combined_library function."""

    def test_book_enrichment_runs_for_books(self, temp_catalog):
        """Book-specific enrichment should run for CatalogBook entries."""
        book = CatalogBook(title="Test Book", authors=["Author"], slug="test-book")
        temp_catalog.combinedlib.contents["test-book"] = book

        with patch("bibliographer.enrich.google_books_search") as mock_gbooks:
            with patch("bibliographer.enrich.wikipedia_relevant_pages") as mock_wiki:
                mock_gbooks.return_value = {"bookid": "vol123"}
                mock_wiki.return_value = {"title": "https://wiki.example.com"}

                enrich_combined_library(temp_catalog, "fake-api-key")

                # google_books_search should be called for books
                mock_gbooks.assert_called_once()
                # Wikipedia should also be called
                mock_wiki.assert_called_once()

    def test_book_enrichment_skipped_for_articles(self, temp_catalog):
        """Book-specific enrichment should be skipped for CatalogArticle entries."""
        article = CatalogArticle(
            title="Test Article",
            authors=["Author"],
            slug="test-article",
            url="https://example.com",
        )
        temp_catalog.combinedlib.contents["test-article"] = article

        with patch("bibliographer.enrich.google_books_search") as mock_gbooks:
            with patch("bibliographer.enrich.wikipedia_relevant_pages") as mock_wiki:
                mock_wiki.return_value = {"title": "https://wiki.example.com"}

                enrich_combined_library(temp_catalog, "fake-api-key")

                # google_books_search should NOT be called for articles
                mock_gbooks.assert_not_called()
                # But Wikipedia should still be called
                mock_wiki.assert_called_once()

    def test_book_enrichment_skipped_for_podcasts(self, temp_catalog):
        """Book-specific enrichment should be skipped for CatalogPodcastEpisode entries."""
        podcast = CatalogPodcastEpisode(
            title="Test Episode",
            authors=["Host"],
            slug="test-episode",
            podcast_name="Test Podcast",
        )
        temp_catalog.combinedlib.contents["test-episode"] = podcast

        with patch("bibliographer.enrich.google_books_search") as mock_gbooks:
            with patch("bibliographer.enrich.wikipedia_relevant_pages") as mock_wiki:
                mock_wiki.return_value = {"title": "https://wiki.example.com"}

                enrich_combined_library(temp_catalog, "fake-api-key")

                mock_gbooks.assert_not_called()
                mock_wiki.assert_called_once()

    def test_book_enrichment_skipped_for_videos(self, temp_catalog):
        """Book-specific enrichment should be skipped for CatalogVideo entries."""
        video = CatalogVideo(
            title="Test Video",
            authors=["Creator"],
            slug="test-video",
            url="https://youtube.com/watch?v=123",
        )
        temp_catalog.combinedlib.contents["test-video"] = video

        with patch("bibliographer.enrich.google_books_search") as mock_gbooks:
            with patch("bibliographer.enrich.wikipedia_relevant_pages") as mock_wiki:
                mock_wiki.return_value = {"title": "https://wiki.example.com"}

                enrich_combined_library(temp_catalog, "fake-api-key")

                mock_gbooks.assert_not_called()
                mock_wiki.assert_called_once()

    def test_mixed_work_types_enrichment(self, temp_catalog):
        """Test enrichment with a mix of work types."""
        book = CatalogBook(title="Book", authors=["Author"], slug="book")
        article = CatalogArticle(title="Article", authors=["Writer"], slug="article")
        podcast = CatalogPodcastEpisode(title="Episode", authors=["Host"], slug="podcast")

        temp_catalog.combinedlib.contents["book"] = book
        temp_catalog.combinedlib.contents["article"] = article
        temp_catalog.combinedlib.contents["podcast"] = podcast

        with patch("bibliographer.enrich.google_books_search") as mock_gbooks:
            with patch("bibliographer.enrich.wikipedia_relevant_pages") as mock_wiki:
                mock_gbooks.return_value = {"bookid": "vol123"}
                mock_wiki.return_value = {"title": "https://wiki.example.com"}

                enrich_combined_library(temp_catalog, "fake-api-key")

                # google_books_search should be called only once (for the book)
                assert mock_gbooks.call_count == 1
                # Wikipedia should be called 3 times (for all work types)
                assert mock_wiki.call_count == 3


class TestRetrieveCovers:
    """Tests for retrieve_covers function."""

    def test_covers_retrieved_for_books(self, temp_catalog):
        """Cover retrieval should run for CatalogBook entries."""
        with tempfile.TemporaryDirectory() as cover_root:
            cover_root_path = pathlib.Path(cover_root)
            book = CatalogBook(
                title="Test Book",
                slug="test-book",
                gbooks_volid="vol123",
            )
            temp_catalog.combinedlib.contents["test-book"] = book

            with patch("bibliographer.enrich.lookup_cover") as mock_cover:
                retrieve_covers(temp_catalog, cover_root_path)
                mock_cover.assert_called_once()

    def test_covers_skipped_for_articles(self, temp_catalog):
        """Cover retrieval should be skipped for CatalogArticle entries."""
        with tempfile.TemporaryDirectory() as cover_root:
            cover_root_path = pathlib.Path(cover_root)
            article = CatalogArticle(
                title="Test Article",
                slug="test-article",
                url="https://example.com",
            )
            temp_catalog.combinedlib.contents["test-article"] = article

            with patch("bibliographer.enrich.lookup_cover") as mock_cover:
                retrieve_covers(temp_catalog, cover_root_path)
                mock_cover.assert_not_called()

    def test_covers_skipped_for_podcasts(self, temp_catalog):
        """Cover retrieval should be skipped for CatalogPodcastEpisode entries."""
        with tempfile.TemporaryDirectory() as cover_root:
            cover_root_path = pathlib.Path(cover_root)
            podcast = CatalogPodcastEpisode(
                title="Test Episode",
                slug="test-episode",
                podcast_name="Test Podcast",
            )
            temp_catalog.combinedlib.contents["test-episode"] = podcast

            with patch("bibliographer.enrich.lookup_cover") as mock_cover:
                retrieve_covers(temp_catalog, cover_root_path)
                mock_cover.assert_not_called()

    def test_covers_skipped_for_videos(self, temp_catalog):
        """Cover retrieval should be skipped for CatalogVideo entries."""
        with tempfile.TemporaryDirectory() as cover_root:
            cover_root_path = pathlib.Path(cover_root)
            video = CatalogVideo(
                title="Test Video",
                slug="test-video",
                url="https://youtube.com/watch?v=123",
            )
            temp_catalog.combinedlib.contents["test-video"] = video

            with patch("bibliographer.enrich.lookup_cover") as mock_cover:
                retrieve_covers(temp_catalog, cover_root_path)
                mock_cover.assert_not_called()


class TestWriteIndexMdFiles:
    """Tests for write_index_md_files function."""

    def test_index_md_created_for_book(self, temp_catalog):
        """index.md should be created for CatalogBook entries."""
        with tempfile.TemporaryDirectory() as content_root:
            content_root_path = pathlib.Path(content_root)
            book = CatalogBook(title="Test Book", slug="test-book")
            temp_catalog.combinedlib.contents["test-book"] = book

            write_index_md_files(temp_catalog, content_root_path)

            index_path = content_root_path / "test-book" / "index.md"
            assert index_path.exists()
            content = index_path.read_text()
            assert 'title: "Test Book"' in content

    def test_index_md_created_for_article(self, temp_catalog):
        """index.md should be created for CatalogArticle entries."""
        with tempfile.TemporaryDirectory() as content_root:
            content_root_path = pathlib.Path(content_root)
            article = CatalogArticle(title="Test Article", slug="test-article")
            temp_catalog.combinedlib.contents["test-article"] = article

            write_index_md_files(temp_catalog, content_root_path)

            index_path = content_root_path / "test-article" / "index.md"
            assert index_path.exists()
            content = index_path.read_text()
            assert 'title: "Test Article"' in content

    def test_index_md_created_for_podcast(self, temp_catalog):
        """index.md should be created for CatalogPodcastEpisode entries."""
        with tempfile.TemporaryDirectory() as content_root:
            content_root_path = pathlib.Path(content_root)
            podcast = CatalogPodcastEpisode(
                title="Test Episode",
                slug="test-episode",
                podcast_name="Test Podcast",
            )
            temp_catalog.combinedlib.contents["test-episode"] = podcast

            write_index_md_files(temp_catalog, content_root_path)

            index_path = content_root_path / "test-episode" / "index.md"
            assert index_path.exists()
            content = index_path.read_text()
            assert 'title: "Test Episode"' in content

    def test_index_md_created_for_video(self, temp_catalog):
        """index.md should be created for CatalogVideo entries."""
        with tempfile.TemporaryDirectory() as content_root:
            content_root_path = pathlib.Path(content_root)
            video = CatalogVideo(title="Test Video", slug="test-video")
            temp_catalog.combinedlib.contents["test-video"] = video

            write_index_md_files(temp_catalog, content_root_path)

            index_path = content_root_path / "test-video" / "index.md"
            assert index_path.exists()
            content = index_path.read_text()
            assert 'title: "Test Video"' in content


class TestWriteBibliographerJsonFiles:
    """Tests for write_bibliographer_json_files function."""

    def test_json_includes_work_type_for_book(self, temp_catalog):
        """bibliographer.json should include work_type for books."""
        with tempfile.TemporaryDirectory() as content_root:
            content_root_path = pathlib.Path(content_root)
            book = CatalogBook(title="Test Book", slug="test-book", isbn="1234567890")
            temp_catalog.combinedlib.contents["test-book"] = book

            write_bibliographer_json_files(temp_catalog, content_root_path)

            json_path = content_root_path / "test-book" / "bibliographer.json"
            assert json_path.exists()
            data = json.loads(json_path.read_text())
            assert data["work_type"] == "book"
            assert data["isbn"] == "1234567890"

    def test_json_includes_work_type_for_article(self, temp_catalog):
        """bibliographer.json should include work_type for articles."""
        with tempfile.TemporaryDirectory() as content_root:
            content_root_path = pathlib.Path(content_root)
            article = CatalogArticle(
                title="Test Article",
                slug="test-article",
                url="https://example.com",
                publication="Tech Blog",
            )
            temp_catalog.combinedlib.contents["test-article"] = article

            write_bibliographer_json_files(temp_catalog, content_root_path)

            json_path = content_root_path / "test-article" / "bibliographer.json"
            assert json_path.exists()
            data = json.loads(json_path.read_text())
            assert data["work_type"] == "article"
            assert data["url"] == "https://example.com"
            assert data["publication"] == "Tech Blog"

    def test_json_includes_work_type_for_podcast(self, temp_catalog):
        """bibliographer.json should include work_type for podcasts."""
        with tempfile.TemporaryDirectory() as content_root:
            content_root_path = pathlib.Path(content_root)
            podcast = CatalogPodcastEpisode(
                title="Test Episode",
                slug="test-episode",
                podcast_name="Test Podcast",
                episode_number=42,
            )
            temp_catalog.combinedlib.contents["test-episode"] = podcast

            write_bibliographer_json_files(temp_catalog, content_root_path)

            json_path = content_root_path / "test-episode" / "bibliographer.json"
            assert json_path.exists()
            data = json.loads(json_path.read_text())
            assert data["work_type"] == "podcast"
            assert data["podcast_name"] == "Test Podcast"
            assert data["episode_number"] == 42

    def test_json_includes_work_type_for_video(self, temp_catalog):
        """bibliographer.json should include work_type for videos."""
        with tempfile.TemporaryDirectory() as content_root:
            content_root_path = pathlib.Path(content_root)
            video = CatalogVideo(
                title="Test Video",
                slug="test-video",
                url="https://youtube.com/watch?v=123",
            )
            temp_catalog.combinedlib.contents["test-video"] = video

            write_bibliographer_json_files(temp_catalog, content_root_path)

            json_path = content_root_path / "test-video" / "bibliographer.json"
            assert json_path.exists()
            data = json.loads(json_path.read_text())
            assert data["work_type"] == "video"
            assert data["url"] == "https://youtube.com/watch?v=123"

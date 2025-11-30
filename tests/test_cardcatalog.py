"""Tests for the cardcatalog module and work type hierarchy."""

import pytest

from bibliographer.cardcatalog import (
    CatalogArticle,
    CatalogBook,
    CatalogPodcastEpisode,
    CatalogVideo,
    CombinedCatalogBook,
    CombinedCatalogWork,
    WorkType,
)


class TestWorkTypeHierarchy:
    """Tests for the work type class hierarchy."""

    def test_work_type_literal(self):
        """WorkType should include all expected types."""
        # This is a type-level test; we verify the values work at runtime
        valid_types: list[WorkType] = ["book", "article", "podcast", "video", "other"]
        for wt in valid_types:
            work = CombinedCatalogWork(work_type=wt)
            assert work.work_type == wt

    def test_catalog_book_default_work_type(self):
        """CatalogBook should have work_type='book' by default."""
        book = CatalogBook()
        assert book.work_type == "book"

    def test_catalog_article_default_work_type(self):
        """CatalogArticle should have work_type='article' by default."""
        article = CatalogArticle()
        assert article.work_type == "article"

    def test_catalog_podcast_default_work_type(self):
        """CatalogPodcastEpisode should have work_type='podcast' by default."""
        podcast = CatalogPodcastEpisode()
        assert podcast.work_type == "podcast"

    def test_catalog_video_default_work_type(self):
        """CatalogVideo should have work_type='video' by default."""
        video = CatalogVideo()
        assert video.work_type == "video"

    def test_combined_catalog_work_default_work_type(self):
        """CombinedCatalogWork should have work_type='other' by default."""
        work = CombinedCatalogWork()
        assert work.work_type == "other"


class TestFromDictFactory:
    """Tests for the from_dict factory method."""

    def test_from_dict_returns_book_for_book_type(self):
        """from_dict should return CatalogBook for work_type='book'."""
        data = {"title": "Test Book", "work_type": "book", "isbn": "1234567890"}
        result = CombinedCatalogWork.from_dict(data)
        assert isinstance(result, CatalogBook)
        assert result.title == "Test Book"
        assert result.isbn == "1234567890"

    def test_from_dict_returns_book_for_missing_work_type(self):
        """from_dict should default to CatalogBook when work_type is missing (backward compat)."""
        data = {"title": "Legacy Book", "isbn": "1234567890"}
        result = CombinedCatalogWork.from_dict(data)
        assert isinstance(result, CatalogBook)
        assert result.work_type == "book"
        assert result.title == "Legacy Book"

    def test_from_dict_returns_article_for_article_type(self):
        """from_dict should return CatalogArticle for work_type='article'."""
        data = {"title": "Test Article", "work_type": "article", "url": "https://example.com"}
        result = CombinedCatalogWork.from_dict(data)
        assert isinstance(result, CatalogArticle)
        assert result.title == "Test Article"
        assert result.url == "https://example.com"

    def test_from_dict_returns_podcast_for_podcast_type(self):
        """from_dict should return CatalogPodcastEpisode for work_type='podcast'."""
        data = {"title": "Episode 1", "work_type": "podcast", "podcast_name": "My Podcast"}
        result = CombinedCatalogWork.from_dict(data)
        assert isinstance(result, CatalogPodcastEpisode)
        assert result.title == "Episode 1"
        assert result.podcast_name == "My Podcast"

    def test_from_dict_returns_video_for_video_type(self):
        """from_dict should return CatalogVideo for work_type='video'."""
        data = {"title": "My Video", "work_type": "video", "url": "https://youtube.com/watch?v=123"}
        result = CombinedCatalogWork.from_dict(data)
        assert isinstance(result, CatalogVideo)
        assert result.title == "My Video"
        assert result.url == "https://youtube.com/watch?v=123"

    def test_from_dict_returns_base_for_other_type(self):
        """from_dict should return CombinedCatalogWork for work_type='other'."""
        data = {"title": "Some Work", "work_type": "other"}
        result = CombinedCatalogWork.from_dict(data)
        assert type(result) is CombinedCatalogWork
        assert result.title == "Some Work"

    def test_from_dict_filters_unknown_fields(self):
        """from_dict should filter out fields that don't exist on the target class."""
        data = {"title": "Test", "work_type": "article", "unknown_field": "value", "isbn": "123"}
        result = CombinedCatalogWork.from_dict(data)
        assert isinstance(result, CatalogArticle)
        assert not hasattr(result, "unknown_field")
        # isbn is a book field, not article field
        assert not hasattr(result, "isbn") or result.isbn is None

    def test_from_dict_on_subclass_creates_that_type(self):
        """Calling from_dict on a subclass should create that specific type."""
        data = {"title": "Direct Book", "isbn": "999"}
        result = CatalogBook.from_dict(data)
        assert isinstance(result, CatalogBook)
        assert result.title == "Direct Book"
        assert result.isbn == "999"


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing data."""

    def test_combined_catalog_book_is_catalog_book(self):
        """CombinedCatalogBook should be an alias for CatalogBook."""
        assert CombinedCatalogBook is CatalogBook

    def test_read_date_alias_getter(self):
        """read_date property should return consumed_date value."""
        book = CatalogBook(consumed_date="2024-01-15")
        assert book.read_date == "2024-01-15"

    def test_read_date_alias_setter(self):
        """Setting read_date should set consumed_date."""
        book = CatalogBook()
        book.read_date = "2024-01-15"
        assert book.consumed_date == "2024-01-15"

    def test_from_dict_migrates_read_date_to_consumed_date(self):
        """from_dict should migrate read_date to consumed_date."""
        data = {"title": "Old Book", "read_date": "2024-01-15"}
        result = CatalogBook.from_dict(data)
        assert result.consumed_date == "2024-01-15"

    def test_from_dict_prefers_consumed_date_over_read_date(self):
        """If both read_date and consumed_date present, prefer consumed_date."""
        data = {"title": "Book", "read_date": "2024-01-01", "consumed_date": "2024-06-15"}
        result = CatalogBook.from_dict(data)
        assert result.consumed_date == "2024-06-15"


class TestMerge:
    """Tests for the merge functionality."""

    def test_catalog_book_merge_fills_empty_fields(self):
        """merge() should fill empty fields from another book."""
        book1 = CatalogBook(title="Book Title", isbn=None)
        book2 = CatalogBook(title="Different Title", isbn="1234567890")
        book1.merge(book2)
        assert book1.title == "Book Title"  # Not overwritten
        assert book1.isbn == "1234567890"  # Filled from book2

    def test_catalog_book_merge_preserves_existing_values(self):
        """merge() should not overwrite existing values."""
        book1 = CatalogBook(title="Original", authors=["Author 1"], isbn="111")
        book2 = CatalogBook(title="Other", authors=["Author 2"], isbn="222", kindle_asin="B001")
        book1.merge(book2)
        assert book1.title == "Original"
        assert book1.authors == ["Author 1"]
        assert book1.isbn == "111"
        assert book1.kindle_asin == "B001"  # New field added

    def test_base_class_merge_raises_not_implemented(self):
        """merge() on base class should raise NotImplementedError."""
        work1 = CombinedCatalogWork(title="Work 1")
        work2 = CombinedCatalogWork(title="Work 2")
        with pytest.raises(NotImplementedError):
            work1.merge(work2)

    def test_article_merge_raises_not_implemented(self):
        """merge() on CatalogArticle should raise NotImplementedError."""
        article1 = CatalogArticle(title="Article 1")
        article2 = CatalogArticle(title="Article 2")
        with pytest.raises(NotImplementedError):
            article1.merge(article2)


class TestSerialization:
    """Tests for serialization to/from dict."""

    def test_catalog_book_asdict(self):
        """asdict should return all fields including work_type."""
        book = CatalogBook(title="Test", isbn="123", authors=["A"])
        d = book.asdict
        assert d["title"] == "Test"
        assert d["isbn"] == "123"
        assert d["authors"] == ["A"]
        assert d["work_type"] == "book"

    def test_catalog_article_asdict(self):
        """asdict should include article-specific fields."""
        article = CatalogArticle(title="Test", url="https://example.com", publication="Blog")
        d = article.asdict
        assert d["title"] == "Test"
        assert d["url"] == "https://example.com"
        assert d["publication"] == "Blog"
        assert d["work_type"] == "article"

    def test_catalog_podcast_asdict(self):
        """asdict should include podcast-specific fields."""
        podcast = CatalogPodcastEpisode(
            title="Episode", podcast_name="Show", episode_number=42
        )
        d = podcast.asdict
        assert d["title"] == "Episode"
        assert d["podcast_name"] == "Show"
        assert d["episode_number"] == 42
        assert d["work_type"] == "podcast"

    def test_roundtrip_book(self):
        """CatalogBook should serialize and deserialize correctly."""
        original = CatalogBook(
            title="Test Book",
            authors=["Author One"],
            isbn="1234567890",
            kindle_asin="B001",
            consumed_date="2024-01-15",
        )
        d = original.asdict
        restored = CatalogBook.from_dict(d)
        assert restored.title == original.title
        assert restored.authors == original.authors
        assert restored.isbn == original.isbn
        assert restored.kindle_asin == original.kindle_asin
        assert restored.consumed_date == original.consumed_date
        assert restored.work_type == "book"

    def test_roundtrip_article(self):
        """CatalogArticle should serialize and deserialize correctly."""
        original = CatalogArticle(
            title="Test Article",
            authors=["Author"],
            url="https://example.com/article",
            publication="Tech Blog",
        )
        d = original.asdict
        restored = CombinedCatalogWork.from_dict(d)
        assert isinstance(restored, CatalogArticle)
        assert restored.title == original.title
        assert restored.url == original.url
        assert restored.publication == original.publication

    def test_roundtrip_podcast(self):
        """CatalogPodcastEpisode should serialize and deserialize correctly."""
        original = CatalogPodcastEpisode(
            title="Episode Title",
            podcast_name="My Podcast",
            episode_number=100,
            url="https://podcast.com/ep100",
        )
        d = original.asdict
        restored = CombinedCatalogWork.from_dict(d)
        assert isinstance(restored, CatalogPodcastEpisode)
        assert restored.title == original.title
        assert restored.podcast_name == original.podcast_name
        assert restored.episode_number == original.episode_number

    def test_roundtrip_video(self):
        """CatalogVideo should serialize and deserialize correctly."""
        original = CatalogVideo(
            title="Video Title",
            url="https://youtube.com/watch?v=abc",
            authors=["Creator"],
        )
        d = original.asdict
        restored = CombinedCatalogWork.from_dict(d)
        assert isinstance(restored, CatalogVideo)
        assert restored.title == original.title
        assert restored.url == original.url
        assert restored.authors == original.authors

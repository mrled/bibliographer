"""Tests for the slugify function."""

import pytest

from bibliographer.cardcatalog import CatalogArticle, CatalogBook
from bibliographer.util.slugify import (
    extract_raindrop_highlight_id,
    generate_raindrop_slug,
    generate_slug_for_work,
    slugify,
)


class TestSlugifyBasic:
    """Tests for basic slugify behavior."""

    def test_multiple_spaces(self):
        """Slugify should collapse multiple spaces into single hyphens."""
        assert slugify("hello   world") == "hello-world"


class TestSlugifySubtitle:
    """Tests for subtitle removal behavior."""

    def test_remove_subtitle_default(self):
        """Slugify should remove subtitles by default."""
        assert slugify("Main Title: The Subtitle") == "main-title"

    def test_remove_subtitle_explicit_true(self):
        """Slugify should remove subtitles when remove_subtitle=True."""
        assert slugify("Main Title: The Subtitle", remove_subtitle=True) == "main-title"

    def test_keep_subtitle(self):
        """Slugify should keep subtitles when remove_subtitle=False."""
        assert slugify("Main Title: The Subtitle", remove_subtitle=False) == "main-title-the-subtitle"

    def test_multiple_colons_remove_subtitle(self):
        """Slugify should remove everything after the first colon."""
        assert slugify("Title: Part 1: Section A") == "title"

    def test_multiple_colons_keep_subtitle(self):
        """Slugify should keep content after colons when remove_subtitle=False."""
        assert slugify("Title: Part 1: Section A", remove_subtitle=False) == "title-part-1-section-a"


class TestSlugifyEdgeCases:
    """Tests for edge cases."""

    def test_only_the(self):
        """Slugify keeps 'the' when not followed by space (edge case)."""
        assert slugify("The") == "the"


class TestGenerateRaindropSlug:
    """Tests for raindrop slug generation."""

    def test_basic_generation(self):
        """Generate slug with domain, title, and highlight ID."""
        result = generate_raindrop_slug(
            url="https://example.com/article",
            title="My Article Title",
            highlight_id="670b2d1c37e0980e9a123456",
        )
        assert result == "example.com/my-article-title-670b2d1c37e0980e9a123456"

    def test_keeps_subtitle(self):
        """Raindrop slugs should keep subtitles (colons in title)."""
        result = generate_raindrop_slug(
            url="https://blog.example.org/post",
            title="Main Title: The Subtitle",
            highlight_id="abcdef1234567890abcdef12",
        )
        assert result == "blog.example.org/main-title-the-subtitle-abcdef1234567890abcdef12"

    def test_url_with_path(self):
        """URL path should not affect the domain extraction."""
        result = generate_raindrop_slug(
            url="https://www.example.com/deep/nested/path/article",
            title="Test",
            highlight_id="123456789012345678901234",
        )
        assert result == "www.example.com/test-123456789012345678901234"


class TestExtractRaindropHighlightId:
    """Tests for extracting highlight ID from raindrop slugs."""

    def test_extract_from_valid_slug(self):
        """Extract highlight ID from a valid raindrop slug."""
        slug = "example.com/my-article-title-670b2d1c37e0980e9a123456"
        assert extract_raindrop_highlight_id(slug) == "670b2d1c37e0980e9a123456"

    def test_extract_from_slug_with_subdomain(self):
        """Extract from slug with subdomain in path."""
        slug = "blog.example.org/main-title-the-subtitle-abcdef1234567890abcdef12"
        assert extract_raindrop_highlight_id(slug) == "abcdef1234567890abcdef12"

    def test_returns_none_for_non_raindrop_slug(self):
        """Return None for slugs without highlight ID."""
        assert extract_raindrop_highlight_id("my-article-title") is None

    def test_returns_none_for_short_id(self):
        """Return None if ID is not exactly 24 hex characters."""
        assert extract_raindrop_highlight_id("example.com/title-abc123") is None

    def test_returns_none_for_non_hex_id(self):
        """Return None if ID contains non-hex characters."""
        assert extract_raindrop_highlight_id("example.com/title-zzzzzzzzzzzzzzzzzzzzzzzz") is None


class TestGenerateSlugForWork:
    """Tests for generate_slug_for_work function."""

    def test_book_removes_subtitle(self):
        """Book slugs should remove subtitles."""
        book = CatalogBook(title="Main Title: The Subtitle")
        result = generate_slug_for_work(book)
        assert result == "main-title"

    def test_article_keeps_subtitle(self):
        """Article slugs should keep subtitles."""
        article = CatalogArticle(title="Main Title: The Subtitle")
        result = generate_slug_for_work(article)
        assert result == "main-title-the-subtitle"

    def test_raindrop_article(self):
        """Raindrop article slugs should use domain/title-id format when slug has highlight ID."""
        article = CatalogArticle(title="My Article", url="https://example.com/post")
        current_slug = "example.com/old-title-670b2d1c37e0980e9a123456"
        result = generate_slug_for_work(article, current_slug)
        assert result == "example.com/my-article-670b2d1c37e0980e9a123456"

    def test_raindrop_preserves_highlight_id(self):
        """Raindrop regeneration should preserve the original highlight ID."""
        article = CatalogArticle(title="Updated Title: With Subtitle", url="https://blog.example.org/article")
        current_slug = "blog.example.org/old-title-abcdef1234567890abcdef12"
        result = generate_slug_for_work(article, current_slug)
        assert result == "blog.example.org/updated-title-with-subtitle-abcdef1234567890abcdef12"

    def test_article_without_raindrop_id_uses_simple_slug(self):
        """Articles with non-raindrop slugs should use simple slug format."""
        article = CatalogArticle(title="Test Article", url="https://example.com")
        result = generate_slug_for_work(article, "old-simple-slug")
        assert result == "test-article"

    def test_article_with_url_but_no_highlight_id_uses_simple_slug(self):
        """Articles with URL but no highlight ID in slug use simple format."""
        article = CatalogArticle(title="My Post", url="https://example.com/post")
        result = generate_slug_for_work(article, "my-post")
        assert result == "my-post"

    def test_slug_with_highlight_id_but_no_url_uses_simple_slug(self):
        """If slug has highlight ID pattern but item has no URL, use simple slug."""
        article = CatalogArticle(title="Test")
        current_slug = "example.com/test-670b2d1c37e0980e9a123456"
        result = generate_slug_for_work(article, current_slug)
        assert result == "test"

    def test_article_without_title_uses_url(self):
        """Articles without title should fall back to URL for slug."""
        article = CatalogArticle(url="https://example.com/my-article-path")
        result = generate_slug_for_work(article)
        assert result == "httpsexamplecommy-article-path"

    def test_item_without_title_or_url_raises_error(self):
        """Items without title or URL should raise ValueError."""
        article = CatalogArticle()
        with pytest.raises(ValueError, match="Cannot generate slug"):
            generate_slug_for_work(article)

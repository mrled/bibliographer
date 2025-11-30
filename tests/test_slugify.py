"""Tests for the slugify function."""

import pytest

from bibliographer.util.slugify import slugify


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

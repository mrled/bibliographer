"""Tests for Raindrop.io highlight processing."""

import json
import pathlib
import tempfile

from bibliographer.cardcatalog import CardCatalog, CatalogArticle
from bibliographer.sources.raindrop import process_raindrop_highlights


def test_process_raindrop_highlights_groups_by_url():
    """Test that multiple highlights for the same URL are grouped into one article."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = pathlib.Path(tmpdir)
        catalog = CardCatalog.from_data_root(data_root)

        # Load test data
        test_data_path = pathlib.Path(__file__).parent / "data" / "raindrop_highlights.json"
        with open(test_data_path) as f:
            highlights = json.load(f)

        # Load highlights into catalog
        for highlight_id, highlight in highlights.items():
            catalog.raindrop_highlights.contents[highlight_id] = highlight

        # Process highlights
        process_raindrop_highlights(catalog)

        # The cfenollosa.com article has 3 highlights in the test data
        cfenollosa_url = "https://cfenollosa.com/blog/ai-favors-texts-written-by-other-ais-even-when-theyre-worse-than-human-ones.html"
        cfenollosa_article = None
        for slug, work in catalog.combinedlib.contents.items():
            if work.url == cfenollosa_url:
                cfenollosa_article = work
                break

        assert cfenollosa_article is not None, "Article for cfenollosa.com not found"
        assert isinstance(cfenollosa_article, CatalogArticle)
        assert len(cfenollosa_article.highlights["raindrop"]) == 3


def test_process_raindrop_highlights_sets_article_fields():
    """Test that article title, url, slug, and consumed_date are set correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = pathlib.Path(tmpdir)
        catalog = CardCatalog.from_data_root(data_root)

        # Load test data
        test_data_path = pathlib.Path(__file__).parent / "data" / "raindrop_highlights.json"
        with open(test_data_path) as f:
            highlights = json.load(f)

        # Load highlights into catalog
        for highlight_id, highlight in highlights.items():
            catalog.raindrop_highlights.contents[highlight_id] = highlight

        # Process highlights
        process_raindrop_highlights(catalog)

        # Find the Go Proverbs article
        go_proverbs_url = "https://go-proverbs.github.io/"
        go_article = None
        for slug, work in catalog.combinedlib.contents.items():
            if work.url == go_proverbs_url:
                go_article = work
                break

        assert go_article is not None, "Go Proverbs article not found"
        assert go_article.title == "Go Proverbs"
        assert go_article.url == go_proverbs_url
        assert go_article.slug is not None
        assert go_article.consumed_date == "2025-11-30T12:29:17.765Z"

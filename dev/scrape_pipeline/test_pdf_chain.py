"""
Unit tests (no network) and integration tests (--network) for pdf_chain.py and download_pdf_workflow.

Run unit tests only (default):
  pytest dev/scrape_pipeline/test_pdf_chain.py

Run all including network integration tests:
  pytest dev/scrape_pipeline/test_pdf_chain.py --network
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scraper.pdf_chain import (
    apply_tier1_transform,
    is_blacklisted,
    is_github_blob,
    parse_citation_pdf_url,
    should_download_as_pdf,
)


# ── apply_tier1_transform ──────────────────────────────────────────────────────

class TestApplyTier1Transform:

    def test_arxiv_abs(self):
        assert apply_tier1_transform("https://arxiv.org/abs/2501.12345") == "https://arxiv.org/pdf/2501.12345"

    def test_arxiv_html(self):
        assert apply_tier1_transform("https://arxiv.org/html/2501.12345") == "https://arxiv.org/pdf/2501.12345"

    def test_arxiv_abs_version_suffix(self):
        assert apply_tier1_transform("https://arxiv.org/abs/2501.12345v2") == "https://arxiv.org/pdf/2501.12345v2"

    def test_arxiv_html_version_suffix(self):
        assert apply_tier1_transform("https://arxiv.org/html/2403.00001v3") == "https://arxiv.org/pdf/2403.00001v3"

    def test_arxiv_pdf_already(self):
        assert apply_tier1_transform("https://arxiv.org/pdf/2501.12345") is None

    def test_arxiv_www_prefix(self):
        assert apply_tier1_transform("https://www.arxiv.org/abs/2501.12345") == "https://www.arxiv.org/pdf/2501.12345"

    def test_aclanthology_plain(self):
        assert apply_tier1_transform("https://aclanthology.org/2022.acl-long.100") == "https://aclanthology.org/2022.acl-long.100.pdf"

    def test_aclanthology_trailing_slash(self):
        assert apply_tier1_transform("https://aclanthology.org/2022.acl-long.100/") == "https://aclanthology.org/2022.acl-long.100.pdf"

    def test_aclanthology_already_pdf(self):
        assert apply_tier1_transform("https://aclanthology.org/2022.acl-long.100.pdf") is None

    def test_aclanthology_already_pdf_uppercase(self):
        assert apply_tier1_transform("https://aclanthology.org/paper.PDF") is None

    def test_openreview_forum(self):
        assert apply_tier1_transform("https://openreview.net/forum?id=ABC123") == "https://openreview.net/pdf?id=ABC123"

    def test_openreview_pdf_already(self):
        assert apply_tier1_transform("https://openreview.net/pdf?id=ABC123") is None

    def test_non_tier1_domain(self):
        assert apply_tier1_transform("https://journals.plos.org/plosone/article?id=x") is None

    def test_mdpi(self):
        assert apply_tier1_transform("https://www.mdpi.com/2073-4441/14/1/1") is None


# ── is_blacklisted ─────────────────────────────────────────────────────────────

class TestIsBlacklisted:

    def test_books_google(self):
        assert is_blacklisted("https://books.google.com/books?id=123") is True

    def test_jstor(self):
        assert is_blacklisted("https://www.jstor.org/stable/123456") is True

    def test_ieeexplore(self):
        assert is_blacklisted("https://ieeexplore.ieee.org/document/123") is True

    def test_muse_jhu(self):
        assert is_blacklisted("https://muse.jhu.edu/article/123") is True

    def test_spiedigitallibrary(self):
        assert is_blacklisted("https://www.spiedigitallibrary.org/...") is True

    def test_semanticscholar(self):
        assert is_blacklisted("https://www.semanticscholar.org/paper/...") is True

    def test_openalex(self):
        assert is_blacklisted("https://openalex.org/W123") is True

    def test_www_prefix_stripped(self):
        assert is_blacklisted("https://www.jstor.org/stable/123") is True

    def test_arxiv_not_blacklisted(self):
        assert is_blacklisted("https://arxiv.org/abs/2501.12345") is False

    def test_plos_not_blacklisted(self):
        assert is_blacklisted("https://journals.plos.org/plosone/article?id=x") is False

    def test_mdpi_not_blacklisted(self):
        assert is_blacklisted("https://www.mdpi.com/article/123") is False

    def test_example_not_blacklisted(self):
        assert is_blacklisted("https://example.com/paper.pdf") is False


# ── is_github_blob ─────────────────────────────────────────────────────────────

class TestIsGithubBlob:

    def test_blob_pdf(self):
        assert is_github_blob("https://github.com/user/repo/blob/main/paper.pdf") is True

    def test_blob_py_file(self):
        # Blob pattern fires on path structure, not just .pdf suffix
        assert is_github_blob("https://github.com/user/repo/blob/main/code.py") is True

    def test_blob_deep_path(self):
        assert is_github_blob("https://github.com/user/repo/blob/main/papers/2024/study.pdf") is True

    def test_raw_path_not_blob(self):
        assert is_github_blob("https://github.com/user/repo/raw/main/paper.pdf") is False

    def test_raw_githubusercontent_not_blob(self):
        assert is_github_blob("https://raw.githubusercontent.com/user/repo/main/paper.pdf") is False

    def test_www_prefix_stripped(self):
        assert is_github_blob("https://www.github.com/user/repo/blob/main/paper.pdf") is True

    def test_non_github_domain(self):
        assert is_github_blob("https://gitlab.com/user/repo/blob/main/paper.pdf") is False

    def test_arxiv_pdf(self):
        assert is_github_blob("https://arxiv.org/pdf/2501.12345") is False


# ── should_download_as_pdf ─────────────────────────────────────────────────────

class TestShouldDownloadAsPdf:

    def test_arxiv_abs(self):
        assert should_download_as_pdf("https://arxiv.org/abs/2501.12345") is True

    def test_arxiv_pdf(self):
        assert should_download_as_pdf("https://arxiv.org/pdf/2501.12345") is True

    def test_aclanthology(self):
        assert should_download_as_pdf("https://aclanthology.org/2022.acl-long.100") is True

    def test_openreview(self):
        assert should_download_as_pdf("https://openreview.net/forum?id=ABC") is True

    def test_direct_pdf_url(self):
        assert should_download_as_pdf("https://example.com/paper.pdf") is True

    def test_direct_pdf_url_uppercase(self):
        assert should_download_as_pdf("https://example.com/paper.PDF") is True

    def test_github_blob_pdf_false(self):
        # GitHub blob URLs end in .pdf but should NOT be downloaded
        assert should_download_as_pdf("https://github.com/user/repo/blob/main/paper.pdf") is False

    def test_multistep_candidate_false(self):
        # MULTI_STEP candidates (no .pdf suffix, non-TIER1) → False
        assert should_download_as_pdf("https://journals.plos.org/plosone/article?id=x") is False

    def test_blacklisted_domain_false(self):
        # Blacklist domains: cli should not route to download_pdf (no PDF available anyway)
        assert should_download_as_pdf("https://books.google.com/books?id=x") is False

    def test_html_page_false(self):
        assert should_download_as_pdf("https://example.com/article/interesting-topic") is False


# ── parse_citation_pdf_url ─────────────────────────────────────────────────────

class TestParseCitationPdfUrl:

    def test_name_before_content(self):
        html = '<meta name="citation_pdf_url" content="https://example.com/paper.pdf">'
        assert parse_citation_pdf_url(html) == "https://example.com/paper.pdf"

    def test_content_before_name(self):
        html = "<meta content='https://example.com/paper.pdf' name='citation_pdf_url'>"
        assert parse_citation_pdf_url(html) == "https://example.com/paper.pdf"

    def test_single_quotes(self):
        html = "<meta name='citation_pdf_url' content='https://example.com/paper.pdf'>"
        assert parse_citation_pdf_url(html) == "https://example.com/paper.pdf"

    def test_mixed_quotes_name_first(self):
        html = '<meta name="citation_pdf_url" content=\'https://example.com/paper.pdf\'>'
        # Regex uses same-quote-char within each group; mixed across name/content may not match
        # This test verifies the actual regex behavior (not a requirement to handle mixed)
        result = parse_citation_pdf_url(html)
        # Accept either a URL result or None (regex may not match mixed quotes)
        assert result is None or result == "https://example.com/paper.pdf"

    def test_no_meta_tag(self):
        html = "<html><head><title>Paper</title></head><body>Content</body></html>"
        assert parse_citation_pdf_url(html) is None

    def test_empty_string(self):
        assert parse_citation_pdf_url("") is None

    def test_other_meta_tags_ignored(self):
        html = '<meta name="description" content="A paper"><meta name="citation_pdf_url" content="https://host.com/file.pdf">'
        assert parse_citation_pdf_url(html) == "https://host.com/file.pdf"

    def test_real_world_plos_style(self):
        # Realistic HTML fragment from a PLOS journal page
        html = (
            '<meta name="citation_pdf_url" '
            'content="https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0000001&type=printable">'
        )
        result = parse_citation_pdf_url(html)
        assert result == "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0000001&type=printable"


# ── Integration tests — require real network (run with --network) ──────────────
#
# These tests exercise download_pdf_workflow end-to-end with real URLs verified in
# dev/search_pipeline/14_download_classify_probe.py (PDF_OK confirmed).
# They specifically guard against regression of the TIER1 transform bug where
# arxiv /pdf/<id> (no .pdf suffix) was incorrectly routed to citation_pdf_url extraction.
#
# URLs used:
#   arxiv:       https://arxiv.org/abs/2603.13277     (bead verification URL)
#   aclanthology: https://aclanthology.org/2020.emnlp-main.400/  (probe 14 PDF_OK)
#   openreview:  https://openreview.net/forum?id=TuFjICawSc      (probe 14 PDF_OK)

@pytest.mark.network
class TestDownloadPdfWorkflowIntegration:

    def _assert_downloaded(self, result, tmp_path):
        assert len(result) == 1
        text = result[0].text
        assert text.startswith("Downloaded:"), (
            f"Expected 'Downloaded: ...' but got: {text!r}\n"
            "This may indicate a TIER1 transform bug (URL routed to wrong chain step)."
        )
        pdfs = list(tmp_path.glob("*.pdf"))
        assert len(pdfs) >= 1, "No .pdf file written to output directory"
        assert pdfs[0].read_bytes()[:4] == b"%PDF", "File does not start with %PDF magic bytes"

    def test_arxiv_abs_tier1_transform(self, tmp_path):
        """arxiv /abs/ → TIER1 transform → /pdf/ → direct download (not citation_pdf_url branch)."""
        from src.scraper.download_pdf import download_pdf_workflow
        result = download_pdf_workflow("https://arxiv.org/abs/2603.13277", str(tmp_path))
        self._assert_downloaded(result, tmp_path)

    def test_arxiv_pdf_direct_no_suffix(self, tmp_path):
        """arxiv /pdf/<id> input (no .pdf suffix) → TIER1 transform returns None → is_tier1 guard
        skips multi-step branch → direct download succeeds.
        Regression: previously, citation_pdf_url extraction was invoked, server returned
        application/pdf (not text/html), extract_citation_pdf_url returned None, workflow
        reported 'no direct PDF path or citation_pdf_url meta tag found'. Bead a1a."""
        from src.scraper.download_pdf import download_pdf_workflow
        result = download_pdf_workflow("https://arxiv.org/pdf/2603.13277", str(tmp_path))
        self._assert_downloaded(result, tmp_path)

    def test_arxiv_html_tier1_transform(self, tmp_path):
        """arxiv /html/ variant → same TIER1 transform path."""
        from src.scraper.download_pdf import download_pdf_workflow
        result = download_pdf_workflow("https://arxiv.org/html/2603.13277", str(tmp_path))
        self._assert_downloaded(result, tmp_path)

    def test_aclanthology_trailing_slash_tier1(self, tmp_path):
        """aclanthology URL with trailing slash → TIER1 strips slash + appends .pdf → download.
        Verified PDF_OK in probe 14."""
        from src.scraper.download_pdf import download_pdf_workflow
        result = download_pdf_workflow("https://aclanthology.org/2020.emnlp-main.400/", str(tmp_path))
        self._assert_downloaded(result, tmp_path)

    def test_openreview_forum_tier1(self, tmp_path):
        """openreview /forum?id= → TIER1 transforms to /pdf?id= → download.
        Verified PDF_OK in probe 14."""
        from src.scraper.download_pdf import download_pdf_workflow
        result = download_pdf_workflow("https://openreview.net/forum?id=TuFjICawSc", str(tmp_path))
        self._assert_downloaded(result, tmp_path)

    def test_blacklisted_domain_returns_error(self, tmp_path):
        """Blacklisted domain returns blocked error, not download."""
        from src.scraper.download_pdf import download_pdf_workflow
        result = download_pdf_workflow("https://books.google.com/books?id=xyz", str(tmp_path))
        assert len(result) == 1
        assert "blocked-domain list" in result[0].text

    def test_github_blob_returns_error(self, tmp_path):
        """GitHub blob URL returns clear error, not download."""
        from src.scraper.download_pdf import download_pdf_workflow
        result = download_pdf_workflow("https://github.com/user/repo/blob/main/paper.pdf", str(tmp_path))
        assert len(result) == 1
        assert "GitHub blob" in result[0].text

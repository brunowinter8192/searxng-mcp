# INFRASTRUCTURE
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from mcp.types import TextContent

# From pdf_chain.py: URL chain resolution (blacklist, TIER1 transforms, multi-step citation_pdf_url)
from src.scraper.pdf_chain import (
    apply_tier1_transform,
    extract_citation_pdf_url,
    is_blacklisted,
    is_github_blob,
)

logger = logging.getLogger(__name__)


# ORCHESTRATOR
def download_pdf_workflow(url: str, output_dir: str = str(Path.home() / "Downloads")) -> list[TextContent]:
    logger.info("Downloading PDF: %s", url)

    # Step 1: Hard blacklist — domains that never yield PDFs
    if is_blacklisted(url):
        from src.scraper.pdf_chain import _base_domain
        domain = _base_domain(url)
        logger.info("PDF download blocked (blacklist): %s", domain)
        return [TextContent(type="text", text=f"Cannot download PDF from {url}: {domain} is on the blocked-domain list (no accessible PDF path).")]

    # Step 2: GitHub blob viewer — URL ends in .pdf but server returns HTML
    if is_github_blob(url):
        logger.info("PDF download blocked (GitHub blob viewer): %s", url)
        return [TextContent(type="text", text=f"Cannot download PDF from {url}: GitHub blob URLs serve HTML viewers. Use the raw URL (github.com/.../raw/...) instead.")]

    # Step 3: TIER1 transform (arxiv /abs/ → /pdf/, aclanthology + .pdf, openreview /forum → /pdf)
    fetch_url = apply_tier1_transform(url) or url
    if fetch_url != url:
        logger.info("TIER1 transform: %s → %s", url, fetch_url)

    # Step 4: If still not a direct PDF path, try multi-step citation_pdf_url extraction
    if not urlparse(fetch_url).path.lower().endswith(".pdf"):
        citation_url = extract_citation_pdf_url(fetch_url)
        if citation_url:
            logger.info("Multi-step citation_pdf_url: %s → %s", fetch_url, citation_url)
            fetch_url = citation_url
        else:
            logger.info("No PDF path found for: %s", url)
            return [TextContent(type="text", text=f"Cannot download PDF from {url}: no direct PDF path or citation_pdf_url meta tag found.")]

    # Step 5: Stream download
    try:
        response = requests.get(fetch_url, stream=True, timeout=30)
        response.raise_for_status()
    except requests.HTTPError as e:
        return [TextContent(type="text", text=f"Error downloading {fetch_url}: HTTP {e.response.status_code}")]
    except requests.RequestException as e:
        return [TextContent(type="text", text=f"Error downloading {fetch_url}: {e}")]

    # Step 6: Verify PDF content (Content-Type or %PDF magic)
    content_type = response.headers.get("Content-Type", "")
    body_start = b""
    if "application/pdf" not in content_type:
        # Peek at first 4 bytes to catch servers that send PDF with wrong Content-Type
        body_start = next(response.iter_content(chunk_size=4), b"")
        if body_start[:4] != b"%PDF":
            return [TextContent(type="text", text=f"Error: URL did not return a PDF (Content-Type: {content_type})")]

    filename = extract_filename(response, fetch_url)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    try:
        write_pdf(response, output_path, body_start)
    except OSError as e:
        return [TextContent(type="text", text=f"Error writing file {output_path}: {e}")]

    file_size = os.path.getsize(output_path)
    size_str = format_size(file_size)
    logger.info("PDF saved: %s (%s)", output_path, size_str)
    return [TextContent(type="text", text=f"Downloaded: {output_path} ({size_str})")]


# FUNCTIONS

# Extract filename from Content-Disposition header, URL path, or generate one
def extract_filename(response: requests.Response, url: str) -> str:
    content_disposition = response.headers.get("Content-Disposition", "")
    if content_disposition:
        match = re.search(r'filename[^;=\n]*=[\"\']?([^;\"\'\n]+)', content_disposition)
        if match:
            name = match.group(1).strip()
            if name:
                return name

    path = url.split("?")[0].rstrip("/")
    basename = path.split("/")[-1]
    if basename and basename.lower().endswith(".pdf"):
        return basename

    return f"download_{int(time.time())}.pdf"


# Write streamed response content to file; body_start is pre-read bytes (may be empty)
def write_pdf(response: requests.Response, output_path: str, body_start: bytes = b"") -> None:
    with open(output_path, "wb") as f:
        if body_start:
            f.write(body_start)
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


# Format byte count as human-readable KB or MB string
def format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / 1024:.1f} KB"

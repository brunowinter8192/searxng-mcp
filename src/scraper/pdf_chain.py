# INFRASTRUCTURE
import re
from urllib.parse import urlparse, urlunparse

import requests

# Domains that deterministically return HTML without a PDF recovery path.
# Empirically validated in dev/search_pipeline/14_download_classify_probe.py.
# scribd.com: book previews may be wanted for --books (bead x4f); keep blocked until then.
# nature.com: 2/2 HTML_OK in probe; OA articles may have citation_pdf_url — re-verify before removing.
# semanticscholar.org / openalex.org: Tier-2; blocked until engine-level URL-fix (bead x4f).
HARD_BLACKLIST = frozenset({
    "books.google.com",
    "jstor.org",
    "ieeexplore.ieee.org",
    "muse.jhu.edu",
    "search.proquest.com",
    "scribd.com",
    "nature.com",
    "search.ebscohost.com",
    "spiedigitallibrary.org",
    "semanticscholar.org",
    "openalex.org",
})

# Domains with deterministic URL transforms that produce a direct PDF URL (100% success in probe 14).
TIER1_DOMAINS = frozenset({"arxiv.org", "aclanthology.org", "openreview.net"})

# github.com/<owner>/<repo>/blob/<branch>/<path>.pdf — server returns HTML viewer, not PDF bytes.
# github.com/<owner>/<repo>/raw/... and raw.githubusercontent.com remain valid direct-PDF hosts.
_GITHUB_BLOB_PATH_RE = re.compile(r"^/[^/]+/[^/]+/blob/")

# Matches both attribute orderings of the citation_pdf_url meta tag.
CITATION_PDF_RE = re.compile(
    r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']'
    r'|<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
    re.IGNORECASE,
)

_HTML_READ_BYTES = 32 * 1024
_HOP_TIMEOUT = 10.0
_USER_AGENT = "Mozilla/5.0 (compatible; searxng-pdf-chain/1.0)"


# FUNCTIONS

# Strip www. prefix and return bare domain
def _base_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


# Apply Tier-1 URL transform; return transformed URL or None if no transform applies
def apply_tier1_transform(url: str) -> str | None:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    # arxiv.org: /abs/<id> or /html/<id> → /pdf/<id> (preserves version suffix)
    if domain == "arxiv.org":
        if re.match(r"^/(abs|html)/", parsed.path):
            new_path = re.sub(r"^/(abs|html)/", "/pdf/", parsed.path)
            return urlunparse(parsed._replace(path=new_path))
        return None  # /pdf/ already — no transform needed

    # aclanthology.org: strip trailing slash, append .pdf (skip if already .pdf)
    if domain == "aclanthology.org":
        if parsed.path.lower().endswith(".pdf"):
            return None
        new_path = parsed.path.rstrip("/") + ".pdf"
        return urlunparse(parsed._replace(path=new_path))

    # openreview.net: /forum?id=X → /pdf?id=X
    if domain == "openreview.net":
        if parsed.path == "/forum":
            return urlunparse(parsed._replace(path="/pdf"))
        return None

    return None


# Return True if base domain is in HARD_BLACKLIST
def is_blacklisted(url: str) -> bool:
    domain = _base_domain(url)
    return domain in HARD_BLACKLIST or any(domain.endswith("." + b) for b in HARD_BLACKLIST)


# Return True if URL is a GitHub blob viewer (serves HTML, not PDF bytes)
def is_github_blob(url: str) -> bool:
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc == "github.com" and bool(_GITHUB_BLOB_PATH_RE.match(parsed.path))
    except Exception:
        return False


# Return True if url should be routed to download_pdf_workflow from cli.py auto-routing.
# TIER1 domains → transform produces PDF; direct .pdf suffix (non-blob) → download as-is.
# MULTI_STEP candidates (no .pdf suffix, non-TIER1) → False: cli scrape_url handles them.
# BLACKLIST domains → False: let scrape_url_workflow attempt scraping; blacklist fires in download_pdf_workflow if explicitly invoked.
def should_download_as_pdf(url: str) -> bool:
    domain = _base_domain(url)
    if domain in TIER1_DOMAINS or any(domain.endswith("." + t) for t in TIER1_DOMAINS):
        return True
    if is_github_blob(url):
        return False
    try:
        path = urlparse(url).path.lower()
        return path.endswith(".pdf")
    except Exception:
        return False


# Extract citation_pdf_url value from HTML body string; return URL or None
def parse_citation_pdf_url(body: str) -> str | None:
    m = CITATION_PDF_RE.search(body)
    if m:
        return m.group(1) or m.group(2)
    return None


# Hop 1: GET HTML via requests, parse citation_pdf_url meta tag; return URL or None on any failure
def extract_citation_pdf_url(url: str) -> str | None:
    try:
        with requests.get(
            url,
            timeout=_HOP_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
            allow_redirects=True,
            stream=True,
        ) as resp:
            if resp.status_code >= 400:
                return None
            ct = resp.headers.get("content-type", "").lower()
            if "text/html" not in ct:
                return None
            chunks: list[bytes] = []
            bytes_read = 0
            for chunk in resp.iter_content(chunk_size=4096):
                chunks.append(chunk)
                bytes_read += len(chunk)
                if bytes_read >= _HTML_READ_BYTES:
                    break
        body = b"".join(chunks).decode("utf-8", errors="replace")
        return parse_citation_pdf_url(body)
    except Exception:
        return None

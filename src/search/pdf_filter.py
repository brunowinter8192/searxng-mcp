# INFRASTRUCTURE
from urllib.parse import urlparse

# Domains that deliver actual PDF bytes (directly or via deterministic URL transform).
# Sources: download_classify_20260507_172709.md (Section 2), pdf_chain.py TIER1,
#          citation_pdf_followup_20260507_174223.md (Section 3), domain knowledge for OA preprint servers.
#
# TIER1 (deterministic transform → PDF bytes):
#   arxiv.org, aclanthology.org, openreview.net
#
# OA preprint servers (arxiv-class, direct PDF access):
#   biorxiv.org, medrxiv.org, chemrxiv.org, osf.io
#
# OA publisher hosts confirmed in probe (100% via citation_pdf_url):
#   mdpi.com, pmc.ncbi.nlm.nih.gov
#
# Specialty academic repositories:
#   inspirehep.net, zenodo.org, hal.science, hal.archives-ouvertes.fr, europepmc.org
PDF_HOSTS: frozenset[str] = frozenset({
    # TIER1
    "arxiv.org",
    "aclanthology.org",
    "openreview.net",
    # OA preprint servers
    "biorxiv.org",
    "medrxiv.org",
    "chemrxiv.org",
    "osf.io",
    # OA publishers — probe-confirmed
    "mdpi.com",
    "pmc.ncbi.nlm.nih.gov",
    # Specialty repositories
    "inspirehep.net",
    "zenodo.org",
    "hal.science",
    "hal.archives-ouvertes.fr",
    "europepmc.org",
})

# Domains that must never match PDF rules even if path contains .pdf or /pdf/.
# github.com/blob/ serves an HTML viewer, not PDF bytes (raw.githubusercontent.com is separate).
# books.google.com, scribd.com, semanticscholar.org, openalex.org, researchgate.net
# return HTML landing pages only — confirmed 0% PDF_OK in probe.
_HOST_BLACKLIST: frozenset[str] = frozenset({
    "github.com",
    "gitlab.com",
    "books.google.com",
    "scribd.com",
    "semanticscholar.org",
    "openalex.org",
    "researchgate.net",
})

# Path substrings (case-insensitive) that signal a direct PDF file or known PDF-serving path.
# Sources: free_word_injection_probe_20260507_033631.md (+pdf result sets),
#          download_classify_20260507_172709.md (PDF_OK URL patterns).
PDF_PATH_PATTERNS: tuple[str, ...] = (
    ".pdf",           # Direct PDF file link (covers university servers, conf sites, etc.)
    "/pdf/",          # PDF subdirectory (readthedocs, jmmackenzie.io/pdf/, irlab .../pdf/)
    "/pdfs/",         # Plural variant
    "/content/pdf/",  # Springer: link.springer.com/content/pdf/...
    "/_downloads/",   # readthedocs PDF downloads (readthedocs.io/_downloads/.../name.pdf)
)


# FUNCTIONS

# True if URL belongs to PDF host whitelist (exact or subdomain) or matches a PDF path pattern;
# blacklisted hosts return False regardless of path.
def is_pdf_url(url: str) -> bool:
    d = _domain(url)
    if d in _HOST_BLACKLIST or any(d.endswith("." + h) for h in _HOST_BLACKLIST):
        return False
    if d in PDF_HOSTS:
        return True
    if any(d.endswith("." + h) for h in PDF_HOSTS):
        return True
    path = urlparse(url).path.lower()
    return any(p in path for p in PDF_PATH_PATTERNS)


# Extract bare domain (strip www. prefix) from URL
def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""

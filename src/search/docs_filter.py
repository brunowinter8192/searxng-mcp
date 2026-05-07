# INFRASTRUCTURE
from urllib.parse import urlparse

# Forums / Q&A
# reddit.com, stackoverflow.com, bugs.python.org
#
# Blogs / video
# medium.com, youtube.com, dev.to
#
# Code hosting (repos, not rendered docs)
# github.com, gitlab.com, bitbucket.org
#
# Tutorial / community sites (not official docs)
# w3schools.com, geeksforgeeks.org, freecodecamp.org, codezup.com, riptutorial.com
#
# Document-preview / repo-wiki noise
# slideshare.net, scribd.com, deepwiki.com
DOCS_BLACKLIST_HOSTS: frozenset[str] = frozenset({
    # Forums / Q&A
    "reddit.com",
    "stackoverflow.com",
    "bugs.python.org",
    # Blogs / video
    "medium.com",
    "youtube.com",
    "dev.to",
    # Code hosting (repos, not rendered docs)
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    # Tutorial / community sites (not official docs)
    "w3schools.com",
    "geeksforgeeks.org",
    "freecodecamp.org",
    "codezup.com",
    "riptutorial.com",
    # Document-preview / repo-wiki noise
    "slideshare.net",
    "scribd.com",
    "deepwiki.com",
})

# Path-patterns that signal non-docs content even on otherwise-legitimate hosts.
# digitalocean.com is NOT in BLACKLIST_HOSTS — subdomain endswith match would kill
# docs.digitalocean.com. The /community/ path-pattern catches community/tutorials/ instead.
# nginx.com/blog/ is the nginx blog, not docs (docs are at nginx.org).
DOCS_BLACKLIST_PATHS: tuple[str, ...] = (
    "/blog/",
    "/community/",
)


# FUNCTIONS

# True if URL is NOT matched by the noise blacklist — passes docs through, blocks known noise.
# Inverted logic: returns False only on blacklist hit; otherwise True.
def is_docs_url(url: str) -> bool:
    d = _domain(url)
    if d in DOCS_BLACKLIST_HOSTS or any(d.endswith("." + h) for h in DOCS_BLACKLIST_HOSTS):
        return False
    path = urlparse(url).path.lower()
    if any(p in path for p in DOCS_BLACKLIST_PATHS):
        return False
    return True


# Extract bare domain (strip www. prefix) from URL
def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""

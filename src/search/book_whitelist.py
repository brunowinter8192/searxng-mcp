# INFRASTRUCTURE
from urllib.parse import urlparse

# Marketplaces / retailers
# amazon.com, amazon.de, amazon.in, amazon.co.uk, abebooks.de, thalia.de,
# barnesandnoble.com, kulturkaufhaus.de, buecher.de, hugendubel.info, beck-shop.de,
# exsila.ch, booklooker.de, buchshop.bod.de, books.apple.com, ebooks.com,
# audible.com, blinkist.com, perlego.com, ebookaktiv.de, legimi.de,
# e-booksdirectory.com, hqaudiobooks.net, book-sharing.de, downmagaz.net, ebooksyard.com
#
# Publishers
# oreilly.com, manning.com, simonandschuster.com, penguinrandomhouse.com,
# hachettebookgroup.com, fischerverlage.de, chbeck.de, bloomsbury.com, penguin.de,
# tharpa.com, bibleandbookcenter.com
#
# Catalogs / archives
# goodreads.com, gutenberg.org, openlibrary.org, archive.org, books.google.com,
# deutsche-digitale-bibliothek.de, en.wikisource.org, yumpu.com, worldmags.net,
# drive.google.com
#
# Book-list aggregators
# fivebooks.com, bookauthority.org, ordertoread.com, reedsy.com, bookseriesinorder.com,
# booksinorder.org, infobooks.org, booksaremythirdplace.com, eatyourbooks.com,
# fictionhorizon.com, shortform.com, dedp.online, harrypotter.com
#
# Book-companion sites
# refactoring.guru, formdesignpatterns.com, cleancodecookbook.com, superfastpython.com,
# pythonbooks.org, buddho.org, berniegourley.com, eternalisedofficial.com
BOOK_WHITELIST: frozenset[str] = frozenset({
    "amazon.com",
    "amazon.de",
    "amazon.in",
    "amazon.co.uk",
    "abebooks.de",
    "thalia.de",
    "barnesandnoble.com",
    "kulturkaufhaus.de",
    "buecher.de",
    "hugendubel.info",
    "beck-shop.de",
    "exsila.ch",
    "booklooker.de",
    "buchshop.bod.de",
    "books.apple.com",
    "ebooks.com",
    "audible.com",
    "blinkist.com",
    "perlego.com",
    "ebookaktiv.de",
    "legimi.de",
    "e-booksdirectory.com",
    "hqaudiobooks.net",
    "book-sharing.de",
    "downmagaz.net",
    "ebooksyard.com",
    "oreilly.com",
    "manning.com",
    "simonandschuster.com",
    "penguinrandomhouse.com",
    "hachettebookgroup.com",
    "fischerverlage.de",
    "chbeck.de",
    "bloomsbury.com",
    "penguin.de",
    "tharpa.com",
    "bibleandbookcenter.com",
    "goodreads.com",
    "gutenberg.org",
    "openlibrary.org",
    "archive.org",
    "books.google.com",
    "deutsche-digitale-bibliothek.de",
    "en.wikisource.org",
    "yumpu.com",
    "worldmags.net",
    "drive.google.com",
    "fivebooks.com",
    "bookauthority.org",
    "ordertoread.com",
    "reedsy.com",
    "bookseriesinorder.com",
    "booksinorder.org",
    "infobooks.org",
    "booksaremythirdplace.com",
    "eatyourbooks.com",
    "fictionhorizon.com",
    "shortform.com",
    "dedp.online",
    "harrypotter.com",
    "refactoring.guru",
    "formdesignpatterns.com",
    "cleancodecookbook.com",
    "superfastpython.com",
    "pythonbooks.org",
    "buddho.org",
    "berniegourley.com",
    "eternalisedofficial.com",
})

# Path substrings that signal book content regardless of domain
BOOK_PATH_PATTERNS: tuple[str, ...] = (
    "/books/",
    "/buecher/",
    "/buch/",
    "/book/show/",
    "/dp/",
    "/ebooks/",
    "/detail/isbn-",
    "/library/view/",
    "/title/",
    "/ebook/",
)


# FUNCTIONS

# True if URL belongs to the book whitelist (domain or subdomain) or matches a book path pattern
def is_book_url(url: str) -> bool:
    d = _domain(url)
    if d in BOOK_WHITELIST:
        return True
    if any(d.endswith("." + h) for h in BOOK_WHITELIST):
        return True
    path = urlparse(url).path.lower()
    return any(p in path for p in BOOK_PATH_PATTERNS)


# Extract bare domain (strip www. prefix) from URL
def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""

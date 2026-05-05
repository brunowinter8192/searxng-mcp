# INFRASTRUCTURE
import html
import re

# From result.py: SearchResult dataclass
from src.search.result import SearchResult

MIN_FLOOR = 40  # minimum clean_len for a non-floor snippet

# Combined EN + DE stopwords — no NLTK dependency
STOPWORDS = {
    "a","about","above","after","again","all","also","although","among","an","and","any",
    "are","as","at","be","because","been","before","being","between","both","but","by",
    "can","could","did","do","does","doing","during","each","even","ever","for","from",
    "get","got","had","has","have","having","he","her","here","him","his","how","if",
    "in","into","is","it","its","itself","just","like","may","me","might","more","most",
    "much","my","nor","not","now","of","off","on","or","other","our","out","own","per",
    "s","shall","she","should","since","so","some","such","t","than","that","the","their",
    "them","then","there","these","they","this","those","through","to","too","under","up",
    "us","very","was","we","were","what","when","where","which","while","who","will",
    "with","would","you","your","re","ve","ll","d","m","no","use",
    "aber","alle","allem","allen","aller","alles","als","also","am","an","ander","andere",
    "anderen","anderer","anderes","auf","aus","bei","bin","bis","bist","da","damit","dann",
    "das","dass","dem","den","denn","der","des","dessen","die","dies","diese","diesem",
    "diesen","dieser","dieses","doch","dort","du","durch","ein","eine","einem","einen",
    "einer","eines","er","es","etwas","fur","gegen","gibt","hat","hatte","haben","hier",
    "hin","hinter","ich","im","in","ist","ja","jede","jedem","jeden","jeder","jedes",
    "jetzt","kann","kein","keine","konnte","mal","man","mehr","mein","mit","nach","nicht",
    "noch","nun","nur","ob","oder","ohne","schon","sehr","seit","sich","sie","sind","so",
    "soll","sondern","uber","um","und","uns","unter","viel","vom","von","vor","war","was",
    "weil","wenn","werden","wie","will","wir","wird","wo","wurde","zum","zur","zu",
}


# FUNCTIONS

# Ratio of unique non-stopword content words (≥3 chars) to all word tokens
def lexical_density(text: str) -> float:
    words = re.findall(r'\b[a-zA-ZäöüÄÖÜßé]{3,}\b', text.lower())
    if not words:
        return 0.0
    unique_content = {w for w in words if w not in STOPWORDS}
    return len(unique_content) / len(words)


# Remove Google doubled title+domain prefix (heuristic: maximize cut across all repeated-chunk matches)
def _strip_doubled_prefix(text: str) -> str:
    if len(text) < 60:
        return text
    head = text[:300]
    best_cut = 0
    for L in (100, 70, 50, 30):
        if len(head) < 2 * L:
            continue
        for start in range(0, min(len(head) - 2 * L, 100)):
            chunk = head[start:start + L]
            second = head.find(chunk, start + L)
            if 0 < second and second + L <= len(head):
                cut = second + L
                if cut > best_cut:
                    best_cut = cut
    return text[best_cut:] if best_cut else text


# Decode HTML entities, strip doubled prefix, and remove bloat patterns; return normalized whitespace
def _strip_bloat(text: str) -> str:
    text = html.unescape(text)
    text = _strip_doubled_prefix(text)
    text = re.sub(r'^Web results', '', text)
    text = re.sub(r'^Featured snippet from the web', '', text)
    text = re.sub(r'\bRead more\b.*', '', text)
    text = re.sub(r'\d[\d,.]*[Kk]?\+? *(likes|comments|answers|posts) *·[^\n]*', '', text)
    text = re.sub(r'\S*›\S*', '', text)
    text = re.sub(r'\d{1,2} \w{3,9} \d{4} — ', '', text)
    text = re.sub(r'&[a-z]+;|&#\d+;', '', text)
    text = re.sub(r'Tagged with [\w, ]+\.?$', '', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    return ' '.join(text.split())


# Select best snippet for a merged SearchResult by score (clean_len × lexical_density); returns (snippet, source)
def _select_snippet(r: SearchResult) -> tuple[str, str]:
    preview = r.preview or {}
    og   = preview.get("og") or ""
    meta = preview.get("meta") or ""

    # Build candidate pool: source_name -> raw_text
    candidates: dict[str, str] = {}
    if og:   candidates["og"]   = og
    if meta: candidates["meta"] = meta
    for eng, text in (r.snippets or {}).items():
        if text: candidates[eng] = text

    if not candidates:
        return "", ""

    # Score every candidate (clean_len from strip_bloat, lex_density from raw)
    scored = {}
    for src, text in candidates.items():
        clean_len = len(_strip_bloat(text))
        score     = clean_len * lexical_density(text)
        scored[src] = (score, clean_len)

    # Floor check; fall back to best-of-worst if everything below floor
    above_floor = {s: v for s, v in scored.items() if v[1] >= MIN_FLOOR}
    pool = above_floor if above_floor else scored

    winner       = max(pool, key=lambda s: pool[s][0])
    display_text = _strip_bloat(candidates[winner])
    return display_text, winner

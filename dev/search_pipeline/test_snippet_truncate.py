import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.search.snippet import _truncate, MAX_SNIPPET_LEN

# Test 1: Short text returned unchanged
short = "This is a short snippet under 200 chars."
assert _truncate(short, MAX_SNIPPET_LEN) == short, "Test 1 FAIL: short text modified"

# Test 2: Long text with ". " at ~450 → clean period cut, no ellipsis
# "A"*449 + ". " puts the period at index 449 (inside [250, 499]); total 551 chars
long_period = "A" * 449 + ". " + "B" * 100
result2 = _truncate(long_period, MAX_SNIPPET_LEN)
assert result2.endswith("."), f"Test 2 FAIL: does not end with period — {result2[-10:]!r}"
assert "…" not in result2,   f"Test 2 FAIL: unexpected ellipsis — {result2[-10:]!r}"
assert len(result2) == 450,  f"Test 2 FAIL: wrong length {len(result2)}"

# Test 3: Long text with spaces but no ". " → word-boundary cut with ellipsis
# "word " × 120 = 600 chars, no periods anywhere
no_period = "word " * 120
result3 = _truncate(no_period, MAX_SNIPPET_LEN)
assert result3.endswith("…"),           f"Test 3 FAIL: missing ellipsis — {result3[-10:]!r}"
assert len(result3) <= MAX_SNIPPET_LEN, f"Test 3 FAIL: too long {len(result3)}"

# Test 4: No spaces at all → hard cut at exactly MAX_SNIPPET_LEN + 1 chars
no_spaces = "x" * 1000
result4 = _truncate(no_spaces, MAX_SNIPPET_LEN)
assert result4.endswith("…"),                f"Test 4 FAIL: missing ellipsis — {result4[-5:]!r}"
assert len(result4) == MAX_SNIPPET_LEN + 1,  f"Test 4 FAIL: wrong length {len(result4)}"

print("OK")

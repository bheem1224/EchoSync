"""
Fix the broken apostrophe OR clauses in Tier 1 and escalation Tier 2 SQL.

The previous session wrote '\\'' (backslash + apostrophe) and '\\u2019'
(6-char literal escape text) into the SQL strings — neither is what SQLite
expects.  The correct approach (already working in the initial Tier 2 block)
is to embed the actual Unicode characters directly, so SQLite sees them as
genuine character literals.

SQL idiom used:
  REPLACE(t.title, '<U+2019>', '''')
  = replace right-single-quotation-mark with plain apostrophe
  The replacement value '''' is: opening SQL quote + '' (escaped ') + closing
  SQL quote → SQL string containing one plain apostrophe.
"""

path = "web/routes/playlists.py"
src = open(path, encoding="utf-8").read()

# ── TIER 1 ────────────────────────────────────────────────────────────────────
# The broken text uses a literal backslash before the apostrophe producing
# '\\'/' and '\\u2019' in the file.  Replace both OR clauses together so the
# match is unambiguous.

RSQM = "\u2019"   # RIGHT SINGLE QUOTATION MARK  '
LSQM = "\u2018"  # LEFT SINGLE QUOTATION MARK   '

tier1_old = (
    "                                OR\n"
    "                                (LOWER(a.name) = LOWER(:artist_exact)\n"
    "                                    AND LOWER(REPLACE(REPLACE(t.title, '\\'', ''), '\\u2019', '')) LIKE LOWER(:title_norm_pattern))\n"
    "                                OR\n"
    "                                (LOWER(a.name) LIKE LOWER(:artist_pattern)\n"
    "                                    AND LOWER(REPLACE(REPLACE(t.title, '\\'', ''), '\\u2019', '')) LIKE LOWER(:title_norm_pattern))\n"
)

# New: normalize DB title from smart-apos → plain apos, then LIKE plain-apos pattern.
# title_norm_pattern already has plain apostrophes (provider goes through normalize_text).
tier1_new = (
    "                                OR\n"
    "                                (LOWER(a.name) = LOWER(:artist_exact)\n"
    f"                                    AND LOWER(REPLACE(REPLACE(t.title, '{RSQM}', '''''), '{LSQM}', ''''')) LIKE LOWER(:title_norm_pattern))\n"
    "                                OR\n"
    "                                (LOWER(a.name) LIKE LOWER(:artist_pattern)\n"
    f"                                    AND LOWER(REPLACE(REPLACE(t.title, '{RSQM}', '''''), '{LSQM}', ''''')) LIKE LOWER(:title_norm_pattern))\n"
)

new_src = src.replace(tier1_old, tier1_new, 1)
if new_src == src:
    print("TIER 1: no match — dumping surrounding lines for diagnosis")
    lines = src.splitlines()
    for i in range(148, 158):
        print(i+1, repr(lines[i]))
else:
    src = new_src
    print("TIER 1: replaced OK")

# ── ESCALATION TIER 2 ─────────────────────────────────────────────────────────
# Lines 341-342 (0-indexed 340-341) have the same broken escapes.

esc_old = (
    "                                        OR LOWER(REPLACE(REPLACE(t.title, '\\'', ''), '\\u2019', '')) = LOWER(REPLACE(REPLACE(:title_exact, '\\'', ''), '\\u2019', ''))\n"
    f"                                        OR LOWER(REPLACE(REPLACE(t.title, '\\u2019', '\\''), '\\u2018', '\\'')) = LOWER(:title_exact)\n"
)

esc_new = (
    f"                                        OR LOWER(REPLACE(REPLACE(t.title, '{RSQM}', '''''), '{LSQM}', ''''')) = LOWER(REPLACE(REPLACE(:title_exact, '{RSQM}', '''''), '{LSQM}', '''''))\n"
    f"                                        OR LOWER(t.title) = LOWER(REPLACE(REPLACE(:title_exact, '{RSQM}', '''''), '{LSQM}', '''''))\n"
)

new_src = src.replace(esc_old, esc_new, 1)
if new_src == src:
    print("ESCALATION TIER 2: no match — dumping surrounding lines for diagnosis")
    lines = src.splitlines()
    for i in range(338, 346):
        print(i+1, repr(lines[i]))
else:
    src = new_src
    print("ESCALATION TIER 2: replaced OK")

# ── WRITE + SYNTAX CHECK ──────────────────────────────────────────────────────
open(path, "w", encoding="utf-8").write(src)
print("Written.")

import ast
try:
    ast.parse(src)
    print("Syntax OK.")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

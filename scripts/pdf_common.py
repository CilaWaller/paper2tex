"""Shared helpers for the paper2tex code-enhanced tools.

These utilities generalize the reusable logic that was proven on real
conversions: unicode/ligature cleaning, two-column detection, equation-number
anchor detection, math-vs-prose classification, and bbox math. They contain no
paper-specific constants; page geometry (column split, page height) is derived
per page from the rendered PDF instead of being hard-coded.

Dependencies: PyMuPDF (``fitz``). Pillow + numpy are only needed for the
ink-trimming step in ``formula_crops.py`` and are imported there, not here.
"""

from __future__ import annotations

import re

# Math-font name fragments emitted by common typesetting engines. These are
# strong positive signals that a text span belongs to a displayed formula.
MATH_FONTS = ("MTSY", "RMTMI", "MTEX", "MSBM", "CMSY", "CMMI", "CMEX", "MSAM")

_LIGATURES = {
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
    "–": "-", "—": "-", "−": "-", "“": '"', "”": '"', "’": "'",
}
_LIG_TABLE = str.maketrans(_LIGATURES)

_MATH_SYMBOL_RE = re.compile(r"[=∫∑∏√≤≥±×·∈∼≈∝∇∂]|\b(arg|max|min|log|exp|Pr|s\.t\.)\b")
_PROSE_STOPWORDS_RE = re.compile(
    r"\b(the|of|and|to|in|for|with|from|that|this|where|which|under|after|"
    r"before|then|hence|we|is|are|was|were|can|will)\b",
    re.I,
)
_PROSE_START_RE = re.compile(
    r"^(where|both|each|within|once|the|we|metrics|similar|generated|for|or|an|"
    r"this|to determine|assuming|under|after|before)\b",
    re.I,
)


def clean(text: str) -> str:
    """Collapse whitespace and normalize ligatures/dashes/quotes."""
    return re.sub(r"\s+", " ", (text or "").translate(_LIG_TABLE)).strip()


def strip_control(text: str) -> str:
    """Drop the control characters that degraded math extraction produces."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text or "")


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]{2,}", clean(text)))


def eq_numbers(text: str, max_eq: int = 200) -> list[int]:
    """Return equation numbers ``(n)`` found in ``text`` within ``1..max_eq``."""
    return [
        int(m.group(1))
        for m in re.finditer(r"\((\d{1,3})\)", clean(text))
        if 1 <= int(m.group(1)) <= max_eq
    ]


def is_anchor_text(text: str) -> bool:
    """True when the text is/contains an equation-number anchor.

    Handles the three positions seen in practice: standalone ``(12)``, a number
    at the end of a math line, and a number that starts a block, e.g.
    ``(51) Both ...``.
    """
    t = clean(text)
    return bool(
        re.fullmatch(r"\(?\d{1,3}\)?", t)
        or re.search(r"\(\d{1,3}\)\s*$", t)
        or re.match(r"^\(\d{1,3}\)(?:\s|$)", t)
    )


def has_math_font(fonts) -> bool:
    return any(any(tag in (font or "") for tag in MATH_FONTS) for font in fonts)


def bbox_union(boxes):
    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


def clamp_bbox(bbox, page_w, page_h, xpad=2.5, ypad=2.0):
    return [
        max(0.0, bbox[0] - xpad),
        max(0.0, bbox[1] - ypad),
        min(page_w, bbox[2] + xpad),
        min(page_h, bbox[3] + ypad),
    ]


def column_of(bbox, page_w, columns=2):
    """Assign a bbox to a column index based on its horizontal center.

    Column boundaries are derived from ``page_w`` so the helper works for any
    page size, not just US-letter 612pt papers.
    """
    if columns <= 1:
        return 0
    cx = (bbox[0] + bbox[2]) / 2
    col = int(cx / (page_w / columns))
    return max(0, min(columns - 1, col))


def is_prose_like(text: str) -> bool:
    """Heuristic: True for ordinary running prose, False for formula lines."""
    t = clean(text)
    wc = word_count(t)
    if wc >= 6 and _PROSE_STOPWORDS_RE.search(t) and not _MATH_SYMBOL_RE.search(t):
        return True
    if _PROSE_START_RE.match(t) and wc > 3 and "=" not in t:
        return True
    if wc > 11 and not _MATH_SYMBOL_RE.search(t):
        return True
    return False


def math_like(text: str, has_font: bool) -> bool:
    """Score a line as math-like using fonts, symbols, and brevity."""
    t = clean(text)
    if not t:
        return False
    if is_anchor_text(t) and word_count(t) <= 5:
        return True
    if is_prose_like(t):
        return False
    score = 0
    if has_font:
        score += 3
    if _MATH_SYMBOL_RE.search(t):
        score += 3
    if re.search(r"\b(P[A-Z]{1,3}|P\(|N\(|D\(|R\[|I\[|C\d|H0|H1|T\(|Q\(|f\(|p\(|L\()", t):
        score += 2
    if word_count(t) <= 3:
        score += 1
    return score >= 2


def extract_lines(page, columns=2):
    """Return line-level records with bbox, fonts, column, and center-y.

    ``page`` is a PyMuPDF page. Output is sorted in reading order
    (column, top-to-bottom, left-to-right).
    """
    page_w = page.rect.width
    data = page.get_text("dict")
    lines = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = clean("".join(span.get("text", "") for span in spans))
            if not text:
                continue
            bbox = list(line["bbox"])
            fonts = sorted({span.get("font", "") for span in spans})
            lines.append({
                "text": text,
                "bbox": bbox,
                "fonts": fonts,
                "has_math_font": has_math_font(fonts),
                "col": column_of(bbox, page_w, columns),
                "cy": (bbox[1] + bbox[3]) / 2,
            })
    lines.sort(key=lambda ln: (ln["col"], ln["cy"], ln["bbox"][0]))
    return lines

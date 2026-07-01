"""Stage 2b tool: export formula text candidates to assist transcription.

Reuses the anchor detection and line-selection logic from ``formula_crops``
to dump, for each equation, the raw text lines that fall inside the crop
region. Writes ``_formula_text_candidates.json``.

This is a transcription aid, NOT a recognizer. Embedded math fonts are often
degraded (control characters, missing symbols), so these candidates must be
combined with the rendered crop and, when available, ``pdftotext -layout``
output before writing editable LaTeX. No OCR or external service is used.

Usage:
    python formula_text.py --pdf "<path>.pdf" --out "<output_dir>" \
        --max-eq 72 [--columns 2] [--last-page 13]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdf_common as pc  # noqa: E402
import formula_crops as fc  # noqa: E402


def export(pdf_path, out_dir, max_eq, columns, last_page):
    block_map = json.loads((out_dir / "_section_source_blocks.json").read_text(encoding="utf-8"))
    doc = fitz.open(pdf_path)

    anchors = fc.find_anchors(doc, block_map, max_eq, columns, last_page or 0)
    grouped = {}
    for a in anchors:
        grouped.setdefault((a["page"], a["col"]), []).append(a)
    for g in grouped.values():
        g.sort(key=lambda a: a["cy"])

    items = []
    for a in anchors:
        lines = pc.extract_lines(doc[a["page"] - 1], columns)
        group = grouped[(a["page"], a["col"])]
        pos = group.index(a)
        prev_cy = group[pos - 1]["cy"] if pos else None
        next_cy = group[pos + 1]["cy"] if pos + 1 < len(group) else None
        selected = fc.candidate_lines(lines, a, prev_cy, next_cy)
        texts = [pc.strip_control(ln["text"]) for _, ln in selected]
        items.append({
            "equation": a["equation_no"],
            "page": a["page"],
            "selected_line_indexes": [idx for idx, _ in selected],
            "text_lines": texts,
            "joined_text": " \\ ".join(texts),
        })

    items.sort(key=lambda it: it["equation"])
    path = out_dir / "_formula_text_candidates.json"
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"count": len(items), "file": str(path)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Export formula text candidates for transcription.")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-eq", type=int, required=True)
    ap.add_argument("--columns", type=int, default=2)
    ap.add_argument("--last-page", type=int, default=0)
    args = ap.parse_args()

    result = export(Path(args.pdf), Path(args.out), args.max_eq, args.columns, args.last_page)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

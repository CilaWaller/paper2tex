"""Stage 2 tool: optimized formula crops + manifest validation.

Generalizes the fourth-pass formula crop optimizer that produced correct,
tight crops. For every displayed equation it:

1. Detects equation-number anchors in all positions (standalone ``(12)``,
   trailing ``... (12)``, and leading ``(51) Both ...``), from line-level
   text first and the saved block map as a fallback.
2. Groups anchors by page and column.
3. Starts at the anchor line and expands only through adjacent math-like
   lines, stopping at ordinary prose, large vertical gaps, or the next anchor.
4. Trims the crop to actual ink (Pillow + numpy) and adds small padding.
5. Writes ``formula_crops/formula_pXX_eqYY.png`` plus
   ``formula_crops/_formula_manifest.json``.
6. Validates the manifest against the expected equation range and flags
   missing numbers and suspiciously sized crops.

Usage:
    python formula_crops.py --pdf "<path>.pdf" --out "<output_dir>" \
        --max-eq 72 [--columns 2] [--scale 5] [--last-page 13]

Crops are verification/reference assets only. Per the skill, formulas must be
transcribed to editable LaTeX; the crops back that transcription up.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdf_common as pc  # noqa: E402


def find_anchors(doc, block_map, max_eq, columns, last_page):
    """Detect equation-number anchors via line text, then block-map fallback."""
    anchors, seen = [], set()
    limit = last_page if last_page else doc.page_count

    for pno in range(1, min(limit, doc.page_count) + 1):
        for idx, line in enumerate(pc.extract_lines(doc[pno - 1], columns)):
            text = line["text"]
            if not pc.is_anchor_text(text):
                continue
            for n in pc.eq_numbers(text, max_eq):
                if n in seen:
                    continue
                if pc.word_count(text) > 8 and not text.startswith(f"({n})"):
                    continue
                seen.add(n)
                anchors.append({
                    "equation_no": n, "page": pno, "line": idx,
                    "bbox": line["bbox"], "col": line["col"], "cy": line["cy"],
                    "source": "line-anchor",
                })

    for page in block_map["pages"]:
        pno = page["page"]
        if last_page and pno > last_page:
            continue
        page_w = page["width"]
        for idx, block in enumerate(page["blocks"]):
            if block.get("type") != "text" or not pc.is_anchor_text(block.get("text", "")):
                continue
            for n in pc.eq_numbers(block.get("text", ""), max_eq):
                if n in seen:
                    continue
                seen.add(n)
                bbox = block["bbox"]
                anchors.append({
                    "equation_no": n, "page": pno, "line": None, "bbox": bbox,
                    "col": pc.column_of(bbox, page_w, columns),
                    "cy": (bbox[1] + bbox[3]) / 2,
                    "source": f"block-fallback-{idx}",
                })

    anchors.sort(key=lambda a: a["equation_no"])
    return anchors


def candidate_lines(lines, anchor, prev_cy, next_cy):
    """Select the math lines that make up one equation, stopping at prose."""
    top = max(30.0, (prev_cy + anchor["cy"]) / 2 if prev_cy is not None else anchor["cy"] - 80.0)
    bottom = (next_cy + anchor["cy"]) / 2 if next_cy is not None else anchor["cy"] + 80.0
    same_col = [
        (idx, ln) for idx, ln in enumerate(lines)
        if ln["col"] == anchor["col"] and top <= ln["cy"] <= bottom
    ]
    if not same_col:
        return [(-1, {"bbox": anchor["bbox"], "text": "", "cy": anchor["cy"]})]

    if anchor.get("line") is not None:
        pos = next((i for i, (idx, _) in enumerate(same_col) if idx == anchor["line"]), None)
    else:
        pos = None
    if pos is None:
        pos = min(range(len(same_col)), key=lambda i: abs(same_col[i][1]["cy"] - anchor["cy"]))

    selected = [same_col[pos]]

    last_top = same_col[pos][1]["bbox"][1]
    for idx, ln in reversed(same_col[:pos]):
        if last_top - ln["bbox"][3] > 18:
            break
        ml = pc.math_like(ln["text"], ln.get("has_math_font", False))
        if pc.is_prose_like(ln["text"]) and not ml:
            break
        if ml:
            selected.append((idx, ln))
            last_top = min(last_top, ln["bbox"][1])
            continue
        break

    last_bottom = same_col[pos][1]["bbox"][3]
    for idx, ln in same_col[pos + 1:]:
        if ln["bbox"][1] - last_bottom > 18:
            break
        ml = pc.math_like(ln["text"], ln.get("has_math_font", False))
        if pc.is_prose_like(ln["text"]) and not (ml and pc.word_count(ln["text"]) <= 3):
            break
        if ml:
            selected.append((idx, ln))
            last_bottom = max(last_bottom, ln["bbox"][3])
            continue
        break

    if len(selected) == 1:
        above = []
        for idx, ln in reversed(same_col[:pos]):
            if anchor["cy"] - ln["cy"] > 75:
                break
            if pc.is_prose_like(ln["text"]) and above:
                break
            if pc.math_like(ln["text"], ln.get("has_math_font", False)):
                above.append((idx, ln))
        if above:
            above.reverse()
            selected.extend(above)

    selected.sort(key=lambda item: item[1]["cy"])
    return selected


def trim_to_ink(page, bbox, scale):
    bbox = pc.clamp_bbox(bbox, page.rect.width, page.rect.height, xpad=4.0, ypad=3.0)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=fitz.Rect(*bbox), alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    gray = np.asarray(image.convert("L"))
    fg = gray < 245
    if not fg.any():
        return bbox
    ys, xs = np.where(fg)
    m = 10
    x0 = max(0, int(xs.min()) - m)
    y0 = max(0, int(ys.min()) - m)
    x1 = min(gray.shape[1] - 1, int(xs.max()) + m)
    y1 = min(gray.shape[0] - 1, int(ys.max()) + m)
    trimmed = [
        bbox[0] + x0 / scale, bbox[1] + y0 / scale,
        bbox[0] + (x1 + 1) / scale, bbox[1] + (y1 + 1) / scale,
    ]
    if trimmed[3] - trimmed[1] < 11:
        cy = (trimmed[1] + trimmed[3]) / 2
        trimmed[1], trimmed[3] = cy - 5.5, cy + 5.5
    return pc.clamp_bbox(trimmed, page.rect.width, page.rect.height, xpad=1.2, ypad=1.0)


def optimize(pdf_path, out_dir, max_eq, columns, scale, last_page):
    formulas = out_dir / "formula_crops"
    formulas.mkdir(parents=True, exist_ok=True)
    block_map = json.loads((out_dir / "_section_source_blocks.json").read_text(encoding="utf-8"))
    doc = fitz.open(pdf_path)

    anchors = find_anchors(doc, block_map, max_eq, columns, last_page)
    grouped = {}
    for a in anchors:
        grouped.setdefault((a["page"], a["col"]), []).append(a)
    for g in grouped.values():
        g.sort(key=lambda a: a["cy"])

    manifest, suspicious = [], []
    for a in anchors:
        page = doc[a["page"] - 1]
        lines = pc.extract_lines(page, columns)
        group = grouped[(a["page"], a["col"])]
        pos = group.index(a)
        prev_cy = group[pos - 1]["cy"] if pos else None
        next_cy = group[pos + 1]["cy"] if pos + 1 < len(group) else None
        selected = candidate_lines(lines, a, prev_cy, next_cy)
        boxes = [ln["bbox"] for _, ln in selected] + [a["bbox"]]
        bbox = trim_to_ink(page, pc.bbox_union(boxes), scale)
        fname = f"formula_p{a['page']:02d}_eq{a['equation_no']:02d}.png"
        page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=fitz.Rect(*bbox), alpha=False).save(formulas / fname)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if h > 95 or w > 270 or h < 10:
            suspicious.append(a["equation_no"])
        manifest.append({
            "equation": f"({a['equation_no']})",
            "page": a["page"],
            "bbox": [round(v, 2) for v in bbox],
            "file": f"formula_crops/{fname}",
            "basis": f"stop-at-prose ink-trimmed crop from {a['source']}; lines {[i for i, _ in selected]}",
            "status": "optimized crop; verify visually against editable LaTeX",
        })

    manifest.sort(key=lambda m: int(m["equation"].strip("()")))
    (formulas / "_formula_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    numbers = {int(m["equation"].strip("()")) for m in manifest}
    return {
        "formula_crops": len(manifest),
        "missing_equations": sorted(set(range(1, max_eq + 1)) - numbers),
        "suspicious_size_equations": sorted(suspicious),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate optimized formula crops and validate them.")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-eq", type=int, required=True, help="Highest equation number, e.g. 72.")
    ap.add_argument("--columns", type=int, default=2, help="Column count (1 or 2).")
    ap.add_argument("--scale", type=int, default=5, help="Crop render scale.")
    ap.add_argument("--last-page", type=int, default=0,
                    help="Ignore anchors after this page (0 = all pages).")
    args = ap.parse_args()

    result = optimize(Path(args.pdf), Path(args.out), args.max_eq,
                      args.columns, args.scale, args.last_page or 0)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

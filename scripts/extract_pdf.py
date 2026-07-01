"""Stage 1 tool: render pages and build a traceable source map.

Generalizes the proven build/extract step. Given a PDF and an output
directory, it renders each page to ``pages/page_XX.png``, extracts embedded
text/image blocks with coordinates, and writes:

- ``pages/page_XX.png``            rendered page images for visual review
- ``_raw_text.txt``                page-separated raw text (diagnostic only)
- ``_blocks.txt``                  human-readable block dump with bbox/fonts
- ``_section_source_blocks.json``  structured block map (the source of truth)
- ``_summary.json``                per-page counts and PDF metadata
- ``_embedded_images.json``        list of embedded raster images with xrefs

Usage:
    python extract_pdf.py --pdf "<path>.pdf" --out "<output_dir>" [--zoom 2.2]

The block map produced here is consumed by ``formula_crops.py`` and
``repair_paragraphs.py``. This tool never writes LaTeX; it only supports
traceability, per the skill's core principles.

Note on figure extraction:
Many academic PDFs render figures as vector graphics (axes, labels, lines),
not as embedded raster images. ``_embedded_images.json`` lists only the
raster images embedded directly in the PDF. For vector-graphics figures,
you must crop from the rendered page image using coordinates derived from
visual inspection of ``pages/page_XX.png``. See ``figure_crops.py`` for
a helper to batch-crop figure regions from page renders.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


def build(pdf_path: Path, out_dir: Path, zoom: float) -> dict:
    pages_dir = out_dir / "pages"
    for d in (out_dir, pages_dir):
        d.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    summary = {
        "pdf": str(pdf_path),
        "paper_name": pdf_path.stem,
        "page_count": doc.page_count,
        "metadata": doc.metadata,
        "pages": [],
    }
    raw_parts, block_parts, json_pages = [], [], []

    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        pix.save(pages_dir / f"page_{i:02d}.png")

        text = page.get_text("text", sort=True)
        raw_parts.append(f"===== Page {i} =====\n{text}\n")

        dct = page.get_text("dict", sort=True)
        page_entry = {
            "page": i,
            "width": page.rect.width,
            "height": page.rect.height,
            "blocks": [],
        }
        tblocks = iblocks = 0
        block_parts.append(
            f"===== Page {i} ({page.rect.width:.1f} x {page.rect.height:.1f}) ====="
        )
        for bi, b in enumerate(dct.get("blocks", [])):
            bbox = [round(float(x), 2) for x in b.get("bbox", [])]
            if b.get("type") == 0:
                tblocks += 1
                lines, font_sizes, fonts = [], [], []
                for ln in b.get("lines", []):
                    line = "".join(sp.get("text", "") for sp in ln.get("spans", []))
                    if line.strip():
                        lines.append(line.rstrip())
                    for sp in ln.get("spans", []):
                        font_sizes.append(sp.get("size", 0))
                        fonts.append(sp.get("font", ""))
                txt = "\n".join(lines).strip()
                entry = {
                    "type": "text",
                    "bbox": bbox,
                    "text": txt,
                    "font_size_max": round(max(font_sizes) if font_sizes else 0, 2),
                    "fonts": sorted(set(fonts))[:6],
                }
                page_entry["blocks"].append(entry)
                block_parts.append(
                    f"TEXT b{bi} bbox={bbox} size={entry['font_size_max']} "
                    f"fonts={entry['fonts']}: " + " | ".join(lines)
                )
            elif b.get("type") == 1:
                iblocks += 1
                entry = {
                    "type": "image",
                    "bbox": bbox,
                    "width": b.get("width"),
                    "height": b.get("height"),
                    "ext": b.get("ext"),
                }
                page_entry["blocks"].append(entry)
                block_parts.append(
                    f"IMAGE b{bi} bbox={bbox} size={b.get('width')}x{b.get('height')}"
                )
        summary["pages"].append({
            "page": i,
            "w": page.rect.width,
            "h": page.rect.height,
            "chars": len(text),
            "text_blocks": tblocks,
            "image_blocks": iblocks,
        })
        json_pages.append(page_entry)

    (out_dir / "_raw_text.txt").write_text("\n".join(raw_parts), encoding="utf-8")
    (out_dir / "_blocks.txt").write_text("\n".join(block_parts), encoding="utf-8")
    (out_dir / "_section_source_blocks.json").write_text(
        json.dumps({"pages": json_pages}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Detect and catalog embedded raster images (for figure extraction reference)
    embedded_images = []
    for i, page in enumerate(doc, start=1):
        imgs = page.get_images(full=True)
        for img in imgs:
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                w, h = pix.width, pix.height
                # Skip tiny 1x1 images (common placeholders)
                if w > 5 and h > 5:
                    embedded_images.append({
                        "page": i,
                        "xref": xref,
                        "width": w,
                        "height": h,
                        "colorspace": str(pix.colorspace).replace("Colorspace.", ""),
                    })
                pix = None
            except Exception:
                pass
    (out_dir / "_embedded_images.json").write_text(
        json.dumps(embedded_images, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary["embedded_image_count"] = len(embedded_images)

    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Render pages and build a PDF source map.")
    ap.add_argument("--pdf", required=True, help="Path to the source PDF.")
    ap.add_argument("--out", required=True, help="Output directory for this paper.")
    ap.add_argument("--zoom", type=float, default=2.2, help="Page render zoom factor.")
    args = ap.parse_args()

    summary = build(Path(args.pdf), Path(args.out), args.zoom)
    print(json.dumps({
        "page_count": summary["page_count"],
        "out": args.out,
        "pages_rendered": summary["page_count"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

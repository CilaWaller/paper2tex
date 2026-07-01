"""Figure cropping helper for vector-graphics figures in academic PDFs.

Many research papers render figures as vector graphics (axes, labels, and
lines drawn with vector primitives), not as embedded bitmap images.
``page.get_images()`` will only find embedded raster images in those cases.

This script helps batch-crop figure regions from rendered page images using
explicit PDF-point coordinates derived from visual inspection of
``pages/page_XX.png``.

You provide a list of figure definitions (page, bbox, filename) via
``--defs`` (a JSON file), and the script crops each figure at 3x zoom and
saves to ``figures/`` along with a crop manifest.

Workflow:
1. Run ``extract_pdf.py`` to generate ``pages/page_XX.png``.
2. Visually inspect pages to determine figure coordinates in PDF points.
   Tip: Open the page image in an image viewer; divide pixel coordinates
   by the zoom factor (default 2.2) to get PDF points.
3. Write a JSON defs file (see example below).
4. Run this script to crop figures.
5. Inspect output; adjust coordinates and re-run if needed.

Usage:
    python figure_crops.py --pdf "<path>.pdf" --out "<output_dir>" \\
        --defs "<figure_defs>.json" [--zoom 3.0]

Figure defs JSON format:
```json
[
  {
    "page": 5,
    "x0": 305,
    "y0": 80,
    "x1": 595,
    "y1": 390,
    "name": "fig_01.png",
    "caption": "Geolocation scenario.",
    "label": "fig:fig_01",
    "confidence": "medium"
  },
  ...
]
```

The script writes ``figures/_crop_manifest.json`` with all figure metadata.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


def crop_figures(pdf_path: Path, out_dir: Path, defs_path: Path, zoom: float) -> dict:
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    defs = json.loads(defs_path.read_text(encoding="utf-8"))

    manifest = []
    errors = []

    for i, fig in enumerate(defs):
        try:
            page_num = int(fig["page"])
            if page_num < 1 or page_num > doc.page_count:
                errors.append(f"Figure {i}: page {page_num} out of range")
                continue

            page = doc[page_num - 1]
            x0 = float(fig["x0"])
            y0 = float(fig["y0"])
            x1 = float(fig["x1"])
            y1 = float(fig["y1"])
            name = fig.get("name", f"fig_{i+1:02d}.png")

            # Clamp to page bounds
            x0 = max(0, min(x0, page.rect.width))
            x1 = max(0, min(x1, page.rect.width))
            y0 = max(0, min(y0, page.rect.height))
            y1 = max(0, min(y1, page.rect.height))

            if x1 <= x0 or y1 <= y0:
                errors.append(f"Figure {i} ({name}): invalid bbox")
                continue

            rect = fitz.Rect(x0, y0, x1, y1)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, clip=rect)
            fig_path = figures_dir / name
            pix.save(fig_path)

            entry = {
                "figure": name,
                "page": page_num,
                "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                "pixel_size": [pix.width, pix.height],
                "caption": fig.get("caption", ""),
                "label": fig.get("label", ""),
                "confidence": fig.get("confidence", "medium"),
                "crop_basis": fig.get("crop_basis", "manual from page image"),
            }
            manifest.append(entry)
            print(f"OK: {name} (page {page_num}, {pix.width}x{pix.height})")

        except Exception as e:
            errors.append(f"Figure {i}: {e}")
            print(f"ERROR figure {i}: {e}")

    # Write manifest
    manifest_path = figures_dir / "_crop_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nManifest: {manifest_path}")

    result = {
        "total": len(defs),
        "successful": len(manifest),
        "errors": errors,
        "manifest": str(manifest_path),
    }

    if errors:
        print(f"WARNING: {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")

    doc.close()
    return result


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Batch-crop figure regions from PDF pages using explicit coordinates."
    )
    ap.add_argument("--pdf", required=True, help="Path to the source PDF.")
    ap.add_argument("--out", required=True, help="Output directory for this paper.")
    ap.add_argument(
        "--defs",
        required=True,
        help="Path to JSON file with figure definitions (page, bbox, name, caption, label).",
    )
    ap.add_argument(
        "--zoom",
        type=float,
        default=3.0,
        help="Render zoom factor for cropped figures (default 3.0 for high quality).",
    )
    args = ap.parse_args()

    result = crop_figures(
        Path(args.pdf),
        Path(args.out),
        Path(args.defs),
        args.zoom,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

# Paper2TeX-skill

> 中文简介：将研究论文 PDF 转换为可追溯的 LaTeX 项目。支持逐页提取、公式识别、图表提取、表格转换，并保持页面可追溯性。

A skill for converting research paper PDFs into traceable LaTeX projects. Designed for extracting papers page-by-page with preserved formulas, figures, tables, references, and reading order.

## Features

- **Page-by-Page Extraction**: Extract content while maintaining traceability to original PDF pages
- **Formula Recognition**: Convert complex mathematical formulas to editable LaTeX with crop verification
- **Figure & Table Extraction**: Extract figures, tables, and their captions with proper placement
- **Reading Order Preservation**: Correctly handle single-column, double-column, and mixed-layout papers
- **Column/Page Continuity Repair**: Merge sentences and words falsely split at column or page boundaries
- **Any LaTeX Template**: Adapt to any user-specified template (journal, conference, thesis, report, or custom class) — the template's own class, packages, and field commands are preserved, not a fixed one
- **Verification & Validation**: Built-in text coverage and continuity checks
- **Extraction Report**: Comprehensive report documenting completeness and uncertainties
- **Bundled Code Tools**: Reusable, parameterized Python tools under `scripts/` that encode the proven extraction/repair logic, so each new paper reuses tested code instead of throwaway scripts

## Bundled Code Tools

The `scripts/` directory contains parameterized tools (no paper-specific constants). Requirements: `PyMuPDF`; plus `Pillow` and `numpy` for `formula_crops.py`.

- `scripts/pdf_common.py` — shared helpers (cleaning, column detection, anchor detection, math/prose classification, line extraction). Imported, not run directly.
- `scripts/extract_pdf.py` — render pages and build the `_section_source_blocks.json` source map.
- `scripts/formula_crops.py` — regenerate optimized formula crops and validate the manifest against the expected equation range.
- `scripts/formula_text.py` — export `_formula_text_candidates.json` to aid editable-LaTeX transcription.
- `scripts/repair_paragraphs.py` — repair cross-column/page paragraph breaks (with a `--dry-run` preview mode; skips math environments).

Example:

```powershell
python scripts/extract_pdf.py --pdf "8 - Author - Title.pdf" --out "output/8 - Author - Title"
python scripts/formula_crops.py --pdf "8 - Author - Title.pdf" --out "output/8 - Author - Title" --max-eq 40 --columns 2
python scripts/repair_paragraphs.py --sections "output/8 - Author - Title/section_drafts" --dry-run
```

Formula crops are verification/reference assets only; formulas must still be transcribed to editable LaTeX. See [SKILL.md](SKILL.md) for full tool usage rules.

## Usage

In Trae AI, invoke the skill when converting research PDFs to LaTeX:

```
Convert paper "12 - Author - Title.pdf" to LaTeX using the template at <template_path>
```

Or simply:

```
Extract paper 8 to LaTeX
```

The template can be any LaTeX template you point to; the skill reads it first and reuses its document class, packages, and field commands.

## Output Structure

For each source PDF, the skill generates:

```
output/paper_name/
├── paperN.tex              # Main compile entry (short ASCII name)
├── extraction_report.md    # Comprehensive extraction report
├── pages/                  # Rendered page images for verification
├── figures/                # Extracted figures and tables
│   └── _crop_manifest.json # Crop metadata
├── formula_crops/          # Formula crop images for verification
└── section_drafts/         # Section-by-section drafts (optional)
    ├── 00_front_matter.tex
    ├── 01_introduction.tex
    └── ...
```

## Workflow Overview

1. **Initialize**: Create project directory, render page images, extract text blocks
2. **Extract**: Reconstruct reading order, identify sections, extract content paragraph-by-paragraph
3. **Process**: Convert formulas, figures, tables to LaTeX; handle multi-column layouts; repair sentences/words split at column or page boundaries
4. **Verify**: Run text coverage checks, continuity validation, and compile verification against the specified template

## Skill Definition

The detailed skill instructions are in [SKILL.md](SKILL.md), which defines:
- Core principles and requirements
- Bundled code tools and their usage rules
- Preflight checks and identity verification
- Page-by-page extraction rules
- Formula, figure, and table handling
- Section completeness workflow
- Final verification checklist

## License

This project is open source and available under the MIT License.

## Acknowledgments

Built for research paper processing workflows in Trae AI.

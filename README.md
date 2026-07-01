# Paper2TeX

> 中文简介：将研究论文 PDF 转换为可追溯的 LaTeX 项目。支持逐页提取、公式识别、图表提取、表格转换，并保持页面可追溯性。

A skill for converting research paper PDFs into traceable LaTeX projects. Designed for extracting papers page-by-page with preserved formulas, figures, tables, references, and reading order.

## Features

- **Page-by-Page Extraction**: Extract content while maintaining traceability to original PDF pages
- **Formula Recognition**: Convert complex mathematical formulas to editable LaTeX with crop verification
- **Figure & Table Extraction**: Extract figures, tables, and their captions with proper placement
- **Reading Order Preservation**: Correctly handle single-column, double-column, and mixed-layout papers
- **LaTeX Template Support**: Adapt to journal/conference templates (IEEE, ACM, etc.)
- **Verification & Validation**: Built-in text coverage and continuity checks
- **Extraction Report**: Comprehensive report documenting completeness and uncertainties

## Usage

In Trae AI, invoke the skill when converting research PDFs to LaTeX:

```
Convert paper "12 - Author - Title.pdf" to LaTeX using the IEEE template
```

Or simply:

```
Extract paper 8 to LaTeX
```

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
3. **Process**: Convert formulas, figures, tables to LaTeX; handle multi-column layouts
4. **Verify**: Run text coverage checks, continuity validation, and compile verification

## Skill Definition

The detailed skill instructions are in [SKILL.md](SKILL.md), which defines:
- Core principles and requirements
- Preflight checks and identity verification
- Page-by-page extraction rules
- Formula, figure, and table handling
- Section completeness workflow
- Final verification checklist

## License

This project is open source and available under the MIT License.

## Acknowledgments

Built for research paper processing workflows in Trae AI.

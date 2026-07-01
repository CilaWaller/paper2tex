---
name: "paper2tex"
description: "Converts research PDFs to traceable LaTeX projects. Invoke when extracting papers page-by-page, formulas, figures, tables, or using a LaTeX template."
---

# Paper2TeX

Use this skill when the user asks to convert one or more research-paper PDFs into editable LaTeX, especially when the output must preserve page traceability, formulas, figures, tables, references, double-column reading order, compilation behavior, or a specified LaTeX template.

## Core Principles

- Process papers one by one unless the user explicitly requests parallel agents; even then, each agent must handle exactly one PDF.
- Do not summarize, rewrite, polish, translate, or compress the paper content.
- Preserve the original language, terminology, citation markers, equation numbers, figure/table numbers, and section order.
- Every extracted section must be traceable to original PDF pages.
- Prefer editable LaTeX for text, formulas, tables, captions, references, appendices, and biographies.
- Use screenshots/crops only as verification aids or placeholders when reliable editable conversion is not possible.
- Mark uncertainty explicitly with `% TODO` in `.tex` and with structured entries in `extraction_report.md`.
- Do not call OCR, external formula-recognition services, external layout-analysis services, or web services for extraction.
- It is allowed to use local PDF rendering/text extraction/cropping tools such as PyMuPDF to render pages, inspect embedded text, extract block coordinates, and crop visual regions. These tools support traceability; they do not replace visual/manual reasoning.
- For content completeness, process the paper by logical sections after page-level extraction. Never replace a section with a short paraphrase or compressed summary.

## Required Output Structure

For each source PDF, create:

```text
output/
  paper_name/
    paperN.tex              # short compile entry, e.g. paper8.tex; use main.tex if no paper number exists
    section_drafts/         # mandatory for long/double-column/dense/template-based papers
    figures/
      _crop_manifest.json
    formula_crops/
    pages/
    extraction_report.md
```

Optional files may be created only when useful for verification:

```text
_raw_text.txt
_blocks.txt
_section_source_blocks.txt
_section_source_blocks.json
_summary.json
paper_name.tex              # optional human-readable wrapper if filename is safe
```

Use a short ASCII compile entry (`paperN.tex` or `main.tex`) whenever the PDF/output folder name is long, contains spaces, non-ASCII punctuation, or may exceed Windows/TeX path limits. The short entry should contain the template preamble and `\input{section_drafts/...}` statements.

## Preflight and Identity Checks

Before extraction:

1. Identify the exact PDF requested by the user. If the user gives a paper number, match the filename prefix exactly, e.g. `8 - *.pdf`.
2. Compare the PDF filename, embedded metadata title, and visually rendered first-page title.
3. If they differ, follow the visible first-page title for LaTeX metadata and record the mismatch in `extraction_report.md`.
4. Decide the compile entry name before writing files:
   - Prefer `paperN.tex` when the user selected a numbered paper.
   - Otherwise use `main.tex`.
   - Avoid compiling directly from long paper-title filenames on Windows.
5. If a template directory is provided, identify the sample `.tex`, class files (`.cls`), style files (`.sty`), bibliography files, and required assets. Copy only files required for local compilation.
6. Build a source map before drafting:
   - rendered page images,
   - embedded text blocks sorted by page/column/bounding box,
   - candidate section headings, including headings split across adjacent lines or blocks,
   - candidate subsection/list-style subheads,
   - candidate equation regions,
   - candidate figure/table regions,
   - references and biography/end-matter regions,
   - filtered non-body regions such as headers, footers, DOI/copyright/license notices, running heads, author notes, captions, and table labels.
7. Save source maps when useful as `_blocks.txt`, `_section_source_blocks.txt`, and/or `_section_source_blocks.json`.
8. For multi-column or template-based papers, preserve enough block metadata for later validation: page number, bbox, column assignment, cleaned text, expected logical section, and exclusion reason when a source block is intentionally not body prose.

## LaTeX Template Support

If the user provides a template path, an existing `.tex` template, or asks to use a journal/conference template:

1. Read the template before writing the output.
2. Preserve the template's document class, packages, metadata structure, bibliography style, and required environments.
3. Insert extracted content into the appropriate location, usually after `\begin{document}` and before bibliography/end matter.
4. Do not overwrite template-specific commands unless necessary.
5. Map extracted fields to template fields:
   - Title -> template title command, e.g. `\title{}` or journal-specific equivalent.
   - Authors -> `\author{}` or template author block.
   - Abstract -> template abstract environment.
   - Keywords -> template keyword command/environment.
   - Sections -> template sectioning commands.
   - Figures/tables -> template-compatible environments.
6. If the template has class/style dependencies, copy only necessary `.cls`, `.sty`, bibliography style, or asset files into the output directory.
7. If the template conflicts with required packages, prefer the template and record package conflicts in `extraction_report.md`.
8. If no template is provided, use a minimal article-style preamble:

```tex
\documentclass{article}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{algorithm}
\usepackage{algorithmic}
\usepackage{hyperref}
\usepackage{cite}
\begin{document}
% extracted content
\end{document}
```

## Workflow

### 1. Initialize Project Directory

For each PDF:

1. Derive `paper_name` from the PDF filename without extension.
2. Create:
   - `output/<paper_name>/`
   - `output/<paper_name>/pages/`
   - `output/<paper_name>/figures/`
   - `output/<paper_name>/formula_crops/`
   - `output/<paper_name>/section_drafts/` when required.
3. Render every PDF page to `pages/page_XX.png` at sufficient resolution for visual review.
4. Record page count, page dimensions, embedded metadata if available, and visible layout observations.

### 2. Page-by-Page Extraction and Reading Order

For every page, insert or preserve traceability comments either in the main `.tex` or in the relevant section draft:

```tex
% ===== Page <page_number> =====
% Layout: single-column / double-column / mixed
% Contains equations: yes/no
% Contains figures: yes/no
% Contains tables: yes/no
% Reading order confidence: high/medium/low
% Uncertain items: ...
```

Rules:

- Determine page layout visually from rendered pages and confirm with block coordinates when embedded text is available.
- For multi-column papers, raw page text (`page.get_text('text')`, copied PDF text, or line-sorted text) is a diagnostic source only; it MUST NOT be used directly as body prose unless a column-order validation proves it is not horizontally interleaved.
- For double-column pages, reconstruct reading order from block coordinates: remove headers/footers/copyright/DOI/license blocks first, then read left column top-to-bottom followed by right column top-to-bottom, while handling full-width titles/floats separately.
- Treat page 1/front matter as a special layout: title/author/abstract/keywords/thanks may be full-width or mixed with the first body column, and lower author-note blocks must not be assigned to `Introduction`.
- Full-width or wide blocks are not automatically section-level prose. Classify them by visual position and nearby headings; license/copyright/watermark blocks must stay excluded even when their bbox is wide.
- Insert cross-column titles, abstracts, equations, figures, and tables according to visual position.
- Exclude page headers, footers, page numbers, copyright notices, DOI lines, author-affiliation footnotes, license notices, and running heads from main text unless required by the paper.
- Front matter (`title`, `authors`, `abstract`, `keywords`, `thanks`) must appear only in the front-matter draft/template fields and must not be duplicated in `Introduction`.
- Do not confuse reference numbers, figure numbers, equation numbers, table numbers, or numbered list labels with section numbers.
- Avoid overly aggressive formula/noise filtering: short prose near equations, variables, or citations must be preserved unless it is clearly a standalone formula fragment.
- Preserve Unicode math symbols and ligatures during extraction or map them explicitly to LaTeX, including common forms such as `∗`, `∆`, `△`, `∑`, `∫`, `≈`, `±`, `√`, and `ﬁ/ﬀ/ﬃ/ﬂ`.

#### Column/Page Final-Line Continuity Pass

For multi-column pages and page boundaries, always run a final-line continuity pass before accepting a section draft.

1. Compare the last body line/block of the current column or page with the first body line/block of the next reading-order column or page.
2. Exclude headers, footers, captions, table bodies, figure labels, license text, page numbers, section headings, bibliography labels, and biography starts before deciding continuity.
3. Join fragments only when visual order and sentence continuity support the join. Strong join signals include:
   - the previous fragment ends without terminal punctuation;
   - the previous fragment ends with a line-break hyphen;
   - the next fragment begins with a lowercase word, continuation phrase, citation, math variable, or object of the previous verb/preposition;
   - the two fragments form a known technical phrase from the paper, e.g. `GAN` + `detection`, `2D search` + `matrix`.
4. Dehyphenate only when the hyphen is a PDF line-break artifact, e.g. `indus-` + `trial` -> `industrial`, `authen` + `ic` -> `authentic`.
5. Preserve real compound hyphens such as `anti-spoofing`, `low-cost`, `small-delay`, and `deep learning-based`.
6. Do not join across section/subsection headings, bibliography item boundaries, biography starts, independent list items, table/figure captions, or a clear sentence boundary where the previous fragment ends with terminal punctuation and the next fragment starts a new sentence.
7. When a float or table interrupts a sentence at a column/page boundary, keep the prose sentence continuous in the section draft, place the float near its first mention, and add a `% TODO` if hidden table/float text prevents reliable recovery.
8. If uncertain, keep the safer reconstruction and add:

```tex
% TODO: verify column/page transition on page <page_number>
```

#### Continuity Repair Pass for Existing Drafts

When the user reports that paragraphs were not merged across column/page transitions, or when final validation finds false blank paragraphs, run an explicit repair pass instead of making ad-hoc edits only.

1. Use the structured block map (`_section_source_blocks.json` or equivalent) and generated section drafts as the source of truth.
2. Scan section drafts for suspicious breaks, including:
   - a paragraph ending without terminal punctuation followed by a lowercase continuation;
   - a comma, semicolon, article, preposition, conjunction, or hyphen at the end of a paragraph followed by a continuation phrase;
   - a `% ===== Page N =====` comment inserted between two fragments of the same sentence;
   - a float/table inserted between two fragments where the prose should remain continuous.
3. Join only when the source page/column order and grammar both support the join. Do not join across headings, independent list items, captions, references, biographies, or true sentence boundaries.
4. If a page comment interrupts a continuous sentence, either move it to a safe paragraph boundary or remove it from that sentence while preserving page traceability in nearby comments/section metadata.
5. After repair, run the suspicious-break scan again and report both the number of joins performed and any unresolved transitions.
6. If multiple repair passes are run, preserve cumulative counts in `extraction_report.md` rather than overwriting earlier repair statistics with the final rerun count.

### 3. Section-by-Section Completeness Workflow

After rendering pages and before writing the final compile entry, perform a logical-section pass. This pass is mandatory for long, double-column, formula-dense, figure/table-dense, or template-based papers. Prefer section drafts by default unless the paper is very short and simple.

1. Build a section map from the PDF:
   - Front matter: title, authors, affiliations, abstract, keywords.
   - Main sections: `I`, `II`, `III`, etc., or equivalent headings.
   - Subsections: `A`, `B`, `C`, numbered subsections, or styled subheads.
   - Acknowledgment, references, appendices, author biographies, funding notes, and other end matter if present.
2. Create one section draft per logical unit:

```text
section_drafts/
  00_front_matter.tex
  01_introduction.tex
  02_<section-name>.tex
  ...
  references.tex
  author_biographies.tex
```

3. For every section draft, include a section header comment:

```tex
% ===== Section: <section title> =====
% Source pages: <page range>
% Expected subsections: <list or none>
% Expected equations: <list or none>
% Expected figures: <list or none>
% Expected tables: <list or none>
% Completeness status: complete / partial / needs manual check
```

4. Extract section text paragraph-by-paragraph, not as a summary. Preserve citations, math variables, abbreviations, and sentence order.
   - For multi-column PDFs, section text must be assembled from filtered text blocks and explicit heading boundaries, not from raw whole-page text.
   - Use main-section and subsection headings as hard structural boundaries. When a heading occurs mid-page, split the page at that heading instead of assigning the entire page to both adjacent sections.
   - Detect headings even when the PDF splits them across adjacent blocks or lines; combine adjacent heading fragments before deciding the section boundary.
   - If two logical sections share a page, classify each block by its position relative to the detected heading block and by column order; do not move all blocks on that page into the later section.
   - When a block visually appears before a new main-section heading, keep it in the previous section unless there is clear visual evidence that it belongs to the later section.
   - When a block visually appears after a new main-section heading, move it to the later section even if raw extraction order places it earlier.
   - Preserve body-like short paragraphs near formulas, figures, and tables; only exclude standalone equation fragments, pure labels, captions already represented as floats, and confirmed non-body noise.
   - Do not place figures, tables, or equations in bulk at the end of a section unless their exact reading-order position cannot be identified; if fallback placement is used, add a `% TODO` explaining why.
   - Captions and table labels should not remain as ordinary body paragraphs when a corresponding LaTeX float has been inserted.
   - After drafting each section, run a paragraph-boundary cleanup pass focused on column/page transitions: remove false blank paragraphs caused by PDF extraction, join split words, and merge sentences split by final-line column or page breaks when continuity is clear.
   - Preserve a paragraph break when the next block begins a genuinely new sentence, subsection, list item, float, reference, biography, or independent topic.
5. Insert figures, tables, and equations at their section-level reading-order positions. If precise placement is uncertain, place them near first mention and add a `% TODO`.
6. After writing a section draft, run a section completeness check:
   - All expected subsection headings appear in the draft.
   - All expected equations are present as editable LaTeX or explicitly retained as formula crops.
   - All figures/tables first mentioned in the section are present.
   - References, acknowledgments, appendices, and author biographies are included if present in the PDF.
   - Paragraph order follows the source reading order; for double-column pages compare against block coordinates.
   - If embedded text extraction is used, compare the draft against page text block counts and flag missing blocks.
   - For multi-column/template papers, run a block-level coverage check before final assembly: every body-like source block must be found in exactly the expected section draft, unless it is explicitly classified as heading, formula-only, caption/table label already represented by a float, reference/biography item, or non-body noise.
   - The coverage check must report both `missing` and `misplaced` body-like blocks. Do not treat a successful LaTeX compile as a content-completeness pass.
   - Normalize only for comparison, not for output: handle hyphenated line breaks, ligatures, Unicode dashes/math symbols, LaTeX commands, and common PDF extraction spacing variants.
   - If a paragraph, formula, table cell, reference line, or biography cannot be confidently reconstructed, keep the best attempt and add a `% TODO` instead of deleting it.
7. Assemble the final compile entry from section drafts only after each section is checked.
8. In `extraction_report.md`, add a `Section Completeness` table.

### 4. Anti-Summary Gate

Before accepting any section draft, reject summary-like replacement text. The output must not use phrases such as:

- `the paper discusses ...`
- `this section introduces ...`
- `the authors analyze ...`
- `the results show ...` as a substitute for full result paragraphs
- any short paragraph that compresses several source paragraphs into one unsupported sentence

If full reconstruction is uncertain, keep the recovered text, add `% TODO`, and cite the source page/crop. Do not delete or summarize the missing region.

## Text Coverage and Placement Validation

For long, multi-column, dense, or template-based papers, create and run a text coverage validator before final response. This validator may be a small project-local script when needed.

Validation requirements:

1. Use the structured source block map as the source of truth, not raw whole-page text.
2. Exclude only clearly non-body blocks:
   - page headers/footers/page numbers,
   - DOI/copyright/license/running-head text,
   - front-matter fields already mapped to template metadata,
   - standalone headings and subheadings,
   - pure equation fragments or equation numbers,
   - figure captions/table titles already represented by floats,
   - pure table-cell fragments when the table is represented as a crop or tabular,
   - reference/biography blocks only when they are validated against their own end-matter drafts.
3. Classify each remaining body-like block into the expected logical section using detected heading boundaries and page/column/bbox order.
4. Compare each body-like block against the generated section draft after comparison-only normalization.
5. Report:
   - checked body-like block count,
   - missing blocks,
   - misplaced blocks,
   - skipped block categories if useful.
6. If `missing` or `misplaced` is nonzero, repair the section drafts or the section map. Do not silence true positives by broadening skip filters.
7. Run a final-line continuity validation for multi-column/template papers:
   - scan generated section drafts for suspicious blank paragraph breaks where a line ending in a word, comma, semicolon, preposition, article, or hyphen is followed by a lowercase continuation;
   - scan for split-word artifacts such as `authen` + `ic`, `indus-` + `trial`, or `GAN` + `detection` separated by a false paragraph break;
   - compare suspicious joins against rendered pages or source block coordinates before changing prose;
   - record unresolved float-interrupted sentences as TODOs and in the report.
8. Only adjust validator filters when the source block is demonstrably non-body text or is represented elsewhere, and record the reason in the report.

Recommended normalization for comparison:

- convert ligatures (`ﬁ`, `ﬀ`, `ﬃ`, `ﬂ`),
- normalize Unicode dashes/minus signs,
- normalize common math symbols to comparable tokens,
- remove LaTeX commands and markup only for matching,
- join hyphenated line breaks such as `hardware- level`,
- collapse whitespace and punctuation differences,
- keep the original generated `.tex` text unchanged except for real extraction fixes.

## Text and Structure Conversion

Use these mappings:

- Paper title -> `\title{...}` or template-specific title command.
- Authors -> `\author{...}` or template-specific author block.
- Abstract -> template abstract environment.
- Keywords/index terms -> template keyword environment or keyword command.
- Level-1 headings -> `\section{...}`.
- Level-2 headings -> `\subsection{...}`.
- Level-3 headings -> `\subsubsection{...}`.
- Body paragraphs -> natural LaTeX paragraphs.
- Lists -> `enumerate` or `itemize` only when visually/list-structurally supported.

Preserve citations, bracket numbers, abbreviations, variable names, technical terms, and original punctuation as much as possible.

## Crop Boundary Quality Gate

For formulas, figures, and tables, do not rely on rough guessed crop boxes when block or visual coordinates can be derived.

1. Derive crop boxes from actual PDF coordinates whenever possible:
   - embedded text/image block bounding boxes,
   - rendered-page visual inspection,
   - neighboring caption/equation-number locations,
   - section source block positions.
2. Add small padding only to avoid clipping; avoid capturing unrelated neighboring content.
3. Inspect every crop visually before using it.
4. Re-crop if any of these are true:
   - formula symbols are clipped,
   - figure axes/legends/caption associations are missing,
   - table borders/headers/last rows are missing,
   - adjacent paragraph text is included enough to confuse identification,
   - caption belongs to a different figure/table.
5. Maintain `figures/_crop_manifest.json` with page, bbox, label, caption, crop basis, and confidence.
6. Record low-confidence crops in `extraction_report.md` and add `% TODO` near the corresponding LaTeX insertion.

## Complex Formula Handling With Formula Crops

All formulas must be attempted as editable LaTeX. Use a crop-and-recognize loop for complex formulas.

### Formula Crop Workflow

For each displayed formula:

1. Identify page number, column, equation number, and visual location.
2. Crop the formula region using the crop boundary quality gate.
3. Save the crop as `formula_crops/formula_p<page>_<eqindex>.png`.
4. Inspect the crop visually.
5. Write the best editable LaTeX reconstruction.
6. Compare the LaTeX against the crop symbol by symbol.
7. Add `% TODO` if any part remains uncertain.
8. Record crop path, equation number, page, bbox/location, uncertainty, and verification status in `extraction_report.md`.

### Formula Crop Repair and Anchor Validation

When formula crops are wrong, clipped, overly broad, or missing equation numbers, perform a dedicated formula re-cropping pass.

1. Rebuild formula crops from PDF coordinates, not from guessed vertical bands.
2. Use equation-number anchors and nearby math-font/text blocks to define local crop bounds. Detect anchors in all common positions:
   - standalone equation numbers such as `(12)`;
   - equation numbers at the end of a math/text block;
   - equation numbers at the beginning of a block, e.g. `(51) Both ...`, where the number may be embedded before prose.
3. For two-column papers, group candidates by page and column before pairing math blocks with equation-number anchors.
4. Use neighboring equation anchors to bound the vertical crop region so adjacent prose, captions, or following equations are not captured.
5. Prefer line-level math clustering over whole-block union when prior crops include prose:
   - start from the equation-number anchor;
   - expand upward/downward only through adjacent math-like lines;
   - stop expansion at ordinary prose, captions, headers/footers, large vertical gaps, or the next equation anchor;
   - use math fonts and math symbols as positive signals, but treat prose words such as `where`, `both`, `each`, `the`, `we`, `which`, and long grammatical sentences as stop signals even if they contain math variables.
6. After coordinate selection, run an image-ink trimming step on the candidate crop to remove extra whitespace and accidental neighboring text, then add only small padding to prevent clipping.
7. Validate crop dimensions after trimming. Flag or re-crop equations whose crop is suspiciously tall, suspiciously wide, or too short to contain the formula.
8. Maintain `formula_crops/_formula_manifest.json` with equation number, page, bbox, crop path, selected line/block basis, and confidence/status.
9. Validate the manifest against the expected equation-number range, for example equations `(1)`--`(72)`, and explicitly report missing numbers as a sorted list.
10. If a formula number was accidentally retained as normal prose after re-cropping, remove that stray number from the section draft while preserving the surrounding sentence.
11. Recompile after crop and draft repairs, because formula placeholders, graphics paths, or nearby floats may have changed.

### Formula LaTeX Rules

- Inline formulas -> `$...$`.
- One-line displayed formulas -> `equation`.
- Multi-line formulas -> `align` or `aligned` inside `equation`.
- Preserve equation numbers. Prefer `\tag{X}` when reconstructing from the original paper.
- For long formulas in narrow two-column templates, split with `align` rather than allowing severe overfull boxes.
- If the equation number cannot be safely embedded, add `% original equation number: (X)`.
- Never skip complex formulas. If unrecoverable, insert both best guess and image reference:

```tex
% TODO: verify formula on page <page_number>, location: <top/middle/bottom, left/right/full-width>
% Formula crop: formula_crops/formula_p<page>_<eqindex>.png
\begin{equation}
\text{[Uncertain formula, see formula crop]}
\end{equation}
```

### Symbol Checks

Actively verify confusing symbols:

- `l`, `1`, `I`
- `0`, `O`
- `x`, `\times`
- `v`, `\nu`
- `u`, `\mu`
- `p`, `\rho`
- `\phi`, `\varphi`
- `\epsilon`, `\varepsilon`
- `\sum`, `\Sigma`
- `T`, transpose `^T`, time index `(t)`
- bold vectors/matrices vs scalar variables
- hats, tildes, bars, dots, primes
- subscripts/superscripts and nested indices
- norms, expectations, probabilities, integrals, limits, sums
- piecewise braces and matrix dimensions

### Formula Verification Checklist

For every equation, verify:

- Equation number matches the PDF.
- Left-hand side exists and is complete.
- Right-hand side is complete.
- Fractions have correct numerator/denominator scope.
- Superscripts and subscripts bind to the correct symbol.
- Parentheses/brackets/braces are balanced.
- Alignment points in `align` are visually consistent.
- Vectors/matrices are marked consistently.
- All TODOs are reflected in `extraction_report.md`.

## Figure Extraction

For every figure, plot, block diagram, architecture diagram, photo, flowchart, or schematic:

1. Crop the original visual region using the crop boundary quality gate.
2. Save as `figures/fig_01.png`, `figures/fig_02.png`, etc.
3. Insert at the corresponding reading-order location:

```tex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.95\linewidth]{figures/fig_01.png}
    \caption{<original caption>}
    \label{fig:fig_01}
\end{figure}
```

4. Preserve original figure number and caption text.
5. If readable, add a concise visual-content comment.
6. If association or boundary is uncertain, add `% TODO: verify figure-caption association on page <page_number>`.

## Table Extraction

For tables:

1. Attempt editable LaTeX `table` + `tabular` first for simple tables.
2. Prefer `booktabs` style.
3. Use `??` for uncertain cells and add a TODO.
4. For dense tables, checkmark/cross tables, multi-row tables, or visually complex tables, retain a screenshot and optionally provide a partial editable version only if reliable:

```tex
\begin{table}[htbp]
    \centering
    \caption{<original table caption>}
    \label{tab:table_01}
    % TODO: verify table content on page <page_number>; retained as screenshot because editable reconstruction is uncertain.
    \includegraphics[width=0.95\linewidth]{figures/table_01.png}
\end{table}
```

5. For tables converted to editable `tabular`, still keep the table crop as a verification asset when feasible.
6. Record all screenshot-only or partially editable tables in `extraction_report.md`.
7. When a table interrupts prose in the source page, do not splice table text into the prose. Place the table as a float and reconnect the prose before/after it only when the sentence continuation is visually clear.

## Algorithms and Pseudocode

If the paper contains algorithms:

- Prefer `algorithm` + `algorithmic` if line order is clear.
- Preserve algorithm title, inputs, outputs, numbered steps, loops, and conditions.
- If line order is uncertain, reconstruct best effort and add `% TODO: verify Algorithm <number> on page <page_number>; line order reconstructed from PDF.`

## References and End Matter

Convert references to:

```tex
\begin{thebibliography}{99}
\bibitem{ref1} ...
\bibitem{ref2} ...
\end{thebibliography}
```

Rules:

- Preserve reference numbers and full entries.
- Do not merge, delete, reorder, or rewrite references.
- Fix obvious line wrapping only when unambiguous.
- If a reference spans columns/pages and joining is uncertain, add `% TODO: verify reference on page <page_number>`.
- If the template requires BibTeX/BibLaTeX, either adapt to the template or record the limitation and keep `thebibliography` if no `.bib` is provided.
- Include acknowledgments, funding statements, appendices, supplementary notes, and author biographies if visible in the PDF.
- If author portraits are not separately extracted, record this in `extraction_report.md` rather than omitting biography text.

## Extraction Report

Every paper must include `extraction_report.md`:

```md
# Extraction Report

## Source PDF
<file_name>

## Basic Information
- Page count:
- Layout:
- Formula density:
- Figure count:
- Table count:
- Template used:
- Compile entry:
- Visible title / filename mismatch:

## Output Files
- LaTeX compile entry:
- Section drafts directory:
- Figures directory:
- Page images directory:
- Formula crops directory:

## Section Completeness
| Section | Source pages | Status | Missing/uncertain items |
|---|---:|---|---|

## Crop Manifest Notes
- Crop manifest:
- Low-confidence crops:

## Formula Verification
- Page X, equation (Y), crop path, location/bbox, status: verified/uncertain, reason

## Uncertain Equations
- Page X, left/right/full-width column, top/middle/bottom: reason

## Uncertain Figures
- Page X: reason

## Uncertain Tables
- Page X: reason

## Reading Order Issues
- Page X: reason

## Template Adaptation Notes
- Packages preserved/changed:
- Template-specific fields used:
- Conflicts or unresolved items:

## Compilation Check
- Engine:
- Command:
- Result:
- Fatal errors:
- Warnings requiring attention:
- Output PDF:

## Final Consistency Check
- Missing expected sections:
- Missing expected equations:
- Missing expected figures/tables:
- Missing graphics/crops:
- Text coverage result: checked body-like blocks, missing blocks, misplaced blocks
- Column/page final-line continuity pass: performed/not performed; fixed joins; unresolved transitions
- Formula crop validation: expected equation range; crop manifest count; missing equation numbers; low-confidence crops
- TODO count:

## Repair Pass
- Formula crop repair actions and validation result:
- Paragraph continuity repair actions, including cumulative join counts and removed/moved page comments:
- Targeted cleanup items, such as stray equation-number fragments or float-interrupted prose:
- Recompile result after repair:

## Recommended Manual Checks
- List pages and items that should be manually verified.
```

## Final Verification After Writing

After generating outputs, perform a local consistency check:

- Required files/directories exist:
  - short compile entry `.tex`, e.g. `paperN.tex` or `main.tex`,
  - `extraction_report.md`,
  - `pages/`,
  - `figures/`,
  - `formula_crops/` if formula crops are referenced,
  - `section_drafts/` when used.
- Page image count equals PDF page count.
- Every source page is covered by page comments or section source-page comments.
- Every expected section/subsection heading appears or is explicitly listed as missing/uncertain.
- Every expected equation number appears as editable LaTeX or is explicitly retained as a crop with TODO.
- Every expected figure/table label appears in LaTeX or is explicitly listed as missing/uncertain.
- Figure/table files referenced by `\includegraphics` exist.
- Formula crop files referenced in comments/report exist.
- All TODOs in `.tex` are represented in `extraction_report.md`.
- No section draft contains summary placeholders that replace source paragraphs.
- Structural integrity checks for multi-column/template papers:
  - Introduction does not contain duplicated title, author list, abstract, keywords, manuscript notes, DOI, copyright/license text, or page headers/footers.
  - No obvious horizontal column interleaving remains, such as unrelated sentence fragments from left and right columns joined on the same line.
  - Main sections start at their detected heading blocks; adjacent sections sharing one page are split at the heading block, not by whole-page assignment.
  - Split headings across PDF blocks are detected and do not leave orphan heading fragments as prose.
  - Body-like blocks immediately before a later main-section heading remain in the previous section unless visual order proves otherwise.
  - Body-like blocks after a later main-section heading are assigned to that later section even if raw extraction order is misleading.
  - Figure captions/table titles are represented by floats and are not duplicated as normal prose.
  - Floats/equations appear near first mention or include a TODO explaining fallback placement.
  - Final-line column/page transitions have been checked: no obvious false paragraph break remains where a sentence continues into the next column/page, and no line-break hyphen artifact remains as a broken word.
  - Suspicious split-boundary patterns have been scanned after any repair pass, including standalone equation-number fragments, equation numbers accidentally starting prose, and page comments inserted between lowercase sentence continuations.
  - Suspicious float-interrupted prose near tables/figures has either been repaired or marked with a TODO and recorded in `extraction_report.md`.
  - A block-level text coverage report exists for long/multi-column/template papers and shows no unresolved missing or misplaced body-like blocks; any exclusions are justified as non-body or represented elsewhere.
- Basic LaTeX syntax sanity:
  - `\begin{document}` and `\end{document}` exist in the compile entry,
  - environments are balanced as far as practical,
  - braces in generated commands are not obviously broken,
  - graphics paths are relative to the compile entry.

## Compilation Verification

When a local TeX engine is available, compile the short entry after writing. Compilation is mandatory for template-based conversions unless the user explicitly says not to compile.

Recommended command pattern:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error paperN.tex
```

Rules:

1. Compile from the output directory, not from a parent directory with long paths in the command argument.
2. Compile the short entry (`paperN.tex` or `main.tex`), not the long paper-title filename.
3. If cross-references, citations, or labels require reruns, run the same engine again when practical.
4. If compilation fails, fix directly caused LaTeX errors when feasible:
   - missing graphics paths,
   - unbalanced environments,
   - broken math delimiters,
   - unsupported template/package conflicts,
   - overlong formulas that need `align` splitting.
5. Do not hide failures. Record fatal errors, unresolved warnings, overfull/underfull boxes that matter, and output PDF existence in `extraction_report.md`.
6. A successful compile does not prove extraction completeness; still run the section and expected-item checks.

## Subagent Instructions for Parallel Work

When using subagents:

- Assign exactly one PDF per subagent.
- Include the exact filename prefix or full PDF path.
- Tell the subagent not to process other PDFs.
- Require the same output structure, section-by-section workflow, crop manifest, compile entry, and report.
- Require a concise return summary:
  - PDF filename,
  - page count,
  - output directory,
  - compile entry,
  - number of page images,
  - number of figure/table/formula crops,
  - compilation result,
  - main TODOs.

## Response to User

Final response should be concise and include clickable file links for generated files/directories when available:

- Output directory,
- main compile entry `.tex`,
- `extraction_report.md`,
- `section_drafts/`,
- `pages/`,
- `figures/`,
- compilation result,
- counts and major TODOs.

Do not paste the whole paper into the chat unless explicitly requested.

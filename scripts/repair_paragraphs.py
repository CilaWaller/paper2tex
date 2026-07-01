"""Stage 3 tool: repair cross-column / cross-page paragraph continuity.

Generalizes the paragraph continuity repair. It scans section-draft ``.tex``
files for false paragraph breaks introduced by two-column/page-boundary PDF
extraction and joins them only when both reading order and grammar support the
join. Page-traceability comments (``% ===== Page N =====``) that sit inside a
continuous sentence are preserved by moving them ahead of the joined sentence.

Join signals (any one triggers a join with the next prose line):
- previous line ends without terminal punctuation and next starts lowercase;
- previous line ends with a comma or a line-break hyphen;
- next line starts with a continuation word (and/or/of/to/the/that/...);
- previous line ends with an article/preposition/conjunction.

It never joins across headings, ``\\begin``/``\\end`` environments, list
items, blank-line-separated true sentence boundaries, or lines ending in
terminal punctuation.

Line-break hyphens (``indus-`` + ``trial``) are de-hyphenated into a single
word. Genuine compound hyphens are protected: when the fragment before the
hyphen is a common compound-forming prefix (``anti``, ``non``, ``self``,
``deep``, ...), the hyphen is kept and only the line break is removed, so
``anti-`` + ``spoofing`` becomes ``anti-spoofing`` rather than ``antispoofing``.

Usage:
    # Repair every section draft in place and print counts:
    python repair_paragraphs.py --sections "<out>/section_drafts"

    # Only report suspicious breaks without editing (safe preview):
    python repair_paragraphs.py --sections "<out>/section_drafts" --dry-run

    # Restrict to specific files:
    python repair_paragraphs.py --files a.tex b.tex

    # Also write the findings JSON to a file for the extraction report:
    python repair_paragraphs.py --sections "<out>/section_drafts" --report "<out>/_paragraph_repair.json"
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PAGE_COMMENT = re.compile(r"^% ===== Page \d+ =====")
TERM = re.compile(r"[.!?]['\")\]}]*$")
CONTINUATION_START = re.compile(
    r"^(and|or|of|to|in|for|with|from|by|as|at|the|that|which|while|where|under|"
    r"given|than|through|between|into|using|is|are|was|were|be|being|a|an|on|"
    r"after|before|during|when|if|so|such|then|therefore|hence|respectively)\b",
    re.I,
)
TRAILING_FUNCTION_WORD = re.compile(
    r"\b(the|a|an|of|to|in|with|and|or|as|is|are|was|were|be|being|by|from|for|"
    r"on|at|under|than|through|between|into|using|each|all|any|their|its|this|"
    r"that|these|those)$",
    re.I,
)


ENV_BEGIN = re.compile(r"\\begin\{(equation|align|aligned|gather|multline|cases|array|matrix|bmatrix|pmatrix|split)\*?\}")
ENV_END = re.compile(r"\\end\{(equation|align|aligned|gather|multline|cases|array|matrix|bmatrix|pmatrix|split)\*?\}")


def is_page_comment(s: str) -> bool:
    return bool(PAGE_COMMENT.match(s.strip()))


def is_prose(s: str) -> bool:
    s = s.strip()
    if not s or s.startswith("%") or s.startswith("\\") or s in {"}", "{"}:
        return False
    # Lines that carry math markup are not running prose even if they start
    # with an alphanumeric token (e.g. inside an aligned environment).
    if s.endswith("\\\\") or "&" in s or "\\\\" in s:
        return False
    return True


def should_join(prev: str, nxt: str) -> bool:
    p, n = prev.strip(), nxt.strip()
    if not p or not n:
        return False
    if TERM.search(p):
        return False
    if p.endswith((":", ";")):
        return False
    if p.endswith((",", "-")):
        return True
    if CONTINUATION_START.match(n):
        return True
    if re.match(r"^[a-z\[]", n):
        return True
    if TRAILING_FUNCTION_WORD.search(p):
        return True
    return False


# Prefixes/first words that normally keep their hyphen in a real compound word.
# When the token right before a line-break hyphen is one of these, keep the
# hyphen and only drop the line break, e.g. "anti- spoofing" -> "anti-spoofing".
COMPOUND_PREFIX = frozenset("""
anti non self semi multi cross inter intra pre post sub super co re pseudo quasi
deep high low real long short large small well first second third state open
closed hardware software model data noise signal code phase time frequency left
right top bottom two three end
""".split())


def dehyphenate(text: str) -> str:
    """Join line-break hyphens, but keep hyphens in genuine compound words.

    ``indus- trial`` -> ``industrial`` (line-break hyphen removed), while
    ``anti- spoofing`` -> ``anti-spoofing`` (compound hyphen kept).
    """
    def _join(m: re.Match) -> str:
        before, after = m.group(1), m.group(2)
        if before.lower() in COMPOUND_PREFIX:
            return f"{before}-{after}"
        return f"{before}{after}"

    return re.sub(r"(\w+)-\s+([a-z])", _join, text)


def process_file(path: Path, dry_run: bool):
    lines = path.read_text(encoding="utf-8").splitlines()
    out, findings = [], []
    joins = moved_comments = 0
    env_depth = 0
    i, n = 0, len(lines)
    while i < n:
        raw = lines[i]
        env_depth += len(ENV_BEGIN.findall(raw)) - len(ENV_END.findall(raw))
        if env_depth > 0 or not is_prose(raw.strip()):
            out.append(raw)
            i += 1
            continue
        cur = lines[i].strip()
        cur_lineno = i + 1
        while True:
            j = i + 1
            sep = []
            while j < n and (lines[j].strip() == "" or is_page_comment(lines[j])):
                sep.append(lines[j].strip())
                j += 1
            if j < n and is_prose(lines[j]) and should_join(cur, lines[j]):
                comments = [s for s in sep if is_page_comment(s)]
                findings.append({"file": path.name, "line": cur_lineno,
                                 "prev": cur[-60:], "next": lines[j].strip()[:60]})
                if dry_run:
                    out.append(cur)
                    out.extend(sep)
                    i = j
                    break
                if comments:
                    out.append(dehyphenate(cur))
                    out.extend(comments)
                    moved_comments += len(comments)
                    cur = lines[j].strip()
                else:
                    cur = dehyphenate(cur + " " + lines[j].strip())
                joins += 1
                i = j
                continue
            out.append(dehyphenate(cur) if not dry_run else cur)
            out.extend(sep)
            i = j
            break

    if not dry_run:
        path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return {"joins": joins, "moved_page_comments": moved_comments, "findings": findings}


def main() -> None:
    ap = argparse.ArgumentParser(description="Repair cross-column/page paragraph continuity.")
    ap.add_argument("--sections", help="Directory of section-draft .tex files.")
    ap.add_argument("--files", nargs="*", help="Explicit .tex files to process.")
    ap.add_argument("--dry-run", action="store_true", help="Report suspicious breaks only.")
    ap.add_argument("--report", help="Optional path to write the findings JSON for the extraction report.")
    args = ap.parse_args()

    targets = []
    if args.sections:
        targets.extend(sorted(Path(args.sections).glob("*.tex")))
    if args.files:
        targets.extend(Path(f) for f in args.files)
    if not targets:
        ap.error("provide --sections and/or --files")

    total = {"joins": 0, "moved_page_comments": 0, "files": [], "findings": []}
    for path in targets:
        r = process_file(path, args.dry_run)
        total["joins"] += r["joins"]
        total["moved_page_comments"] += r["moved_page_comments"]
        total["findings"].extend(r["findings"])
        total["files"].append({"file": path.name, "joins": r["joins"],
                               "moved_page_comments": r["moved_page_comments"]})

    total["dry_run"] = args.dry_run
    if args.report:
        Path(args.report).write_text(
            json.dumps(total, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(total, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

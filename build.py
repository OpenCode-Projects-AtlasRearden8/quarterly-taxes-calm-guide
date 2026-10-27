#!/usr/bin/env python3
"""Build the Quarterly Taxes Calm Guide as a static HTML site.

Local-first, zero dependencies: Python 3 standard library only.
Reads markdown from docs/ and writes HTML pages into site/ (or --out DIR).

    python3 build.py            # build into ./site/
    python3 build.py --out DIR  # build elsewhere (the tests use this)
"""

from __future__ import annotations

import argparse
import html
import posixpath
import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
DOCS = BASE / "docs"
ASSETS = BASE / "assets"

SITE_NAME = "Quarterly Taxes Calm Guide"
TAGLINE = "education only, never tax advice"

# Reading order for the sidebar and the Prev / Next pager.
PAGE_ORDER = [
    "00-start-here.md",
    "01-estimated-tax-rhythm.md",
    "02-set-aside-percentages.md",
    "03-receipts-what-to-keep.md",
    "04-1099s-decoded.md",
    "05-quarterly-ritual.md",
    "06-when-to-call-a-professional.md",
    "worksheets/due-date-calendar.md",
    "worksheets/panic-meter.md",
    "glossary.md",
]

NAV_GROUPS = [
    ("Start here", PAGE_ORDER[:1]),
    ("The basics", PAGE_ORDER[1:7]),
    ("Worksheets", PAGE_ORDER[7:9]),
    ("Reference", PAGE_ORDER[9:]),
]

FOOTER_HTML = (
    '<div class="doc-footer">'
    "<p><strong>Education only.</strong> This guide explains paperwork concepts in plain "
    "English. It is not tax, legal, accounting, or financial advice, it is not "
    "personalized to your situation, and it is not affiliated with or endorsed by the "
    "IRS or any state tax agency. Rules and dates change and differ by person: always "
    "verify current details with the official IRS and your state tax agency, and talk "
    "to a qualified professional before acting on anything here.</p>"
    "<p class=\"colophon\">Copyright (c) 2026 Asdale Dynamics, LLC &#183; MIT License "
    "&#183; built locally with <code>build.py</code> &#183; companion guides: "
    "<code>llc-first-year-handbook</code>, <code>cashflow-simple-ledger</code></p>"
    "</div>"
)


def relmd_to_relhtml(rel_md: str) -> str:
    """docs/01-estimated-tax-rhythm.md -> 01-estimated-tax-rhythm.html (site-relative)."""
    stem = posixpath.splitext(rel_md)[0]
    if stem == "00-start-here":
        stem = "index"
    return stem + ".html"


def _slugify(text: str) -> str:
    text = re.sub(r"[*`_]", "", text).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# --------------------------------------------------------------------------
# Markdown -> HTML (the subset our docs actually use)
# --------------------------------------------------------------------------

def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _inline_link, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    return text


def _inline_link(match: re.Match) -> str:
    label = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", match.group(1))
    label = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", label)
    return f'<a href="{match.group(2)}">{label}</a>'


def _list_item(item: str) -> tuple[str, str]:
    """Return (css_class, li_html) for one list item line."""
    box = re.match(r"\[([ xX])\]\s+(.*)$", item)
    if box:
        done = box.group(1).strip() != ""
        marker = '<span class="box done"></span>' if done else '<span class="box"></span>'
        return "job", marker + _inline(box.group(2))
    return "", _inline(item)


def _is_table_start(lines: list[str], idx: int) -> bool:
    if idx + 1 >= len(lines):
        return False
    second = lines[idx + 1].strip()
    if not (second.startswith("|") and second.endswith("|")):
        return False
    cells = [c.strip() for c in second.strip("|").split("|")]
    return all(re.fullmatch(r":?-+:?", c) for c in cells)


def markdown_to_html(md_text: str) -> str:
    lines = md_text.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    i = 0

    def flush_paragraph() -> None:
        if paragraph:
            joined = " ".join(p.strip() for p in paragraph)
            out.append(f"<p>{_inline(joined)}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            i += 1
            code: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            quoted: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quoted.append(lines[i].strip().lstrip(">").strip())
                i += 1
            body = _inline(" ".join(part for part in quoted if part))
            out.append(f"<blockquote><p>{body}</p></blockquote>")
            continue

        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            flush_paragraph()
            out.append("<hr>")
            i += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            text = heading.group(2)
            out.append(f'<h{level} id="{_slugify(text)}">{_inline(text)}</h{level}>')
            i += 1
            continue

        item = re.match(r"^(\s*)([-*+]|(\d+)\.)\s+(.*)$", line)
        if item:
            flush_paragraph()
            ordered = line.lstrip()[0].isdigit()
            items_raw: list[str] = []
            while i < len(lines):
                m = re.match(r"^(\s*)([-*+]|(\d+)\.)\s+(.*)$", lines[i])
                if m:
                    is_ordered = m.group(2)[0] not in "-*+"
                    ordered = ordered or is_ordered
                    items_raw.append(m.group(4))
                    i += 1
                    continue
                if lines[i].strip() and lines[i].startswith((" ", "\t")):
                    if items_raw:
                        items_raw[-1] += " " + lines[i].strip()
                        i += 1
                        continue
                break
            items = [_list_item(raw) for raw in items_raw]
            tag = "ol" if ordered else "ul"
            inner = "".join(
                f'<li class="{cls}">{body}</li>' if cls else f"<li>{body}</li>"
                for cls, body in items
            )
            out.append(f"<{tag}>{inner}</{tag}>")
            continue

        if stripped.startswith("|") and _is_table_start(lines, i):
            flush_paragraph()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head = "".join(f"<th>{_inline(c)}</th>" for c in header)
            body = "".join(
                "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>"
                for row in rows
            )
            out.append(
                '<div class="tablewrap"><table><thead><tr>'
                f"{head}</tr></thead><tbody>{body}</tbody></table></div>"
            )
            continue

        paragraph.append(line)
        i += 1

    flush_paragraph()
    return "\n".join(out)


# --------------------------------------------------------------------------
# Link rewriting: docs-relative markdown hrefs -> site-relative HTML hrefs
# --------------------------------------------------------------------------

def _rewrite_md_link(link: str, current_dir: str) -> str:
    if link.startswith(("http://", "https://", "mailto:", "#")):
        return link
    anchor = ""
    if "#" in link:
        link, anchor = link.split("#", 1)
        anchor = "#" + anchor
    if not link.endswith(".md"):
        return link + anchor
    # Links inside markdown are relative to the source page; resolve them in
    # docs-space first, then convert and make them relative to the output dir.
    norm_md = posixpath.normpath(posixpath.join(current_dir, link))
    target_html = relmd_to_relhtml(norm_md)
    output = posixpath.relpath(target_html, current_dir or ".")
    return posixpath.normpath(output) + anchor


def _rewrite_doc_links(html_doc: str, current_dir: str) -> str:
    def sub(match: re.Match) -> str:
        return f'href="{_rewrite_md_link(match.group(1), current_dir)}"'

    return re.sub(r'href="([^"]+)"', sub, html_doc)


# --------------------------------------------------------------------------
# Page assembly
# --------------------------------------------------------------------------

def _page_title(rel_md: str) -> str:
    path = DOCS / rel_md
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#\s+(.*?)\s*$", raw)
        if m:
            return m.group(1)
    raise ValueError(f"No H1 title found in {rel_md}")


def _nav_link(nav_rel: str, current_rel: str) -> str:
    from_dir = posixpath.dirname(relmd_to_relhtml(current_rel))
    target = relmd_to_relhtml(nav_rel)
    return posixpath.normpath(posixpath.relpath(target, from_dir or "."))


def _build_nav(current_rel: str) -> str:
    chunks: list[str] = []
    for group_name, pages in NAV_GROUPS:
        items = "".join(
            f'<li><a class="active" href="{_nav_link(p, current_rel)}">{_page_title(p)}</a></li>'
            if p == current_rel
            else f'<li><a href="{_nav_link(p, current_rel)}">{_page_title(p)}</a></li>'
            for p in pages
        )
        chunks.append(
            f'<div class="nav-group"><div class="nav-heading">{group_name}</div>'
            f"<ul>{items}</ul></div>"
        )
    return "\n".join(chunks)


def _pager(current_rel: str) -> str:
    idx = PAGE_ORDER.index(current_rel)
    parts: list[str] = []
    if idx > 0:
        prev = PAGE_ORDER[idx - 1]
        parts.append(
            f'<a class="pager-link" href="{_nav_link(prev, current_rel)}">Back: '
            + _page_title(prev)
            + "</a>"
        )
    if idx < len(PAGE_ORDER) - 1:
        nxt = PAGE_ORDER[idx + 1]
        parts.append(
            f'<a class="pager-link pager-next" href="{_nav_link(nxt, current_rel)}">Next: '
            + _page_title(nxt)
            + "</a>"
        )
    return '<div class="pager">' + "".join(parts) + "</div>"


def _render_page(rel_md: str) -> str:
    md_text = (DOCS / rel_md).read_text(encoding="utf-8")
    title = _page_title(rel_md)
    body = markdown_to_html(md_text)
    current_dir = posixpath.dirname(relmd_to_relhtml(rel_md))
    body = _rewrite_doc_links(body, current_dir)
    style_href = posixpath.normpath(posixpath.relpath("styles.css", current_dir or "."))
    nav = _build_nav(rel_md)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="description" content="A calm, education-only paperwork manual for US '
        'self-employed folks and LLC owners. Never tax advice.">\n'
        f"<title>{html.escape(title)} &#183; {SITE_NAME}</title>\n"
        f'<link rel="stylesheet" href="{style_href}">\n'
        "</head>\n"
        "<body>\n"
        '<header class="topbar">\n'
        '<span class="brand">Quarterly Taxes Calm Guide</span>\n'
        f'<span class="tagline">{TAGLINE}</span>\n'
        "</header>\n"
        '<div class="layout">\n'
        '<nav class="sidebar" aria-label="Guide contents">\n'
        f"{nav}\n"
        "</nav>\n"
        '<main class="content">\n'
        f"{body}\n"
        + _pager(rel_md)
        + FOOTER_HTML
        + "</main>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def build(out_dir: Path) -> None:
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "worksheets").mkdir(parents=True)
    out_dir.joinpath("styles.css").write_text(
        (ASSETS / "styles.css").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for rel_md in PAGE_ORDER:
        src = DOCS / rel_md
        if not src.exists():
            raise FileNotFoundError(f"Missing docs source: {rel_md}")
        out_rel = relmd_to_relhtml(rel_md)
        out_path = out_dir / out_rel
        out_path.write_text(_render_page(rel_md), encoding="utf-8")

    # Sanity: every internal href should point at a real generated file.
    for page in out_dir.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:", "#", "styles.css")):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            if not target.exists():
                raise ValueError(
                    f"Broken link {href!r} in {page.relative_to(out_dir)} "
                    f"(resolves to {target})"
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the static site.")
    parser.add_argument("--out", default=str(BASE / "site"), help="output directory")
    args = parser.parse_args(argv)
    build(Path(args.out))
    print(f"Built {len(PAGE_ORDER)} pages into {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

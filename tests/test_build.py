#!/usr/bin/env python3
"""Tests for the Quarterly Taxes Calm Guide build.

Everything imports build.py as a module and drives it against the real
docs/, building into a temp directory (never clobbering the repo's site/).
Run with:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import html
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"


def _load_build_module():
    spec = importlib.util.spec_from_file_location("guide_build", REPO / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUILD = _load_build_module()

EXPECTED_PAGES = [
    "index.html",
    "01-estimated-tax-rhythm.html",
    "02-set-aside-percentages.html",
    "03-receipts-what-to-keep.html",
    "04-1099s-decoded.html",
    "05-quarterly-ritual.html",
    "06-when-to-call-a-professional.html",
    "worksheets/due-date-calendar.html",
    "worksheets/panic-meter.html",
    "glossary.html",
]

DISCLAIMER_SNIPPETS = (
    "<strong>Education only.</strong>",
    "not tax, legal, accounting, or financial advice",
    "Copyright (c) 2026 Asdale Dynamics, LLC",
)


class BuildSiteTest(unittest.TestCase):
    """One shared build in a temp dir; every test reads from it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="qtcg-tests-")
        cls.site = Path(cls.tmp.name) / "site"
        BUILD.build(cls.site)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _page(self, name: str) -> str:
        return (self.site / name).read_text(encoding="utf-8")

    # -- structure ------------------------------------------------------

    def test_all_expected_pages_exist(self):
        for name in EXPECTED_PAGES:
            with self.subTest(page=name):
                self.assertTrue((self.site / name).exists(), f"missing {name}")

    def test_styles_copied(self):
        self.assertTrue((self.site / "styles.css").exists())
        self.assertIn("--accent", (self.site / "styles.css").read_text(encoding="utf-8"))

    def test_every_page_has_disclaimer_footer(self):
        for name in EXPECTED_PAGES:
            html_doc = self._page(name)
            with self.subTest(page=name):
                for snippet in DISCLAIMER_SNIPPETS:
                    self.assertIn(snippet, html_doc)

    def test_every_page_has_nav_with_glossary_and_home(self):
        for name in EXPECTED_PAGES:
            html_doc = self._page(name)
            with self.subTest(page=name):
                self.assertTrue(
                    re.search(r'href="(\.\./)?glossary\.html"', html_doc),
                    f"{name}: no glossary nav link",
                )
                self.assertTrue(
                    re.search(r'href="(\.\./)?index\.html"', html_doc),
                    f"{name}: no home nav link",
                )

    def test_titles_match_source_h1(self):
        for name in BUILD.PAGE_ORDER:
            title = BUILD._page_title(name)
            html_doc = self._page(BUILD.relmd_to_relhtml(name))
            with self.subTest(page=name, title=title):
                self.assertIn(html.escape(title), html_doc)

    # -- links ----------------------------------------------------------

    def test_generated_internal_links_resolve(self):
        for page in self.site.rglob("*.html"):
            html_doc = page.read_text(encoding="utf-8")
            for href in re.findall(r'href="([^"]+)"', html_doc):
                if href.startswith(("http://", "https://", "mailto:")):
                    continue
                target = (page.parent / href.split("#")[0]).resolve()
                with self.subTest(page=str(page.relative_to(self.site)), href=href):
                    self.assertTrue(
                        target.exists(),
                        f"broken href {href!r} in {page.relative_to(self.site)}",
                    )

    def test_same_page_anchors_resolve(self):
        for page in self.site.rglob("*.html"):
            html_doc = page.read_text(encoding="utf-8")
            ids = set(re.findall(r'id="([^"]+)"', html_doc))
            for anchor in re.findall(r'href="#([^"]+)"', html_doc):
                with self.subTest(page=str(page.relative_to(self.site)), anchor=anchor):
                    self.assertIn(anchor, ids)

    def test_markdown_crosslinks_point_at_real_docs(self):
        for md in DOCS.rglob("*.md"):
            text = md.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)\s]+)\)", text):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                path_part = target.split("#", 1)[0]
                if not path_part:
                    continue  # same-page anchor, checked in generated HTML
                resolved = (md.parent / path_part).resolve()
                with self.subTest(source=str(md.relative_to(DOCS)), link=target):
                    self.assertTrue(
                        resolved.exists() and resolved.is_file(),
                        f"{md.relative_to(DOCS)} links to missing {target!r}",
                    )

    def test_crossfile_glossary_anchors_resolve(self):
        for md in DOCS.rglob("*.md"):
            if md.name == "glossary.md":
                continue
            text = md.read_text(encoding="utf-8")
            for target in re.findall(r"\]\((glossary\.md#[^)\s]+)\)", text):
                anchor = target.split("#", 1)[1]
                with self.subTest(source=str(md.relative_to(DOCS)), anchor=anchor):
                    self.assertIn(anchor, self._glossary_ids)

    @property
    def _glossary_ids(self):
        if not hasattr(self, "_glossary_ids_cache"):
            html_doc = self._page("glossary.html")
            self._glossary_ids_cache = set(re.findall(r'id="([^"]+)"', html_doc))
        return self._glossary_ids_cache

    # -- content guarantees ---------------------------------------------

    def test_no_number_promises_language(self):
        """The guide must never promise a specific savings/owed amount."""
        forbidden = [
            r"you (will|should) owe \$?\d",
            r"guarentee",
            r"guaranteed refund",
            r"you will get \$",
            r"exactly \$?\d+% ",
        ]
        for md in DOCS.rglob("*.md"):
            text = md.read_text(encoding="utf-8").lower()
            for pattern in forbidden:
                with self.subTest(source=str(md.relative_to(DOCS)), pattern=pattern):
                    self.assertIsNone(
                        re.search(pattern, text),
                        f"{md.relative_to(DOCS)} contains forbidden promise language",
                    )

    def test_education_disclaimer_present_in_every_doc(self):
        for md in DOCS.rglob("*.md"):
            text = md.read_text(encoding="utf-8").lower()
            with self.subTest(source=str(md.relative_to(DOCS))):
                self.assertIn(
                    "education only",
                    text,
                    f"{md.relative_to(DOCS)} lacks the education-only banner",
                )

    def test_glossary_has_minimum_terms(self):
        html_doc = self._page("glossary.html")
        self.assertGreaterEqual(html_doc.count("<h2"), 30)

    def test_workspace_fillins_present_on_calendar_worksheet(self):
        html_doc = self._page("worksheets/due-date-calendar.html")
        for phrase in ("I verified this on", "Amount I paid", "Confirmation #"):
            self.assertIn(phrase, html_doc)

    def test_panic_meter_has_all_five_levels(self):
        html_doc = self._page("worksheets/panic-meter.html")
        for level in range(1, 6):
            self.assertIn(f"Level {level}:", html_doc)

    # -- hygiene ---------------------------------------------------------

    def test_no_secrets_or_keys_in_tracked_text_files(self):
        patterns = [
            re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[\"'][A-Za-z0-9_\-]{8,}[\"']"),
            re.compile(r"sk-[A-Za-z0-9]{20,}"),
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"ghp_[A-Za-z0-9]{30,}"),
            re.compile(r"-----BEGIN [A-Z ]* PRIVATE KEY-----"),
        ]
        for path in sorted(REPO.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in {".md", ".py", ".sh", ".css", ".html", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                with self.subTest(file=str(path.relative_to(REPO))):
                    self.assertIsNone(pattern.search(text), f"possible secret in {path}")

    def test_license_has_exact_copyright_line(self):
        text = (REPO / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Asdale Dynamics, LLC", text)
        self.assertIn("MIT License", text)

    def test_readme_credits_and_links(self):
        text = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("Asdale Dynamics, LLC", text)
        self.assertIn("MIT", text)

    # -- build behaviors ---------------------------------------------------

    def test_cli_build_works(self):
        with tempfile.TemporaryDirectory() as out:
            proc = subprocess.run(
                [sys.executable, str(REPO / "build.py"), "--out", out],
                cwd=REPO,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn("Built 10 pages", proc.stdout)

    def test_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            BUILD.build(Path(tmp1) / "a")
            BUILD.build(Path(tmp2) / "b")
            for name in EXPECTED_PAGES + ["styles.css"]:
                self.assertEqual(
                    (Path(tmp1) / "a" / name).read_bytes(),
                    (Path(tmp2) / "b" / name).read_bytes(),
                    f"non-deterministic output for {name}",
                )


class MarkdownConverterTest(unittest.TestCase):
    def setUp(self):
        self.html_out = lambda md: BUILD.markdown_to_html(md)

    def test_unordered_list_simple(self):
        got = BUILD.markdown_to_html("- one\n- two")
        self.assertIn("<ul><li>one</li><li>two</li></ul>", got)

    def test_ordered_list(self):
        got = BUILD.markdown_to_html("1. one\n2. two")
        self.assertIn("<ol><li>one</li><li>two</li></ol>", got)

    def test_bullet_do_not_require_dot(self):
        got = BUILD.markdown_to_html("- a bullet")
        self.assertIn("<ul><li>a bullet</li></ul>", got)

    def test_wrapped_item_keeps_inline_formatting(self):
        got = BUILD.markdown_to_html("- and anyone likes **bold even while wrapped\n  across lines**")
        self.assertIn("<strong>bold even while wrapped across lines</strong>", got)

    def test_checkbox_items_become_boxes(self):
        got = BUILD.markdown_to_html("- [ ] to do\n- [x] done")
        self.assertIn('<li class="job"><span class="box"></span>to do</li>', got)
        self.assertIn('<li class="job"><span class="box done"></span>done</li>', got)

    def test_table_with_header_and_rows(self):
        got = BUILD.markdown_to_html("| a | b |\n| --- | --- |\n| 1 | 2 |")
        self.assertIn("<th>a</th>", got)
        self.assertIn("<td>2</td>", got)

    def test_table_with_inline_markup(self):
        got = BUILD.markdown_to_html("| h |\n| --- |\n| **bold** |")
        self.assertIn("<strong>bold</strong>", got)

    def test_blockquote(self):
        got = BUILD.markdown_to_html("> **Education only.** be kind")
        self.assertIn('<blockquote><p><strong>Education only.</strong> be kind</p></blockquote>', got)

    def test_heading_ids_unique_slug(self):
        got = BUILD.markdown_to_html("## My Heading!\n\n## My Heading!")
        self.assertEqual(got.count('id="my-heading"'), 2)

    def test_inline_link_with_bold_label(self):
        got = BUILD.markdown_to_html("[**bold** label](https://example.com)")
        self.assertIn('<a href="https://example.com"><strong>bold</strong> label</a>', got)

    def test_html_escaped_by_default(self):
        got = BUILD.markdown_to_html("a < b & c")
        self.assertIn("a &lt; b &amp; c", got)

    def test_fenced_code_escapes_and_preserves(self):
        got = BUILD.markdown_to_html("```\nx < y\n```")
        self.assertIn("<pre><code>x &lt; y</code></pre>", got)

    def test_hr(self):
        got = BUILD.markdown_to_html("before\n\n---\n\nafter")
        self.assertIn("<hr>", got)

    def test_link_rewrite_relative_across_dirs(self):
        self.assertEqual(BUILD._rewrite_md_link("../01-x.md", "worksheets"), "../01-x.html")
        self.assertEqual(BUILD._rewrite_md_link("due.md", "worksheets"), "due.html")
        self.assertEqual(BUILD._rewrite_md_link("01-x.md", ""), "01-x.html")
        self.assertEqual(BUILD._rewrite_md_link("../glossary.md#ein", "worksheets"), "../glossary.html#ein")
        self.assertEqual(BUILD._rewrite_md_link("glossary.md", ""), "glossary.html")
        self.assertEqual(BUILD._rewrite_md_link("#level-2", "worksheets"), "#level-2")
        self.assertEqual(BUILD._rewrite_md_link("https://x.y", "worksheets"), "https://x.y")


if __name__ == "__main__":
    unittest.main()

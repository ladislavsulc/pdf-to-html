#!/usr/bin/env python3
"""Convert PDFs to semantic HTML with optional image extraction."""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class Line:
    text: str
    size: float
    is_bold: bool


@dataclass
class Node:
    kind: str
    text: str | None = None
    level: int | None = None
    items: List[str] | None = None
    src: str | None = None
    alt: str | None = None
    caption: str | None = None
    page: int | None = None
    node_id: str | None = None


HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:\.|\))\s+(.+)$")
BULLET_RE = re.compile(r"^\s*[\u2022\u2023\u25E6\u2043\u2219\-\u2013\u2014]\s+")
FIG_RE = re.compile(r"^(Obr\.|Fig\.|Figure)\s*\d+", re.IGNORECASE)
LEADER_RE = re.compile(r"(?:\s+(?:\.{3,}|(?:·\s*){3,}|(?:•\s*){3,}|(?:⋅\s*){3,}))\s*\d+\s*$")
TOC_LEADER_MIN = 5


STYLE_BLOCK = """
:root {
  color-scheme: light;
  --text: #0b1524;
  --muted: #4b5a70;
  --border: #d7dde7;
  --accent: #1b4d89;
  --bg: #f6f8fb;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Source Serif 4", "Iowan Old Style", "Palatino", serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.6;
}
main {
  max-width: 980px;
  margin: 0 auto;
  padding: 40px 24px 80px;
  background: white;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}
header.document-header {
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
  padding-bottom: 16px;
}
header.document-header p {
  margin: 8px 0 0;
  color: var(--muted);
}
nav.toc {
  margin: 24px 0 40px;
  padding: 16px 20px;
  border: 1px solid var(--border);
  background: #fbfcff;
}
nav.toc h2 {
  margin-top: 0;
}
nav.toc ol {
  margin: 0;
  padding: 0 0 0 20px;
  column-count: 2;
  column-gap: 28px;
  list-style-position: inside;
}
nav.toc li { margin: 6px 0; }
nav.toc li { break-inside: avoid; }
nav.toc li[data-level="3"] { margin-left: 1rem; }
nav.toc li[data-level="4"] { margin-left: 2rem; }
nav.toc li[data-level="5"] { margin-left: 3rem; }
nav.toc li[data-level="6"] { margin-left: 4rem; }
nav.toc a {
  color: var(--accent);
  text-decoration: none;
}
nav.toc a:hover {
  text-decoration: underline;
}
@media (max-width: 720px) {
  nav.toc ol { column-count: 1; }
}
article h2, article h3, article h4 {
  margin-top: 32px;
  color: var(--accent);
}
figure {
  margin: 28px 0;
}
figure img {
  max-width: 100%;
  border: 1px solid var(--border);
}
figure figcaption {
  font-size: 0.95rem;
  color: var(--muted);
  margin-top: 8px;
}
.footer-meta {
  margin-top: 40px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.95rem;
}
""".strip()


def slugify(text: str, fallback: str) -> str:
    raw = re.sub(r"\s+", "-", text.strip().lower())
    raw = re.sub(r"[^a-z0-9\-]", "", raw)
    raw = re.sub(r"-+", "-", raw).strip("-")
    return raw or fallback


def unique_slug(text: str, fallback: str, seen: dict) -> str:
    base = slugify(text, fallback)
    if base not in seen:
        seen[base] = 1
        return base
    seen[base] += 1
    return f"{base}-{seen[base]}"


def median(values: List[float], default: float = 12.0) -> float:
    if not values:
        return default
    return statistics.median(values)


def load_metadata(path: Optional[str]) -> dict:
    if not path:
        return {}
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Metadata JSON must be an object")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PDFs to semantic HTML with SEO-friendly markup.")
    parser.add_argument("input", help="PDF file or directory containing PDFs")
    parser.add_argument("--out", default="out", help="Output directory or HTML file")
    parser.add_argument("--batch", action="store_true", help="Force batch mode for directories")
    parser.add_argument("--recursive", action="store_true", help="Search PDF files recursively")
    parser.add_argument("--no-images", action="store_true", help="Skip image extraction")
    parser.add_argument("--no-toc", action="store_true", help="Skip generating a table of contents")
    parser.add_argument("--keep-toc-pages", action="store_true", help="Keep original PDF TOC pages in body")
    parser.add_argument("--schema-type", default="ScholarlyArticle",
                        help="Schema.org type (e.g., ScholarlyArticle, Report)")
    parser.add_argument("--title", help="Override document title")
    parser.add_argument("--author", help="Override author")
    parser.add_argument("--date", help="Override publication date (YYYY-MM-DD)")
    parser.add_argument("--lang", help="Language code (e.g., en, sk)")
    parser.add_argument("--publisher", help="Publisher / organization")
    parser.add_argument("--description", help="Short description / abstract")
    parser.add_argument("--keywords", help="Comma-separated keywords")
    parser.add_argument("--metadata", help="Path to JSON metadata overrides")
    return parser.parse_args()


def require_fitz():
    try:
        import fitz  # type: ignore
    except Exception as exc:
        raise SystemExit(
            "Missing dependency PyMuPDF. Install with: pip install pymupdf\n"
        ) from exc
    return fitz


def collect_pdf_paths(input_path: Path, recursive: bool) -> List[Path]:
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        return [input_path]
    if input_path.is_dir():
        if recursive:
            return sorted(
                path
                for path in input_path.rglob("*")
                if path.is_file() and path.suffix.lower() == ".pdf"
            )
        return sorted(
            path
            for path in input_path.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        )
    return []


def is_bold_span(span: dict) -> bool:
    font = span.get("font", "") or ""
    flags = span.get("flags", 0) or 0
    return "Bold" in font or bool(flags & 2)


def extract_lines_from_block(block: dict) -> List[Line]:
    lines: List[Line] = []
    for line in block.get("lines", []):
        parts = []
        sizes = []
        bold = False
        for span in line.get("spans", []):
            text = span.get("text", "")
            if text:
                parts.append(text)
                sizes.append(span.get("size", 0.0))
                if is_bold_span(span):
                    bold = True
        text = "".join(parts).strip()
        if text:
            size = median(sizes, default=0.0)
            lines.append(Line(text=text, size=size, is_bold=bold))
    return lines


def merge_lines(lines: List[Line]) -> str:
    if not lines:
        return ""
    merged = lines[0].text
    for idx in range(1, len(lines)):
        prev = lines[idx - 1].text
        current = lines[idx].text
        if not current:
            continue
        if prev.endswith("-") and current[:1].islower():
            merged = merged[:-1] + current
            continue
        merged += " " + current
    return merged.strip()


def strip_leader_dots(text: str, enabled: bool) -> Tuple[str, bool]:
    if not enabled:
        return text.strip(), False
    cleaned = LEADER_RE.sub("", text).strip()
    return cleaned, cleaned != text.strip()


def page_looks_like_toc(blocks: List[dict]) -> bool:
    count = 0
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            parts = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                if text:
                    parts.append(text)
            line_text = "".join(parts).strip()
            if line_text and LEADER_RE.search(line_text):
                count += 1
                if count >= TOC_LEADER_MIN:
                    return True
    return False


def detect_heading(line: Line, body_size: float, level_hint: Optional[int]) -> Optional[int]:
    match = HEADING_RE.match(line.text)
    if match:
        depth = len(match.group(1).split("."))
        return min(6, depth + 1)
    if line.size >= body_size * 1.8:
        return 1 if level_hint == 0 else 2
    if line.size >= body_size * 1.4:
        return 2
    if line.size >= body_size * 1.2 and len(line.text) <= 120:
        return 3
    return None


def extract_title_candidate(lines: List[Line], body_size: float) -> Optional[str]:
    if not lines:
        return None
    best = max(lines, key=lambda ln: ln.size)
    if best.size >= body_size * 1.6 and len(best.text) <= 160:
        return best.text
    return None


def build_nodes(
    doc,
    body_size: float,
    include_images: bool,
    title_line: Optional[str],
    image_dir: Optional[Path],
    include_toc_pages: bool,
) -> List[Node]:
    nodes: List[Node] = []
    image_counter = 0
    heading_count = 0
    pending_text: Optional[str] = None
    pending_page: Optional[int] = None
    pending_y1: Optional[float] = None
    pending_size: Optional[float] = None

    def flush_pending() -> None:
        nonlocal pending_text, pending_page, pending_y1, pending_size
        if pending_text and pending_page is not None:
            nodes.append(Node(kind="p", text=pending_text, page=pending_page))
        pending_text = None
        pending_page = None
        pending_y1 = None
        pending_size = None

    def add_line(text: str, size: float, y0: float, y1: float, page_number: int) -> None:
        nonlocal pending_text, pending_page, pending_y1, pending_size
        if not text:
            return
        if pending_text is None or pending_page != page_number:
            flush_pending()
            pending_text = text
            pending_page = page_number
            pending_y1 = y1
            pending_size = size
            return

        gap = y0 - (pending_y1 or y0)
        threshold = max(2.0, (pending_size or size) * 0.9)
        if gap > threshold:
            flush_pending()
            pending_text = text
            pending_page = page_number
            pending_y1 = y1
            pending_size = size
            return

        if pending_text.endswith("-") and text[:1].islower():
            pending_text = pending_text[:-1] + text
        else:
            pending_text = pending_text + " " + text
        pending_y1 = y1
        pending_size = size

    for page_index in range(len(doc)):
        page = doc[page_index]
        text_dict = page.get_text("dict")
        blocks = list(text_dict.get("blocks", []))
        blocks.sort(key=lambda blk: ((blk.get("bbox") or [0, 0, 0, 0])[1], (blk.get("bbox") or [0, 0, 0, 0])[0]))
        page_is_toc = page_looks_like_toc(blocks)
        if page_is_toc and not include_toc_pages:
            continue
        page_start_idx = len(nodes)
        for block in blocks:
            block_type = block.get("type")
            if block_type == 1 and include_images:
                flush_pending()
                image_bytes = block.get("image")
                ext = block.get("ext", "png")
                xref = block.get("xref")
                if not image_bytes and xref:
                    image = doc.extract_image(xref)
                    image_bytes = image.get("image")
                    ext = image.get("ext", ext)
                if not image_bytes:
                    continue
                image_counter += 1
                if image_dir is not None:
                    image_dir.mkdir(parents=True, exist_ok=True)
                    filename = image_dir / f"page-{page_index+1:03d}-img-{image_counter:03d}.{ext}"
                    filename.write_bytes(image_bytes)
                nodes.append(Node(
                    kind="figure",
                    src=f"images/page-{page_index+1:03d}-img-{image_counter:03d}.{ext}",
                    alt=f"Figure {image_counter} from page {page_index+1}",
                    caption=None,
                    page=page_index + 1,
                ))
                continue
            if block_type != 0:
                continue
            lines = extract_lines_from_block(block)
            if not lines:
                continue
            block_bbox = block.get("bbox") or [0, 0, 0, 0]
            block_y0 = float(block_bbox[1])
            block_y1 = float(block_bbox[3])
            if title_line and lines[0].text == title_line:
                # Skip title line if used as h1
                continue
            # Detect list items
            if all(BULLET_RE.match(ln.text) for ln in lines):
                flush_pending()
                items = [BULLET_RE.sub("", ln.text).strip() for ln in lines]
                nodes.append(Node(kind="ul", items=items, page=page_index + 1))
                continue
            if len(lines) == 1:
                cleaned_text, had_leader = strip_leader_dots(lines[0].text, page_is_toc)
                if had_leader:
                    add_line(cleaned_text, lines[0].size, block_y0, block_y1, page_index + 1)
                    continue
                level = detect_heading(lines[0], body_size, level_hint=heading_count)
                if level:
                    flush_pending()
                    nodes.append(Node(kind="heading", text=cleaned_text, level=level, page=page_index + 1))
                    heading_count += 1
                    continue
                add_line(cleaned_text, lines[0].size, block_y0, block_y1, page_index + 1)
                continue

            flush_pending()
            paragraph = merge_lines(lines)
            if paragraph:
                # If paragraph looks like a heading with numbering
                cleaned_paragraph, had_leader = strip_leader_dots(paragraph, page_is_toc)
                if had_leader:
                    nodes.append(Node(kind="p", text=cleaned_paragraph, page=page_index + 1))
                    continue
                match = HEADING_RE.match(cleaned_paragraph)
                if match:
                    depth = len(match.group(1).split("."))
                    nodes.append(Node(kind="heading", text=cleaned_paragraph, level=min(6, depth + 1), page=page_index + 1))
                    heading_count += 1
                    continue
                nodes.append(Node(kind="p", text=cleaned_paragraph, page=page_index + 1))
        # Append captions if immediately after a figure (including across pages)
        caption_scan_start = max(1, page_start_idx)
        for idx in range(caption_scan_start, len(nodes)):
            if nodes[idx].kind == "p" and nodes[idx - 1].kind == "figure" and nodes[idx - 1].caption is None:
                if nodes[idx].text and FIG_RE.match(nodes[idx].text):
                    nodes[idx - 1].caption = nodes[idx].text
                    nodes[idx].kind = "caption-consumed"
        flush_pending()
    # Remove consumed caption nodes
    nodes = [node for node in nodes if node.kind != "caption-consumed"]
    # Fallback: if no figures detected from blocks, extract page images
    if include_images and image_dir is not None and not any(node.kind == "figure" for node in nodes):
        fallback_counter = 0
        for page_index in range(len(doc)):
            page = doc[page_index]
            page_no = page_index + 1
            image_items: List[Tuple[float, int]] = []
            if hasattr(page, "get_image_info"):
                try:
                    info_list = page.get_image_info(xrefs=True)
                    for info in info_list:
                        xref = info.get("xref")
                        bbox = info.get("bbox") or [0, 0, 0, 0]
                        y0 = float(bbox[1])
                        if xref:
                            image_items.append((y0, xref))
                except Exception:
                    image_items = []
            if not image_items:
                for img in page.get_images(full=True):
                    xref = img[0]
                    image_items.append((0.0, xref))
            image_items.sort(key=lambda item: item[0])
            insert_at = len(nodes)
            for idx in range(len(nodes) - 1, -1, -1):
                if nodes[idx].page == page_no:
                    insert_at = idx + 1
                    break
            for _, xref in image_items:
                image = doc.extract_image(xref)
                image_bytes = image.get("image")
                if not image_bytes:
                    continue
                ext = image.get("ext", "png")
                fallback_counter += 1
                filename = image_dir / f"page-{page_no:03d}-img-{fallback_counter:03d}.{ext}"
                image_dir.mkdir(parents=True, exist_ok=True)
                filename.write_bytes(image_bytes)
                nodes.insert(insert_at, Node(
                    kind="figure",
                    src=f"images/page-{page_no:03d}-img-{fallback_counter:03d}.{ext}",
                    alt=f"Figure {fallback_counter} from page {page_no}",
                    caption=None,
                    page=page_no,
                ))
                insert_at += 1
    # Assign unique heading ids
    seen: dict = {}
    heading_count = 0
    for node in nodes:
        if node.kind == "heading" and node.text:
            heading_count += 1
            node.node_id = unique_slug(node.text, f"section-{heading_count}", seen)
    return nodes


def build_toc(nodes: List[Node]) -> str:
    toc_entries = []
    for node in nodes:
        if node.kind != "heading" or not node.text or not node.level:
            continue
        node_id = node.node_id or slugify(node.text, "section")
        level = max(2, min(6, node.level))
        toc_entries.append(
            f'<li data-level="{level}"><a href="#{escape(node_id)}">{escape(node.text)}</a></li>'
        )
    if not toc_entries:
        return ""
    return "<ol>\n" + "\n".join(toc_entries) + "\n</ol>"


def nodes_to_html(nodes: List[Node]) -> str:
    html_parts: List[str] = []
    section_stack: List[int] = []
    for node in nodes:
        if node.kind == "heading" and node.text and node.level:
            node_id = node.node_id or slugify(node.text, "section")
            level = max(2, min(6, node.level))
            while section_stack and section_stack[-1] >= level:
                html_parts.append("</section>")
                section_stack.pop()
            html_parts.append(f'<section data-page="{node.page}">')
            html_parts.append(f'<h{level} id="{escape(node_id)}">{escape(node.text)}</h{level}>')
            section_stack.append(level)
        elif node.kind == "p" and node.text:
            html_parts.append(f'<p data-page="{node.page}">{escape(node.text)}</p>')
        elif node.kind == "ul" and node.items:
            html_parts.append(f'<ul data-page="{node.page}">')
            for item in node.items:
                html_parts.append(f"<li>{escape(item)}</li>")
            html_parts.append("</ul>")
        elif node.kind == "figure" and node.src:
            html_parts.append(f'<figure data-page="{node.page}">')
            html_parts.append(f'<img src="{escape(node.src)}" alt="{escape(node.alt or "Figure")}">')
            if node.caption:
                html_parts.append(f'<figcaption>{escape(node.caption)}</figcaption>')
            html_parts.append("</figure>")
    while section_stack:
        html_parts.append("</section>")
        section_stack.pop()
    return "\n".join(html_parts)


def build_schema(metadata: dict, title: str, schema_type: str, images: List[str]) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": title,
        "headline": title,
    }
    if metadata.get("author"):
        data["author"] = {"@type": "Person", "name": metadata["author"]}
    if metadata.get("date"):
        data["datePublished"] = metadata["date"]
    if metadata.get("description"):
        data["description"] = metadata["description"]
    if metadata.get("publisher"):
        data["publisher"] = {"@type": "Organization", "name": metadata["publisher"]}
    if metadata.get("lang"):
        data["inLanguage"] = metadata["lang"]
    if metadata.get("keywords"):
        data["keywords"] = metadata["keywords"]
    if images:
        data["image"] = images
    return json.dumps(data, ensure_ascii=False, indent=2)


def render_html(title: str, metadata: dict, toc_html: str, body_html: str, schema_json: str) -> str:
    description = metadata.get("description") or ""
    keywords_value = metadata.get("keywords") or ""
    if isinstance(keywords_value, list):
        keywords = ", ".join(str(item) for item in keywords_value)
    else:
        keywords = str(keywords_value)
    author = metadata.get("author") or ""
    lang = metadata.get("lang") or "und"
    header_lines = []
    if author:
        header_lines.append(f"<p><strong>Author:</strong> {escape(author)}</p>")
    if metadata.get("date"):
        header_lines.append(f"<p><strong>Date:</strong> {escape(metadata['date'])}</p>")
    if metadata.get("publisher"):
        header_lines.append(f"<p><strong>Publisher:</strong> {escape(metadata['publisher'])}</p>")
    header_html = "\n".join(header_lines)

    toc_block = ""
    if toc_html:
        toc_block = f"<nav class=\"toc\"><h2>Contents</h2>{toc_html}</nav>"

    footer_lines = []
    if metadata.get("source"):
        footer_lines.append(f"<div><strong>Source PDF:</strong> {escape(metadata['source'])}</div>")
    footer_html = "\n".join(footer_lines)

    return f"""<!doctype html>
<html lang=\"{escape(lang)}\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{escape(title)}</title>
  <meta name=\"description\" content=\"{escape(description)}\">
  <meta name=\"author\" content=\"{escape(author)}\">
  <meta name=\"keywords\" content=\"{escape(keywords)}\">
  <meta name=\"generator\" content=\"pdf_to_semantic_html.py\">
  <style>{STYLE_BLOCK}</style>
  <script type=\"application/ld+json\">{schema_json}</script>
</head>
<body>
  <main>
    <header class=\"document-header\">
      <h1>{escape(title)}</h1>
      {header_html}
    </header>
    {toc_block}
    <article>
      {body_html}
    </article>
    <footer class=\"footer-meta\">{footer_html}</footer>
  </main>
</body>
</html>"""


def convert_pdf(
    pdf_path: Path,
    output_html: Path,
    include_images: bool,
    meta: dict,
    schema_type: str,
    include_toc: bool,
    include_toc_pages: bool,
) -> None:
    fitz = require_fitz()
    doc = fitz.open(pdf_path)
    pdf_meta = doc.metadata or {}
    if not meta.get("author") and pdf_meta.get("author"):
        meta["author"] = pdf_meta.get("author")
    if not meta.get("title") and pdf_meta.get("title"):
        meta["title"] = pdf_meta.get("title")
    span_sizes: List[float] = []
    for page in doc:
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_sizes.append(span.get("size", 0.0))
    body_size = median(span_sizes, default=12.0)

    # Title candidate from first page
    title_line = None
    if len(doc) > 0:
        first_page = doc[0]
        first_lines = []
        for block in first_page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            first_lines.extend(extract_lines_from_block(block))
        title_line = extract_title_candidate(first_lines, body_size)

    title = meta.get("title") or title_line or pdf_path.stem
    meta.setdefault("title", title)

    image_dir = output_html.parent / "images" if include_images else None
    nodes = build_nodes(
        doc,
        body_size,
        include_images,
        title_line if title_line == title else None,
        image_dir,
        include_toc_pages=include_toc_pages,
    )

    toc_html = "" if not include_toc else build_toc(nodes)
    body_html = nodes_to_html(nodes)

    # Collect image paths for schema
    images = []
    if include_images:
        images = [node.src for node in nodes if node.kind == "figure" and node.src]

    schema_json = build_schema(meta, title, schema_type, images)
    html = render_html(title, meta, toc_html, body_html, schema_json)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")


def apply_overrides(args: argparse.Namespace, meta: dict) -> dict:
    overrides = {
        "title": args.title,
        "author": args.author,
        "date": args.date,
        "lang": args.lang,
        "publisher": args.publisher,
        "description": args.description,
    }
    if args.keywords:
        overrides["keywords"] = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]
    for key, value in overrides.items():
        if value:
            meta[key] = value
    return meta


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.out).expanduser().resolve()
    meta = load_metadata(args.metadata)
    meta = apply_overrides(args, meta)
    meta.setdefault("lang", "und")

    pdf_paths = collect_pdf_paths(input_path, args.recursive)
    if not pdf_paths:
        raise SystemExit("No PDF files found to process.")

    batch_mode = args.batch or input_path.is_dir()
    include_images = not args.no_images
    include_toc = not args.no_toc

    for pdf in pdf_paths:
        meta_instance = dict(meta)
        meta_instance["source"] = pdf.name
        if batch_mode:
            doc_dir = output_path / pdf.stem
            output_html = doc_dir / "index.html"
        else:
            if output_path.suffix.lower() == ".html":
                output_html = output_path
            else:
                output_html = output_path / f"{pdf.stem}.html"
        convert_pdf(
            pdf,
            output_html,
            include_images,
            meta_instance,
            args.schema_type,
            include_toc,
            include_toc_pages=args.keep_toc_pages,
        )
        print(f"Converted: {pdf} -> {output_html}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render the Featured Publications section in index.html from JSON data.

Usage:
  python3 scripts/render_featured_publications.py
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "featured_publications.json"
INDEX_PATH = ROOT / "index.html"

SECTION_PATTERN = re.compile(
    r"<!-- Publications start -->.*?<!-- Publications end -->",
    flags=re.DOTALL,
)


def attr(value: str) -> str:
    return html.escape(value, quote=True)


def text(value: str) -> str:
    return html.escape(value)


def render_authors(authors: list[dict]) -> str:
    lines: list[str] = []
    for i, author in enumerate(authors):
        span_class = ' class="author-highlighted"' if author.get("highlighted") else ""
        comma = "," if i < len(authors) - 1 else ""
        affiliation = attr(author["affiliation"])
        name = text(author["name"])
        lines.append(
            f'              <span{span_class}>{name}</span>'
            f'<i class="author-notes fas fa-info-circle" data-toggle="tooltip" title="{affiliation}"></i>{comma}'
        )
    return "\n".join(lines)


def render_buttons(buttons: list[dict]) -> str:
    lines: list[str] = []
    for button in buttons:
        label = text(button["label"])
        if button.get("type") == "cite":
            filename = attr(button["filename"])
            lines.extend(
                [
                    f'            <a href="#" class="btn btn-outline-primary btn-page-header btn-sm js-cite-modal" data-filename="{filename}">',
                    f"              {label}",
                    "            </a>",
                ]
            )
            continue

        href = attr(button["href"])
        target_attrs = ' target="_blank" rel="noopener"' if button.get("target_blank") else ""
        lines.extend(
            [
                f'            <a class="btn btn-outline-primary btn-page-header btn-sm" href="{href}"{target_attrs}>',
                f"              {label}",
                "            </a>",
            ]
        )
    return "\n".join(lines)


def render_entry(entry: dict) -> str:
    pub_id = text(entry["id"])
    page_url = attr(entry["page_url"])
    date_text = text(entry["date"])
    venue_html = entry["venue_html"]
    title_text = text(entry["title"])
    summary_text = text(entry["summary"])

    image = entry["image"]
    image_src = attr(image["src"])
    image_alt = attr(image["alt"])
    image_height = int(image["height"])
    image_width = int(image["width"])
    image_style = f' style="{attr(image["style"])}"' if image.get("style") else ""

    authors_html = render_authors(entry["authors"])
    buttons_html = render_buttons(entry["buttons"])

    return f"""        <!-- Publication {pub_id} start -->
        <div class="card-simple view-card">
          <div class="article-metadata">
            <div>
{authors_html}

              <span class="article-date">
                {date_text}
              </span>
            </div>
            <span class="middot-divider">
            </span>
            <span class="pub-publication">
              {venue_html}
            </span>
          </div>
          <a href="{page_url}" >
            <div class="img-hover-zoom">
              <img src="{image_src}"{image_style} height="{image_height}" width="{image_width}"
                  class="article-banner" alt="{image_alt}" loading="lazy">
            </div>
          </a>
          <div class="section-subheading article-title mb-1 mt-3">
            <a href="{page_url}" >{title_text}</a>
          </div>
          <a href="{page_url}"  class="summary-link">
            <div class="article-style">
              <p>{summary_text}</p>
            </div>
          </a>
          <div class="btn-links">
{buttons_html}
          </div>
        </div>
        <!-- Publication {pub_id} end -->"""


def render_section(data: dict) -> str:
    section_title = text(data["section_title"])
    entries = data["entries"]
    cards = "\n\n".join(render_entry(entry) for entry in entries)
    return f"""<!-- Publications start -->
<section id="featured" class="home-section wg-featured  "  >
  <div class="home-section-bg " >
  </div>
  <div class="container">
    <div class="row  ">
      <div class="section-heading col-12 col-lg-4 mb-3 mb-lg-0 d-flex flex-column align-items-center align-items-lg-start">
        <h1 class="mb-0">{section_title}</h1>
      </div>

      <div class="col-12 col-lg-8">

{cards}
      </div>
    </div>
  </div>
</section>
<!-- Publications end -->"""


def main() -> int:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    rendered_section = render_section(data)

    index_html = INDEX_PATH.read_text(encoding="utf-8")
    if not SECTION_PATTERN.search(index_html):
        raise RuntimeError("Could not find Publications section markers in index.html")

    updated = SECTION_PATTERN.sub(rendered_section, index_html)
    INDEX_PATH.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

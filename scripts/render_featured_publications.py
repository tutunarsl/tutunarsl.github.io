#!/usr/bin/env python3
"""Refresh publication cards, archive, search index, feeds and sitemap.

Usage:
  python3 scripts/render_featured_publications.py
"""

from __future__ import annotations

import html
import json
import re
import argparse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "featured_publications.json"
INDEX_PATH = ROOT / "index.html"
SITE_URL = "https://www.turcantuna.com"
PUBLICATION_TYPES = {
    "conference": (1, "Conference paper"), "journal": (2, "Journal article"),
    "workshop": (3, "Workshop contribution"), "preprint": (4, "Preprint"),
}

SECTION_PATTERN = re.compile(
    r"<!-- Publications start -->.*?<!-- Publications end -->",
    flags=re.DOTALL,
)


def attr(value: str) -> str:
    return html.escape(value, quote=True)


def text(value: str) -> str:
    return html.escape(value)


def display_authors(entry: dict) -> list[dict]:
    """Reorder only the equal-contribution group; retain published citation order."""
    authors = list(entry["authors"])
    shared = set(entry.get("equal_contributors", []))
    if "Turcan Tuna" in shared:
        positions = [i for i, author in enumerate(authors) if author["name"] in shared]
        group = sorted((authors[i] for i in positions), key=lambda a: a["name"] != "Turcan Tuna")
        for index, author in zip(positions, group):
            authors[index] = author
    return [dict(author, equal=author["name"] in shared) for author in authors]


def equal_note(entry: dict) -> str:
    if not entry.get("equal_contributors"):
        return ""
    return '<p class="article-metadata mb-2"><sup>*</sup> Equal contribution; order within the marked group is a presentation choice.</p>'


def render_authors(authors: list[dict], icon_spacing: bool = False) -> str:
    lines: list[str] = []
    for i, author in enumerate(authors):
        span_class = ' class="author-highlighted"' if author.get("highlighted") else ""
        comma = "," if i < len(authors) - 1 else ""
        affiliation = attr(author.get("affiliation", ""))
        name = text(author["name"])
        if author.get("equal"):
            name += '<sup aria-label="equal contribution">*</sup>'
        spacing = " " if icon_spacing else ""
        tooltip = f'{spacing}<i class="author-notes fas fa-info-circle" data-toggle="tooltip" title="{affiliation}"></i>' if affiliation else ""
        lines.append(
            f'              <span{span_class}>{name}</span>{tooltip}{comma}'
        )
    return "\n".join(lines)


def render_buttons(buttons: list[dict], small: bool = True) -> str:
    lines: list[str] = []
    classes = "btn btn-outline-primary btn-page-header" + (" btn-sm" if small else "")
    for button in buttons:
        label = text(button["label"])
        if button.get("type") == "cite":
            filename = attr(button["filename"])
            lines.extend(
                [
                    f'            <a href="#" class="{classes} js-cite-modal" data-filename="{filename}">',
                    f"              {label}",
                    "            </a>",
                ]
            )
            continue

        href = attr(button["href"])
        target_attrs = ' target="_blank" rel="noopener"' if button.get("target_blank") else ""
        lines.extend(
            [
                f'            <a class="{classes}" href="{href}"{target_attrs}>',
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

    authors_html = render_authors(display_authors(entry), entry.get("author_icon_spacing", False))
    buttons_html = render_buttons(entry["buttons"])
    divider = '<span class="middot-divider"></span>' if entry.get("metadata_divider", True) else ""

    card = f"""        <!-- Publication {pub_id} start -->
        <div class="card-simple view-card">
          <div class="article-metadata">
            <div>
{authors_html}

              <span class="article-date">
                {date_text}
              </span>
            </div>
            {divider}
            <span class="pub-publication">
              {venue_html}
            </span>
          </div>
          {equal_note(entry)}
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
    return "\n".join(line.rstrip() for line in card.splitlines())


def render_section(data: dict, existing_section: str) -> str:
    """Replace cards while preserving the section's layout and introductory notice."""
    ids = [entry["id"] for entry in data["entries"]]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Publication IDs must be unique and the list must not be empty")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", str(pub_id)) for pub_id in ids):
        raise ValueError("Publication IDs must contain only letters, numbers, _ or -")
    blocks = list(re.finditer(
        r"[ \t]*<!-- Publication ([A-Za-z0-9_-]+) start -->.*?<!-- Publication \1 end -->",
        existing_section, re.DOTALL,
    ))
    if not blocks:
        raise RuntimeError("Could not find existing publication card markers")
    cards = "\n\n".join(render_entry(entry) for entry in sorted(data["entries"], key=lambda e: e['year'], reverse=True) if entry.get("featured"))
    section = existing_section[:blocks[0].start()] + cards + existing_section[blocks[-1].end():]
    return re.sub(r'(<h1 class="mb-0">).*?(</h1>)',
                  lambda match: match[1] + text(data["section_title"]) + match[2],
                  section, count=1, flags=re.DOTALL)


def render_archive(data: dict) -> str:
    """Use the existing Wowchemy citation list and filter classes."""
    entries = sorted(data["entries"], key=lambda entry: entry["year"], reverse=True)
    years = sorted({entry["year"] for entry in entries}, reverse=True)
    year_options = "\n".join(f'<option value=".year-{year}">{year}</option>' for year in years)
    rows = []
    for entry in entries:
        publication_type = PUBLICATION_TYPES[entry["publication_type"]][0]
        authors = render_authors(display_authors(entry))
        rows.append(f'''<div class="grid-sizer col-lg-12 isotope-item pubtype-{publication_type} year-{entry['year']}">
  <div class="pub-list-item view-citation" style="margin-bottom: 1rem">
    <i class="far fa-file-alt pub-icon" aria-hidden="true"></i>
    <span class="article-metadata li-cite-author">{authors}</span> ({entry['year']}).
    <a href="{attr(entry['page_url'])}">{text(entry['title'])}</a>.
    <span class="pub-publication">{entry['venue_html']}</span>
    {equal_note(entry)}
    <p>{render_buttons(entry['buttons'])}</p>
  </div>
</div>''')
    type_options = ''.join(f'<option value=".pubtype-{code}">{label}</option>' for code, label in PUBLICATION_TYPES.values())
    return f'''<!-- Publication archive start -->
<div class="universal-wrapper">
  <p>{len(entries)} research works. <a href="/publication/cite.bib" download>Download bibliography</a></p>
  <div class="row"><div class="col-lg-12">
    <div class="form-row mb-4">
      <div class="col-auto"><input type="search" class="filter-search form-control form-control-sm" placeholder="Search..." aria-label="Search publications" autocomplete="off" spellcheck="false"></div>
      <div class="col-auto"><select class="pub-filters pubtype-select form-control form-control-sm" data-filter-group="pubtype" aria-label="Publication type">
        <option value="*">Type</option>{type_options}
      </select></div>
      <div class="col-auto"><select class="pub-filters form-control form-control-sm" data-filter-group="year" aria-label="Publication year">
        <option value="*">Date</option>''' + year_options + '''
      </select></div>
    </div>
    <div id="container-publications">''' + "\n".join(rows) + '''</div>
  </div></div>
</div>
<!-- Publication archive end -->'''


class HomepageSearch(HTMLParser):
    """Extract visible homepage entries for the existing Fuse search engine."""

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.section = ""
        self.active = None
        self.records = []
        self.platforms = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if self.active and self.section == 'platforms':
            if tag == 'img': self.active['image'] = attrs.get('src', '')
            if tag == 'a' and attrs.get('href'): self.active['href'] = attrs['href']
        if tag in self.VOID_TAGS:
            return
        self.stack.append((tag, attrs))
        if tag == "section":
            self.section = attrs.get("id", "")
        classes = attrs.get("class", "").split()
        is_entry = (
            tag == "section" and self.section in {"about", "contact"}
            or self.section == "updates" and tag == "details" and sum(t == "details" for t, _ in self.stack) == 2
            or self.section == "experience" and "experience" in classes
            or self.section == "platforms" and "project-card" in classes
        )
        if is_entry:
            self.active = {"depth": len(self.stack), "title": [], "content": [], "description": [], "section": self.section}

    def handle_endtag(self, tag):
        if not any(t == tag for t, _ in self.stack):
            return
        while self.stack:
            current, _ = self.stack.pop()
            if self.active and len(self.stack) < self.active["depth"]:
                entry = self.active
                title = " ".join(entry["title"]) or entry["section"].title()
                content = " ".join(entry["content"])
                self.records.append(search_record(title, content, "/#" + entry["section"], entry["section"].title(), "home-" + str(len(self.records))))
                if entry['section'] == 'platforms':
                    self.platforms.append(dict(title=title, description=' '.join(entry['description']), image=entry.get('image',''), href=entry.get('href','')))
                self.active = None
            if current == tag:
                break
        if tag == "section":
            self.section = ""

    def handle_data(self, value):
        value = " ".join(value.split())
        if not self.active or not value or any(t in {"script", "style"} for t, _ in self.stack):
            return
        self.active["content"].append(value)
        if self.section == 'platforms' and any(t == 'p' for t, _ in self.stack[self.active['depth']:]):
            self.active['description'].append(value)
        if any(t in {"h1", "h2", "h4", "summary"} or any(c in a.get("class", "").split() for c in {"exp-title", "exp-company"}) for t, a in self.stack[self.active["depth"]:]):
            self.active["title"].append(value)


def search_record(title: str, content: str, path: str, section: str, identifier: str) -> dict:
    return {"title": title, "summary": content[:300], "content": content,
            "relpermalink": path, "permalink": SITE_URL + path, "section": section,
            "objectID": identifier, "authors": [], "tags": [], "categories": []}


def render_search(data: dict, homepage: str) -> str:
    parser = HomepageSearch()
    parser.feed(homepage)
    records = parser.records
    # Derive platform descriptions from their pages instead of recycling stale index.json.
    for page in sorted((ROOT / "platform").glob("*/index.html")):
        source = page.read_text(encoding="utf-8")
        title = html.unescape(re.search(r"<title>(.*?) \|", source, re.DOTALL)[1])
        description = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', source)[1])
        path = "/" + page.parent.relative_to(ROOT).as_posix() + "/"
        records.append(search_record(title, description, path, "Platform", path))
    for entry in data["entries"]:
        content = ' '.join(filter(None, [entry['summary'], entry.get('abstract'), entry['venue_label']]))
        records.append({"title": entry["title"], "summary": entry["summary"], "content": content,
                        "authors": [author["name"] for author in entry["authors"]],
                        "relpermalink": entry["page_url"], "permalink": SITE_URL + entry["page_url"],
                        "section": "publication", "type": "publication", "kind": "page", "lang": "en",
                        "tags": [], "categories": [], "objectID": entry["id"]})
    return json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n"


def render_feed(data: dict) -> str:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for key, value in [("title", "Turcan Tuna — Publications"), ("link", SITE_URL + "/publication/"),
                       ("description", "Research publications by Turcan Tuna.")]:
        ET.SubElement(channel, key).text = value
    for entry in sorted(data["entries"], key=lambda item: item["year"], reverse=True):
        item = ET.SubElement(channel, "item")
        for key, value in [("title", entry["title"]), ("link", SITE_URL + entry["page_url"]),
                           ("guid", SITE_URL + entry["page_url"]), ("description", entry["summary"])]:
            ET.SubElement(item, key).text = value
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(rss, encoding="unicode") + "\n"


def render_platform_archive(homepage: str, source: str) -> str:
    """Use the homepage's existing robot inventory for the compact archive."""
    parser = HomepageSearch(); parser.feed(homepage)
    rows = []
    for robot in parser.platforms:
        rows.append(f'''<div class="media stream-item view-compact">
  <div class="media-body">
    <div class="section-subheading article-title mb-0 mt-0"><a href="{attr(robot['href'])}" target="_blank" rel="noopener">{text(robot['title'])}</a></div>
    <div class="article-style">{text(robot['description'])}</div>
  </div>
  <div class="ml-3"><a href="{attr(robot['href'])}" target="_blank" rel="noopener"><img src="{attr(robot['image'])}" width="150" height="100" style="object-fit:contain" alt="{attr(robot['title'])}" loading="lazy"></a></div>
</div>''')
    body = '<div class="page-body"><div class="universal-wrapper pt-3"><h1>Robotic Platforms</h1></div><div class="universal-wrapper">' + '\n'.join(rows) + '</div></div>'
    begin, end = element_span(source, 'div', 'page-body')
    return source[:begin] + body + source[end:]


def element_span(source: str, tag: str, class_name: str, start: int = 0) -> tuple[int, int]:
    """Locate a complete HTML element without reformatting the exported page."""
    match = next((m for m in re.finditer(r'<' + tag + r'\b[^>]*\bclass="([^"]*)"[^>]*>', source[start:])
                  if class_name in m[1].split()), None)
    if match is None:
        raise ValueError(f'Missing {tag}.{class_name}')
    begin = start + match.start()
    depth = 0
    for token in re.finditer(r'</?' + tag + r'\b[^>]*>', source[begin:]):
        depth += -1 if token[0].startswith('</') else 1
        if depth == 0:
            return begin, begin + token.end()
    raise ValueError(f'Unclosed {tag}.{class_name}')


def render_detail_metadata(entry: dict) -> str:
    return f'''<div class="article-metadata">
  <div>{render_authors(display_authors(entry))}</div>
  <span class="article-date">{text(entry['date'])}</span>
  <span class="middot-divider"></span>
  <span class="pub-publication">{entry['venue_html']}</span>
  {equal_note(entry)}
</div>'''


def render_new_detail(entry: dict) -> str:
    code, label = PUBLICATION_TYPES[entry['publication_type']]
    note = '<p class="article-metadata">' + text(entry['citation_note']) + '</p>' if entry.get('citation_note') else ''
    content = render_abstract(entry) if entry.get('abstract') else '<h3>Overview</h3><p>' + text(entry['summary']) + '</p>'
    figure = render_figure(entry['image']) if entry.get('image') else ''
    return f'''<!-- Publication detail start -->
<article class="pub article-container pt-3">
  <h1>{text(entry['title'])}</h1>
  {render_detail_metadata(entry)}
  <div class="btn-links mb-3">{render_buttons(entry['buttons'], small=False)}</div>
  {figure}
  <div class="article-style">{content}</div>
  {note}
  <p><a href="/publication/#{code}">{label}</a> · <a href="/publication/">All publications</a></p>
</article>
<!-- Publication detail end -->'''


def render_figure(image: dict) -> str:
    return f'''<figure class="publication-figure">
  <a href="{attr(image['src'])}" target="_blank" rel="noopener" aria-label="Open full-size figure">
    <img src="{attr(image['src'])}" width="{int(image['width'])}" height="{int(image['height'])}" alt="{attr(image['alt'])}" loading="lazy" decoding="async" style="background:#fff;width:100%;height:auto;object-fit:contain;">
  </a>
  <figcaption>{text(image['caption'])} <a href="{attr(image['source_url'])}" target="_blank" rel="noopener">{text(image['credit'])} · Source</a></figcaption>
</figure>'''


def render_abstract(entry: dict) -> str:
    return '<h3>Abstract summary</h3><p class="pub-abstract">' + text(entry['abstract']) + '</p><p class="article-metadata"><a href="' + attr(entry['abstract_source']) + '" target="_blank" rel="noopener">Read the original abstract and paper</a></p>'


def render_detail(entry: dict, source: str) -> str:
    """Synchronize authors, dates, descriptions, buttons and scholarly metadata."""
    if '<!-- Publication detail start -->' in source:
        source = re.sub(r'<!-- Publication detail start -->.*?<!-- Publication detail end -->',
                        lambda _: render_new_detail(entry), source, flags=re.DOTALL)
    else:
        begin, end = element_span(source, 'div', 'article-metadata', source.index('<div class="page-body">'))
        source = source[:begin] + render_detail_metadata(entry) + source[end:]
        source = re.sub(r'(<span class="article-date">).*?(</span>)',
                        lambda m: m[1] + text(entry['date']) + m[2], source, flags=re.DOTALL)
        # Preserve paper-specific images and the original page structure.
        source = re.sub(r'(<span class="pub-publication">).*?(</span>)',
                        lambda m: m[1] + entry['venue_html'] + m[2], source, flags=re.DOTALL)
        if entry.get('abstract'):
            primary_figure = '<!-- Publication primary figure start -->\n<div class="article-container">' + render_figure(entry['image']) + '</div>\n<!-- Publication primary figure end -->'
            primary_pattern = r'<!-- Publication primary figure start -->.*?<!-- Publication primary figure end -->'
            if re.search(primary_pattern, source, re.DOTALL):
                source = re.sub(primary_pattern, lambda _: primary_figure, source, flags=re.DOTALL)
            elif not re.search(r'<img\b[^>]*\bsrc="' + re.escape(entry['image']['src']) + '"', source):
                begin, _ = element_span(source, 'div', 'featured-image-wrapper')
                source = source[:begin] + primary_figure + '\n\n' + source[begin:]
            # Preserve the original detail layouts while keeping their text in sync.
            source, count = re.subn(r'<h3>Abstract(?: summary)?</h3>\s*<p class="pub-abstract">.*?</p>(?:<p class="article-metadata"><a href="[^"]*" target="_blank" rel="noopener">Read the original abstract and paper</a></p>)?',
                                    lambda _: render_abstract(entry), source, count=1, flags=re.DOTALL)
            if count != 1: raise RuntimeError('Missing abstract block in ' + entry['page_url'])
            source = re.sub(r'(<a [^>]*class="summary-link"[^>]*>\s*<div class="article-style">\s*<p>).*?(</p>)',
                            lambda m: m[1] + text(entry['summary']) + m[2], source, count=1, flags=re.DOTALL)
            # Existing figures remain in place; add descriptive alternative text.
            source = re.sub(r'(<img\b[^>]*\bsrc="' + re.escape(entry['image']['src']) + r'"[^>]*\balt=")[^"]*(")',
                            lambda m: m[1] + attr(entry['image']['alt']) + m[2], source)
            def credit_caption(match):
                caption = match[2].split(' <a class="figure-source"')[0]
                link = ' <a class="figure-source" href="' + attr(entry['image']['source_url']) + '" target="_blank" rel="noopener">Source</a>'
                return match[1] + caption + link + match[3]
            source = re.sub(r'(<span class="article-header-caption">)(.*?)(</span>)', credit_caption, source, flags=re.DOTALL)
            source = re.sub(r'(<img\b[^>]*\balt=")("[^>]*class="featured-image")',
                            lambda m: m[1] + attr(entry['title'] + ' — research figure') + m[2], source)
    source, count = re.subn(r'(<div class="btn-links(?: mb-3)?">).*?(</div>)',
                           lambda match: match[1] + "\n" + render_buttons(entry["buttons"], small=False) + "\n" + match[2],
                           source, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError("Missing publication buttons in " + entry["page_url"])
    # The exported pages all had the same template date, not their actual publication dates.
    source = re.sub(r'\s*<meta\s+property="article:(?:published|modified)_time"\s+content="[^"]*"\s*/?>', "", source)
    title = entry['title'] + ' | Turcan Tuna'
    description = ' '.join(entry['summary'].split())
    url = SITE_URL + entry['page_url']
    image = SITE_URL + entry.get('image', {}).get('src', '/authors/admin/avatar.jpg')
    source = re.sub(r'<title>.*?</title>', lambda _: '<title>' + text(title) + '</title>', source, flags=re.DOTALL)
    values = {'description':description, 'og:description':description, 'og:title':title, 'og:url':url,
              'og:image':image, 'twitter:image':image}
    for name, value in values.items():
        source = re.sub(r'(<meta (?:name|property)="' + re.escape(name) + r'" content=")[^"]*(")',
                        lambda m: m[1] + attr(value) + m[2], source)
    source = re.sub(r'(<link rel="(?:canonical|alternate)"[^>]*href=")[^"]*(")',
                    lambda m: m[1] + attr(url) + m[2], source)
    metadata = {"@context": "https://schema.org", "@type": "ScholarlyArticle",
                "mainEntityOfPage": SITE_URL + entry["page_url"], "headline": entry["title"],
                "image": [image], "author": [{"@type": "Person", "name": author["name"]} for author in entry["authors"]],
                "description": description, "isPartOf": {"@type":"CreativeWork", "name":entry['venue']}}
    if entry.get('doi'):
        metadata['identifier'] = 'https://doi.org/' + entry['doi']
        metadata['sameAs'] = 'https://doi.org/' + entry['doi']
    if entry['status'] != 'accepted':
        metadata['datePublished'] = str(entry['year'])
    for key in ('volume', 'issue', 'pages'):
        if entry.get(key):
            metadata[{'volume':'volumeNumber','issue':'issueNumber','pages':'pagination'}[key]] = entry[key]
    return re.sub(r'(<script type="application/ld\+json">).*?(</script>)',
                  lambda match: match[1] + "\n" + json.dumps(metadata, ensure_ascii=False, indent=2) + "\n" + match[2],
                  source, count=1, flags=re.DOTALL)


def render_bibtex(entry: dict) -> str:
    kind = 'inproceedings' if entry['publication_type'] in ('conference','workshop') else 'misc' if entry['publication_type']=='preprint' else 'article'
    fields = {'title': '{' + entry['title'] + '}', 'author': ' and '.join(a.get('citation_name', a['name']) for a in entry['authors']),
              'year': str(entry['year'])}
    if kind == 'article': fields['journal'] = entry['venue']
    if kind == 'inproceedings': fields['booktitle'] = entry['venue']
    for key in ('volume','pages','doi'):
        if entry.get(key): fields[key] = str(entry[key])
    if entry.get('issue'): fields['number'] = str(entry['issue'])
    if entry.get('article_number'): fields['eid'] = entry['article_number']
    if entry.get('doi'): fields['url'] = 'https://doi.org/' + entry['doi']
    if entry.get('arxiv_id'):
        fields['eprint'] = entry['arxiv_id']; fields['archivePrefix'] = 'arXiv'
        fields.setdefault('url', 'https://arxiv.org/abs/' + entry['arxiv_id'])
    if entry.get('citation_note'): fields['note'] = entry['citation_note']
    escape = lambda value: value.replace('&', r'\&').replace('%', r'\%').replace('_', r'\_')
    return '@' + kind + '{tuna_' + entry['research_id'] + '_' + str(entry['year']) + ',\n' + ',\n'.join(
        '  ' + key + ' = {' + escape(value) + '}' for key, value in fields.items()) + '\n}\n'


def tex(value: str) -> str:
    escapes = {'&': r'\&', '%': r'\%', '_': r'\_', '#': r'\#', '$': r'\$',
               '{': r'\{', '}': r'\}', '\\': r'\textbackslash{}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(escapes.get(c, c) for c in value)


def render_cv(data: dict, source: str) -> str:
    blocks = ['% Publications start']
    groups = [('journal', 'Journal Articles'), ('conference', 'Conference Proceedings'),
              ('workshop', 'Workshop Contributions'), ('preprint', 'Preprints')]
    for kind, label in groups:
        if kind == 'conference': blocks.append(r'\clearpage')
        blocks.append(r'\cvsubsection{' + label + '}')
        for entry in (e for e in data['entries'] if e['publication_type'] == kind):
            authors = []
            for author in display_authors(entry):
                name = tex(author['name'])
                if author.get('highlighted'): name = r'\textbf{' + name + '}'
                if author['equal']: name += r'\textsuperscript{*}'
                authors.append(name)
            url = 'https://doi.org/' + entry['doi'] if entry.get('doi') else 'https://arxiv.org/abs/' + entry['arxiv_id']
            title = r'\href{' + url + '}{' + tex(entry['title']) + '}'
            note = r'{\fontsize{8}{9.2}\selectfont ' + tex(entry['citation_note']) + r'\par}' if entry.get('citation_note') else ''
            blocks.append(r'\cvpub{' + title + '}{' + ', '.join(authors) + '}{' + tex(entry['venue_label']) + '}{' + note + '}')
    blocks.append('% Publications end')
    source, count = re.subn(r'% Publications start.*?% Publications end', lambda _: '\n'.join(blocks), source, flags=re.DOTALL)
    if count != 1: raise RuntimeError('Expected one publication block in uploads/resume.tex')
    return source


def render_sitemap(data: dict) -> str:
    sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    pages = sorted(set([ROOT / "index.html"] + list((ROOT / "publication").glob("**/index.html")) + list((ROOT / "platform").glob("**/index.html"))
                       + [ROOT / e['page_url'].lstrip('/') / 'index.html' for e in data['entries']]))
    for page in pages:
        if "page" in page.relative_to(ROOT).parts:
            continue
        path = page.parent.relative_to(ROOT).as_posix()
        url = SITE_URL + "/" + (path + "/" if path != "." else "")
        ET.SubElement(ET.SubElement(sitemap, "url"), "loc").text = url
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(sitemap, encoding="unicode") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check for drift without modifying files")
    args = parser.parse_args()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    index_html = INDEX_PATH.read_text(encoding="utf-8")
    sections = list(SECTION_PATTERN.finditer(index_html))
    if len(sections) != 1:
        raise RuntimeError("Expected exactly one Publications section in index.html")
    rendered_section = render_section(data, sections[0].group())

    updated = SECTION_PATTERN.sub(lambda _: rendered_section, index_html)
    archive_path = ROOT / "publication/index.html"
    archive = archive_path.read_text(encoding="utf-8")
    archive_pattern = re.compile(r"<!-- Publication archive start -->.*?<!-- Publication archive end -->", re.DOTALL)
    if len(archive_pattern.findall(archive)) != 1:
        raise RuntimeError("Expected exactly one publication archive block")
    outputs = {
        INDEX_PATH: updated,
        archive_path: archive_pattern.sub(lambda _: render_archive(data), archive),
        ROOT / "index.json": render_search(data, updated),
        ROOT / "index.xml": render_feed(data),
        ROOT / "publication/index.xml": render_feed(data),
        ROOT / "sitemap.xml": render_sitemap(data),
        ROOT / "publication/cite.bib": '\n'.join(render_bibtex(entry) for entry in data['entries']),
        ROOT / "platform/index.html": render_platform_archive(updated, (ROOT / 'platform/index.html').read_text(encoding='utf-8')),
        ROOT / "uploads/resume.tex": render_cv(data, (ROOT / 'uploads/resume.tex').read_text(encoding='utf-8')),
    }
    for entry in data["entries"]:
        page = ROOT / entry["page_url"].lstrip("/") / "index.html"
        source = page.read_text(encoding="utf-8") if page.exists() else (ROOT / 'templates/publication.html').read_text(encoding='utf-8')
        outputs[page] = render_detail(entry, source)
        outputs[page.parent / 'cite.bib'] = render_bibtex(entry)
    outputs = {path: '\n'.join(line.rstrip() for line in content.splitlines()) + '\n'
               for path, content in outputs.items()}
    changed = [path for path, content in outputs.items()
               if not path.exists() or path.read_text(encoding="utf-8") != content]
    if args.check:
        if changed:
            print("Generated content is out of date: " + ", ".join(str(path.relative_to(ROOT)) for path in changed))
            print("Run python3 scripts/render_featured_publications.py")
            return 1
        print("Publication cards, archive, search, feeds and sitemap are in sync.")
        return 0
    for path in changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(outputs[path], encoding="utf-8")
    print("Updated publication content and metadata; existing theme and section layout preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

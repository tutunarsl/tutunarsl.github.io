#!/usr/bin/env python3
"""Check local links, assets, metadata, search entries and generated publication data."""

from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET
from render_featured_publications import display_authors, HomepageSearch

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {'www.turcantuna.com', 'turcantuna.com', 'tutunarsl.github.io'}


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids = []
        self.references = []
        self.canonical = []
        self.images_without_alt = []
        self.images = []
        self.filter_fragments = set()
        self.json_blocks = []
        self.current_json = None
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        line = self.getpos()[0]
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        for key in ('href', 'src', 'data-filename'):
            if attrs.get(key):
                self.references.append((attrs[key], line))
        for match in re.finditer(r'url\([\s\"\x27]*([^\)\"\x27]+)', attrs.get('style', '')):
            self.references.append((match[1], line))
        if tag == 'meta' and attrs.get('property') in ('og:image', 'twitter:image'):
            self.references.append((attrs.get('content', ''), line))
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical.append(attrs.get('href', ''))
        if tag == 'img' and 'alt' not in attrs:
            self.images_without_alt.append(line)
        if tag == 'img':
            self.images.append(attrs.get('src', ''))
        if tag == 'option' and attrs.get('value', '').startswith('.pubtype-'):
            self.filter_fragments.add(attrs['value'][len('.pubtype-'):])
        if tag == 'script' and attrs.get('type') in ('application/json', 'application/ld+json'):
            self.current_json = [line, '']

    handle_startendtag = handle_starttag

    def handle_data(self, data):
        if self.current_json is not None:
            self.current_json[1] += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.current_json is not None:
            self.json_blocks.append(self.current_json)
            self.current_json = None


def main():
    paths = [ROOT / 'index.html', ROOT / '404.html']
    paths += list((ROOT / 'publication').rglob('*.html'))
    paths += list((ROOT / 'platform').rglob('*.html'))
    pages = {path.resolve(): Page(path) for path in paths}
    errors = []
    checked = 0

    def check_reference(source, value, line=0):
        nonlocal checked
        if not value or value in ('#', '/') or value.startswith(('mailto:', 'tel:', 'data:', 'javascript:')):
            return
        source_url = '/' + source.relative_to(ROOT).as_posix()
        url = urlsplit(urljoin('https://www.turcantuna.com' + source_url, value))
        if url.hostname not in HOSTS:
            return
        target = (ROOT / unquote(url.path).lstrip('/')).resolve()
        if target.is_dir():
            target = target / 'index.html'
        checked += 1
        label = str(source.relative_to(ROOT)) + (':' + str(line) if line else '')
        if not target.is_file():
            errors.append(label + ': missing ' + value)
        elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids and url.fragment not in pages[target].filter_fragments:
            errors.append(label + ': missing anchor ' + value)

    for path, page in pages.items():
        for line, content in page.json_blocks:
            try:
                json.loads(content)
            except json.JSONDecodeError as error:
                errors.append('{}:{}: invalid JSON: {}'.format(path.relative_to(ROOT), line, error))
        for identifier, count in Counter(page.ids).items():
            if count > 1:
                errors.append(str(path.relative_to(ROOT)) + ': duplicate ID ' + identifier)
        for value, line in page.references:
            check_reference(path, value, line)
        if '/page/' not in path.as_posix() and (len(page.canonical) != 1 or not page.canonical[0].startswith('https://www.turcantuna.com/')):
            errors.append(str(path.relative_to(ROOT)) + ': expected one canonical URL on www.turcantuna.com')
        for line in page.images_without_alt:
            errors.append(str(path.relative_to(ROOT)) + ':' + str(line) + ': image needs an alt attribute')
    for css in (ROOT / 'css').glob('*.css'):
        for match in re.finditer(r'url\([\s\"\x27]*([^\)\"\x27]+)', css.read_text(encoding='utf-8')):
            check_reference(css, match[1])
    for entry in json.loads((ROOT / 'index.json').read_text(encoding='utf-8')):
        check_reference(ROOT / 'index.json', entry['relpermalink'] or '/')
    for icon in json.loads((ROOT / 'manifest.webmanifest').read_text(encoding='utf-8'))['icons']:
        check_reference(ROOT / 'manifest.webmanifest', icon['src'])
    for path in (ROOT / 'sitemap.xml', ROOT / 'index.xml', ROOT / 'publication/index.xml'):
        try:
            tree = ET.parse(path)
            for element in tree.iter():
                if element.tag.rsplit('}', 1)[-1] in ('loc', 'link', 'guid') and element.text:
                    check_reference(path, element.text)
        except ET.ParseError as error:
            errors.append(str(path.relative_to(ROOT)) + ': invalid XML: ' + str(error))
    catalog = json.loads((ROOT / 'data/featured_publications.json').read_text(encoding='utf-8'))['entries']
    search = json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))
    for key in ('id', 'research_id', 'page_url'):
        if len({entry[key] for entry in catalog}) != len(catalog):
            errors.append('Publication catalog has duplicate ' + key)
    indexed_publications = [entry['relpermalink'] for entry in search if entry.get('type') == 'publication']
    if Counter(indexed_publications) != Counter(entry['page_url'] for entry in catalog):
        errors.append('Search must contain each publication exactly once')
    for entry in catalog:
        names = [a['name'] for a in entry['authors']]
        is_research_paper = entry['status'] in ('published', 'accepted')
        if entry.get('featured') and not is_research_paper:
            errors.append(entry['id'] + ': featured entries must be published or accepted research papers')
        if is_research_paper:
            if not entry.get('abstract') or entry.get('abstract_kind') != 'summary' or not entry.get('abstract_source'):
                errors.append(entry['id'] + ': missing sourced abstract summary')
            figure = entry.get('image', {})
            if not all(figure.get(key) for key in ('src', 'alt', 'width', 'height', 'caption', 'credit', 'source_url')):
                errors.append(entry['id'] + ': missing figure or attribution')
        shared = set(entry.get('equal_contributors', []))
        shown = [a['name'] for a in display_authors(entry)]
        if not shared.issubset(names) or len(names) != len(set(names)):
            errors.append(entry['id'] + ': invalid author credits')
        if 'Turcan Tuna' in shared and next(n for n in shown if n in shared) != 'Turcan Tuna':
            errors.append(entry['id'] + ': shared-contribution display order is incorrect')
        if any(shown[i] != name for i, name in enumerate(names) if name not in shared):
            errors.append(entry['id'] + ': display moved an author outside the shared group')
        page = (ROOT / entry['page_url'].lstrip('/') / 'index.html').resolve()
        if page not in pages:
            errors.append(entry['id'] + ': missing detail page')
            continue
        if is_research_paper:
            content = page.read_text(encoding='utf-8')
            if 'class="pub-abstract"' not in content or entry['abstract_source'] not in content:
                errors.append(entry['id'] + ': detail page is missing its abstract or source')
            if entry.get('image', {}).get('src') not in pages[page].images:
                errors.append(entry['id'] + ': detail page is missing its primary figure')
        article = next((json.loads(block) for _, block in pages[page].json_blocks
                        if json.loads(block).get('@type') == 'ScholarlyArticle'), {})
        if [author['name'] for author in article.get('author', [])] != names:
            errors.append(entry['id'] + ': scholarly metadata must retain published author order')
        citation = (page.parent / 'cite.bib').read_text(encoding='utf-8')
        author_field = re.search(r'^  author = \{(.*)\},$', citation, re.MULTILINE)
        expected = ' and '.join(a.get('citation_name', a['name']) for a in entry['authors'])
        if not author_field or author_field[1] != expected:
            errors.append(entry['id'] + ': BibTeX must retain all authors in published order')
        if entry.get('doi') and ('doi = {' + entry['doi'] + '}') not in citation:
            errors.append(entry['id'] + ': missing DOI in citation')
        if pages[page].canonical != ['https://www.turcantuna.com' + entry['page_url']]:
            errors.append(entry['id'] + ': incorrect canonical URL')
    home = HomepageSearch(); home.feed((ROOT / 'index.html').read_text(encoding='utf-8'))
    platform_archive = (ROOT / 'platform/index.html').read_text(encoding='utf-8')
    if platform_archive.count('media stream-item view-compact') != len(home.platforms):
        errors.append('Platform archive and homepage inventory differ')
    if '0001' in platform_archive:
        errors.append('Platform archive contains a placeholder date')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/render_featured_publications.py'), '--check'])
    if result.returncode:
        errors.append('Generated publication content is out of date')
    if errors:
        print('\n'.join(errors))
        print('{} checks failed.'.format(len(errors)))
        return 1
    print('Checked {} pages, {} local references and {} publication records. Links, assets, metadata, author credits and search coverage pass.'.format(len(pages), checked, len(catalog)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

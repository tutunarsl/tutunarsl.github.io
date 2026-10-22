# Publication catalog

Edit `data/featured_publications.json`, then run:

```sh
python3 scripts/render_featured_publications.py
python3 scripts/check_site.py
```

Each entry contains:

- `id`: unique letters, numbers, `_` or `-`.
- `title`, `summary`, `date`: displayed text.
- `research_id`: stable identifier used in bibliography keys.
- `year`: the volume/proceedings year, as an integer; explain accepted or preprint status separately.
- `publication_type`: `journal`, `conference`, `workshop`, `preprint` or `correction`.
- `status`: `published`, `accepted` or `preprint`.
- `featured`: whether to show the existing homepage card; all entries appear in the archive.
- `authors`: full names in **published order**, optional affiliation, `citation_name` (BibTeX family-name disambiguation) and `highlighted` flag.
- `equal_contributors`: names explicitly marked as equal contributors in the paper. Display puts Turcan Tuna first within that group and marks all its members. BibTeX and scholarly metadata retain published order.
- `venue`, `venue_label`: canonical venue name and full display citation.
- `venue_html`: trusted venue markup, including optional links and award text.
- `doi`, `arxiv_id`, `volume`, `issue`, `pages`, `article_number`: verified citation fields where applicable.
- `citation_note`: acceptance/date qualifications or correction context.
- `source_urls`: primary sources supporting the record.
- `page_url`: local publication route; the generator creates new detail pages from `templates/publication.html`.
- `image`: required only for featured cards: `src`, `alt`, `height`, `width`, and optional inline `style`.
- `buttons`: a `label` with either `href` or `type: "cite"` and `filename`; optional `target_blank`.
- `metadata_divider` and `author_icon_spacing`: preserve the existing card typography.

For a new entry, add its verified data and run the generator. It creates the detail page and citation file. Label actual PDF links “PDF” and publisher landing pages “Paper”.

The generator replaces marked publication cards on the homepage while preserving its section layout. It also updates the archive, authors and metadata on detail pages, individual and aggregate BibTeX, the marked publication block in `uploads/resume.tex`, `index.json`, the feeds and sitemap. Original detail-page abstracts and images are retained. Rebuild `uploads/resume.pdf` after publication changes using the README instructions.

The search index includes homepage updates, experience, robot cards, biography and contact text, plus platform pages and publication records. Run the generator after editing that content too.

The introductory notice remains in `index.html`; `section_title` controls the generated heading. Keep the publication markers in place. The platform archive is also regenerated from the existing homepage robot cards.

Check for stale generated output without modifying files:

```sh
python3 scripts/render_featured_publications.py --check
```

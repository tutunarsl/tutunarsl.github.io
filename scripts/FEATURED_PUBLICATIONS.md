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
- `publication_type`: `journal`, `conference`, `workshop` or `preprint`.
- `status`: `published`, `accepted` or `preprint`.
- `featured`: whether to show the existing homepage card; all entries appear in the archive.
- `abstract`: a concise, original summary of the paper's abstract, displayed as “Abstract summary”; `abstract_kind` is `summary` and `abstract_source` links to the original abstract or paper. Keep reported results and their evaluation scope faithful to the source.
- `authors`: full names in **published order**, optional affiliation, `citation_name` (BibTeX family-name disambiguation) and `highlighted` flag.
- `equal_contributors`: names explicitly marked as equal contributors in the paper. Display puts Turcan Tuna first within that group and marks all its members. BibTeX and scholarly metadata retain published order.
- `venue`, `venue_label`: canonical venue name and full display citation.
- `venue_html`: trusted venue markup, including optional links and award text.
- `doi`, `arxiv_id`, `volume`, `issue`, `pages`, `article_number`: verified citation fields where applicable.
- `citation_note`: acceptance/date qualifications.
- `source_urls`: primary sources supporting the record.
- `page_url`: local publication route; the generator creates new detail pages from `templates/publication.html`.
- `image`: required for published and accepted research papers: local `src`, descriptive `alt`, intrinsic `height` and `width`, `caption`, `credit`, `source_url`, optional `source_asset` for provenance, and optional inline `style`. Use the paper's figure or official project visual, with its complete aspect ratio and legible labels. Store only the web-ready asset in the repository.
- `buttons`: a `label` with either `href` or `type: "cite"` and `filename`; optional `target_blank`.
- `metadata_divider` and `author_icon_spacing`: preserve the existing card typography.

For a new entry, add its verified data and run the generator. It creates the detail page and citation file. Label actual PDF links “PDF” and publisher landing pages “Paper”.

The generator replaces marked publication cards on the homepage while preserving its section layout, ordered newest year first. Published and accepted research papers currently appear there; preprints remain in the full archive. It also updates the archive, detail-page abstracts, figures and metadata, citations, CV publication text, search, feeds and sitemap. The five original detail-page layouts and their additional figures are retained. Rebuild `uploads/resume.pdf` after changes to citation fields using the README instructions.

The search index includes homepage updates, experience, robot cards, biography and contact text, plus platform pages and publication records. Run the generator after editing that content too.

The introductory notice remains in `index.html`; `section_title` controls the generated heading. Keep the publication markers in place. The platform archive is also regenerated from the existing homepage robot cards.

Check for stale generated output without modifying files:

```sh
python3 scripts/render_featured_publications.py --check
```

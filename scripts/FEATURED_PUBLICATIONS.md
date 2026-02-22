# Featured Publications Macro

## Files

- `data/featured_publications.json`: publication data source.
- `scripts/render_featured_publications.py`: renders and injects the section into `index.html`.

## Add a New Publication

1. Open `data/featured_publications.json`.
2. Add one object to `entries` with:
   - `id`
   - `authors` (name + affiliation, optional `highlighted`)
   - `date`
   - `venue_html`
   - `page_url`
   - `image` (`src`, `height`, `width`, optional `style`, `alt`)
   - `title`
   - `summary`
   - `buttons` (`label`, and either `href` or `type: "cite"` + `filename`)
3. Regenerate the section:

```bash
python3 scripts/render_featured_publications.py
```

The script updates only the block between:

- `<!-- Publications start -->`
- `<!-- Publications end -->`

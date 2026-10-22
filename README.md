# Turcan Tuna’s website

Static website for [www.turcantuna.com](https://www.turcantuna.com), hosted on GitHub Pages. The existing Wowchemy styling and page layouts are maintained directly in this repository.

Dark mode is the default for visitors without a saved theme choice. The display menu remembers Light, Dark, or Auto; Auto follows the device setting.

## Preview

From the repository root, run:

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

Open <http://localhost:8080>. No package installation or site build is required.

## Edit

- Homepage text and layout: `index.html`.
- Complete publication catalog, abstract summaries and credited figures: `data/featured_publications.json`. See [the publication guide](scripts/FEATURED_PUBLICATIONS.md); `featured` selects homepage cards.
- Generated publication pages and BibTeX: `publication/<name>/`; new pages use `templates/publication.html`.
- CV source: `uploads/resume.tex`; downloadable CV and historical project portfolio: `uploads/`.
- Domain configuration: `CNAME`.

After editing homepage text, publication data, or adding/removing a page:

```sh
python3 scripts/render_featured_publications.py
python3 scripts/check_site.py
```

The generator updates publication cards, the complete archive, detail-page metadata, citations, CV publication text, search, feeds, and sitemap. The platform archive uses the homepage's robot inventory. Search entries come from the current homepage, platform pages, and publication data. The checker validates local references, structured data, author credit, canonical URLs, and generated-content consistency. Both scripts use only Python’s standard library.

After changing the CV source or publication data, rebuild the downloadable CV with XeLaTeX (TeX Live, Source Sans Pro, Roboto and Font Awesome 5):

```sh
mkdir -p /tmp/turcantuna-cv-build
xelatex -interaction=nonstopmode -halt-on-error -output-directory=/tmp/turcantuna-cv-build uploads/resume.tex
cp /tmp/turcantuna-cv-build/resume.pdf uploads/resume.pdf
```

Keep the CV's review date current and inspect the PDF after rebuilding. Build intermediates stay outside the repository.

## Publish

Commit the HTML, data, and generated metadata together, then merge into `master` and push to the existing GitHub Pages repository. Keep `CNAME` set to `www.turcantuna.com`.

Existing attribution and image credits are retained in the website.

The existing external card images are stored locally to avoid broken remote image hosts. Originals: [MIT SPARK](https://web.mit.edu/sparklab/assets/images/spark-shard.png), [Unitree B2-W](https://shop.unitree.com/cdn/shop/files/1_01_3b15de92-3235-4675-8162-6adb231be57f_1024x1024.jpg?v=1718273847), [Unitree A2-PRO](https://shop.unitree.com/cdn/shop/files/01_7dd342a4-fbbc-497e-b805-25c8ca8188ce_1024x1024.jpg?v=1769775047), and [LimX TRON 1](https://limx-video-oss.limxdynamics.com/limx-website/products/tron1/home/1.png).

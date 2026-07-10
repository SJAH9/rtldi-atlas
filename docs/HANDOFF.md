# RTLDI Atlas Handoff Notes

Last updated after release commit `bb90b15` on `main`.

## Current Git State

- Branch: `main`
- Remote: `origin/main`
- Latest commit: `bb90b15 Release v2026.8.3 cohesive atlas design`
- Latest tag: `v2026.8.3`
- Tag pushed: yes
- Branch pushed: yes

Untracked local scratch files intentionally not committed:

- `exported.md`
- `outputs/atlas/rtl_di_atlas_un_region_eta_review_2026.csv`
- `outputs/atlas/rtl_di_atlas_un_region_eta_review_2026.xlsx`
- `src/generate_region_eta_review_atlas.py`

## Release Documentation

README now includes direct deployed links:

- HTML Atlas: `https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/`
- Interactive Map: `https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/global_interactive.html`
- Full Data View: `https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/full_data.html`

Release notes are in:

- `docs/releases/v2026.8.3.md`

Important caveat: the GitHub Release page itself was not created from this environment because `gh` is not installed and no GitHub token is available. The annotated tag and release notes are pushed and ready for manual GitHub release creation.

## Recent Work Completed

- Cohesive design pass across print atlas, HTML atlas, Full Data View, interactive map, choropleths, and RDF export.
- Print nation pages redesigned with:
  - stronger country identity header
  - RTLP score badge
  - nine-lever status strip
  - cleaner metric cards
  - refreshed country map styling
- Choropleths updated with:
  - shared RTLDI atlas R scale
  - softer ocean/land context
  - graticules
  - clearer coastline/country boundary hierarchy
  - small-state locator layer and notes
- Full Data View updated so:
  - `RTLP` is the second column
  - country names link to `global_interactive.html?country=ISO3`
  - table styling matches the broader atlas design language
- Interactive map supports:
  - `?country=ISO3`
  - `?iso3=ISO3`
  - `#ISO3`
- RDF/XML linked open data export remains generated at:
  - `outputs/html-atlas/rtldi_atlas_2026.rdf`

## Verification Already Run

Commands run successfully:

```bash
python3 -m src.generate_enclosure_map
python3 -m src.generate_atlas_ebook
python3 -m src.generate_html_atlas
python3 -m py_compile src/map_geometry.py src/generate_enclosure_map.py src/generate_html_atlas.py src/generate_atlas_ebook.py src/generate_rdf_atlas.py
```

Verified outputs:

- Full ebook: `237` pages.
- Nation profiles PDF: `194` pages.
- Full Data View: `193` rows.
- Full Data View: `193` country links.
- RDF/XML: `193` `qb:Observation` records.
- Page 8 global total remains `$15.87T`.

Visual spot checks:

- Global choropleth after new map styling.
- Regional SVG previews for Caribbean, Micronesia, and Western Europe.
- Print nation pages for Afghanistan and Albania.

## Suggested Next Steps

1. Create the GitHub Release page for tag `v2026.8.3`.
2. Paste `docs/releases/v2026.8.3.md` into the release body.
3. Attach `outputs/atlas/RTLDI_ATLAS_2026_ebook.pdf`.
4. If continuing design work, preserve the single canonical generation path:
   - `src.generate_atlas_ebook.prepare_atlas_data()`
   - `src.generate_atlas_ebook`
   - `src.generate_html_atlas`
   - `src.generate_enclosure_map`

# RTLDI Atlas Handoff Notes

Last updated while preparing release `v2026.8.7` on `main`.

## v2026.8.7 Work

- Rebuilt the complete print Atlas as a 290-page, five-part A4 publication.
- Added continuous folios, PDF outlines, metadata, print-safe margins, and recto/verso section alignment.
- Converted full-page web/source QR gateways into section title pages.
- Added compact QR symbols beside every visible print URL.
- Added publication record, rights, citation, authorship, production disclosure, source ownership, expanded glossary, credits, and colophon.
- Added the causal-projection/outer-enclosure page with whistleblower protection as the worked example.
- Integrated the 29-page Eurozone module into the common design and sequence.
- Verified 193 nation profiles, 290 total pages, all URL-to-QR annotations, strict PDF parsing, Ghostscript rendering, and tests.
- Release notes: `docs/releases/v2026.8.7.md`.

## v2026.8.6 Work

- Corrected the executable crosswalk so levers 3, 4, 6, and 7 use distinct V-Dem signals: `v2clkill`, `v2xcl_acjst`, `v2x_clphy`, and `v2clrspct`.
- Unified component breakdown and aggregate score generation in `src/build_atlas.py`; the master table and national JSON now derive from the same nine records.
- Verified the old representation was exactly equivalent to seven unique signals with preserved two-ninths weights for the two repeated pairs; maximum score delta `0.0`.
- Corrected 65 national RTLP scores and recalculated the population-weighted regression to eta `0.356`, operationally `0.36` under the unchanged 25% cap.
- Updated the bounded global capital-exclusion estimate from `$15.87T` to `$19.29T`.
- Regenerated all print, web, map, linked-data, Eurozone, spreadsheet, and component outputs. The complete ebook remains 278 pages.
- Added `tests/test_lever_pipeline.py` to enforce distinct fields and exact nine-record score aggregation.
- Release notes: `docs/releases/v2026.8.6.md`.

## v2026.8.4 Work

- Added `src/atlas_evidence.py` as the shared executable crosswalk, regression, and provenance layer.
- Added generated web pages: `levers.html`, `regression.html`, `vdem.html`, and `world_bank.html`.
- Mirrored those evidence sections in print before the glossary.
- Ebook order is front, regions, 193 nation profiles, 27-page Eurozone report, evidence/data pages, then glossary and credits; total is 278 pages.
- Published scores identify V-Dem Full+Others v15 with 2024 observations. The current update workflow targets v16; exact historical replication is limited because the raw v15 checksum is not committed.
- Corrected regression yields eta=0.356 (n=187, robust p=0.0177, weighted R2=0.242); the operational coefficient is 0.36 and remains bounded by the 25% cap.
- Release `v2026.8.4` should attach only `outputs/atlas/RTLDI_ATLAS_2026_ebook.pdf`.

## Prior Published Git State

- Branch: `main`
- Remote: `origin/main`
- Previous release commit: `bb90b15 Release v2026.8.3 cohesive atlas design`
- Previous release tag: `v2026.8.3`
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

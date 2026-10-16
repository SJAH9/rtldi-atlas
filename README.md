# RTLDI ATLAS — UN Member States

**Project**: Build a comprehensive, reproducible **RTLDI ATLAS** of all 193 United Nations Member States using the Right to Life Deficit Index (RTLDI) from the source document (Zenodo 10.5281/zenodo.19468550), extended to quantify **capital exclusions** — the lost potential GDP where capital is excluded from the economy because the nine protections necessary for it to operate are not present. The corrected 2026 atlas estimates `$19.29T` in bounded annual capital exclusions.

> Sid J.A. Hubbard, *Causality and Attraction: A Continuum of Steady States* (Version 3, May 2026).  
> DOI: [10.5281/zenodo.19468550](https://doi.org/10.5281/zenodo.19468550)

## License

The **RTLDI Atlas** in this repository (code, data processing pipeline, documentation, and generated outputs) is licensed under the [MIT License](LICENSE).

**Important clarification**: Only the RTLDI Atlas materials in this repository are covered by the MIT License. The underlying theoretical framework and content from the book *Causality and Attraction: A Continuum of Steady States* remain under their original copyright (CC BY-NC-ND 4.0) and are **not** licensed under this MIT License.

## Releases

### v2026.8.8: World Bank Eurozone data in the print Atlas

The featured update restores the Eurozone report's originally intended data
basis: World Bank data for the euro-area member states, in euros. The earlier
report reused the global USD baselines; this release calculates the Eurozone
report directly from the World Bank's euro-denominated national observations.
It is a source-data correction, not a currency-symbol replacement.

The Eurozone report presents all monetary figures in euros, including totals,
member-state profiles, lever allocations, and trend text. It uses the World Bank's
[GDP per capita in current local currency](https://data.worldbank.org/indicator/NY.GDP.PCAP.CN)
for the 21 members, verified as Euro in World Bank country metadata, with
matching-year population. There is no USD conversion. R, eta, the cap, the global
USD atlas, and the web atlas remain unchanged. GDP baselines use the latest
matched observation in 2023-2025; profiles identify the actual year.
The cached source responses and currency metadata are in
`data/raw/wb_eurozone_eur_2026.json`; refresh with
`python -m src.generate_eurozone_atlas --refresh-wb`.
Eurozone CSV and JSON outputs explicitly label EUR amounts. Bulgaria's pre-2026
baseline is retrospectively euro-denominated by the World Bank, not actual euros
in circulation at that time. The report retains that qualification; its 21-member
model sum is not an official historical euro-area GDP aggregate.

The Eurozone section's QR gateway now opens the standalone Eurozone PDF at a
version-specific release URL, rather than the web Atlas landing page. The
release includes both the complete print Atlas and the standalone report.

See [the v2026.8.8 release notes](docs/releases/v2026.8.8.md).

All releases (including the full PDF ebook as an asset) are available on the [GitHub Releases page](https://github.com/SJAH9/rtldi-atlas/releases).

## Web Atlas

The repository is configured for GitHub Pages. The root `index.html` redirects to the generated HTML atlas at `outputs/html-atlas/index.html`, so the Pages site opens directly into the atlas instead of the source repository layout.

Use GitHub Pages with the repository root as the static site source. The HTML atlas, regional map assets, interactive global map, and linked PDF remain available under the same relative paths used locally.

Direct deployed atlas links:

- [Installable Atlas App](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/app.html)

- [HTML Atlas](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/)
- [Interactive Map](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/global_interactive.html)
- [Full Data View](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/full_data.html)
- [Nine Levers and Crosswalk](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/levers.html)
- [GDP Regression and Eta](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/regression.html)
- [V-Dem Data Guide](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/vdem.html)
- [World Bank Data Guide](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/world_bank.html)
- [About, Authorship, and Citation](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/about.html)

### Web App Frame and Installation

The web Atlas opens inside a thin, common navigation frame with a persistent
header, footer, and fullscreen control. Navigation between Atlas pages stays
inside that frame, including in fullscreen. Existing country links and source
links remain available. PDFs and external sites open separately.

The app includes a scoped web manifest, 192/512-pixel and maskable icons,
Apple touch icon, service worker, browser installation prompt support, and an
offline fallback. Microsoft Edge can recognize it as an installable app; the
browser's own install/add-to-phone controls remain available. The in-app install
button appears only when the browser supplies an installation prompt.
See [Microsoft's PWA guidance](https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/).

The service worker uses network-first fetching, caches visited local views and
assets, and stays within `outputs/html-atlas/`. It does not cache the print PDFs
or intercept other projects on the GitHub Pages origin. Unvisited views and
external map/font/style dependencies can still require a connection; full
offline operation is not claimed. No analytics or user classification is added.

Install or update the frame without rebuilding any Atlas data:

```bash
python -m src.generate_web_app
python -m unittest discover -s tests
```

The normal HTML build also installs it automatically. For browser checks, run a
local HTTP server at the repository root and use `scripts/check_web_app.py`
(requires Playwright and Chromium). The script checks desktop/mobile layouts,
fullscreen continuity, navigation/history, map paths, source deep links,
manifest/service worker, offline cached access, and the install control. A view
can be opened without the frame using `?plain=1`.

### v2026.8.7 (Print atlas publication design overhaul)

This release rebuilds the Atlas as a cohesive, print-ready reference publication while preserving the canonical data pipeline and all 193 national profiles.

- Reorganizes the 290-page A4 ebook into five clearly navigable parts with continuous folios, PDF outlines, metadata, and deliberate recto/verso alignment.
- Turns the large web and repository QR gateways into section title pages for regional summaries, nation profiles, Eurozone maps, and glossary/source access.
- Pairs every visible print URL with a compact, clickable QR code while retaining the printed destination.
- Adds conventional publication matter: rights, citation, authorship and production disclosure, source ownership, expanded glossary, credits, and print colophon.
- Adds a causal-projection page explaining movement from outer enclosures, with whistleblower protection as a worked example and a clear boundary between enabled pathways and guaranteed timing.
- Integrates the Eurozone report into the same editorial sequence and visual language as the global and national Atlas.
- The release contains one PDF asset only: the complete 290-page `RTLDI_ATLAS_2026_ebook.pdf`.

See [the complete v2026.8.7 release notes](docs/releases/v2026.8.7.md) for the publication architecture and validation record.

### v2026.8.5 (Refined web atlas navigation and attribution)

This release brings every web-atlas view into one coherent, responsive information architecture.

- Adds consistent primary and contextual navigation across the overview, map, Full Data, levers, regression, source guides, and About page.
- Adds automatic local-time day/night presentation to every page, including coordinated Plotly map styling.
- Strengthens drill-down paths from global lever summaries, table headers, and country profiles into the underlying lever methodology.
- Adds a conventional About page documenting the Atlas as a Level 4 Nested Causal Modelling Intervention, its origins, authorship, production disclosure, open-source license, and citation.
- Adds field-level citation guidance to Full Data, separating RTLDI Project outputs from V-Dem and World Bank source observations.
- Adds a restrained project footer whose RTLDI Atlas Project identity links to the About page.
- Verified all eight pages in desktop and mobile layouts, day and night modes, with 193 Full Data rows and no missing internal links.
- The release contains one PDF asset only: the complete `RTLDI_ATLAS_2026_ebook.pdf`.

### v2026.8.4 (Transparent levers, regression, and data provenance)

This release exposes the evidence behind the atlas as first-class web and print content.

- Adds a separate nine-lever page with global annual capital exclusions, exact source fields, binary thresholds, proxy rationale, crosswalk caveats, and the NCM Isolated Entity definition.
- Adds a reproducible GDP regression page reporting the canonical population-weighted model, robust uncertainty, statistical significance, explicit `eta`, descriptive comparators, and a non-significant one-year growth falsification check.
- Adds dedicated V-Dem and World Bank WDI provenance/download pages, separating the published v15 score source from the current v16 update workflow.
- Mirrors all four evidence sections in the print back matter before the glossary.
- Corrects older prose to disclose that released levers 3/6 reuse `v2clkill` and levers 4/7 reuse `v2xcl_acjst`.
- Updates the 27-page Eurozone report and concatenates it after the 193 nation profiles and before the evidence/data pages.
- The release contains one PDF asset only: the complete 278-page `RTLDI_ATLAS_2026_ebook.pdf`.

### v2026.8.3 (Cohesive atlas design and linked data views)

This release brings the print atlas, web atlas, interactive map, full data view, and linked-data export into a more cohesive information-design language while preserving the canonical single data pipeline.

- Redesigned print nation pages with stronger country headers, RTLP score badges, nine-lever status strips, cleaner metric hierarchy, and refreshed country-map styling.
- Updated global, regional, and country choropleths with the shared RTLDI atlas R scale, softer ocean/land context, graticules, stronger boundary hierarchy, and small-state locator notes.
- Improved the HTML atlas landing page and Full Data View so they share the same atlas visual language.
- Full Data View now lists `RTLP` as the second column and keeps country names linked directly to the interactive country viewer.
- Interactive map now opens country panels directly from `?country=ISO3`, `?iso3=ISO3`, or `#ISO3`.
- RDF/XML linked open data export remains published as `outputs/html-atlas/rtldi_atlas_2026.rdf` and linked from the HTML pages.
- Verified the atlas still generates from the data pipeline: 237-page PDF ebook, 194-page nation section, 193 Full Data rows, 193 country links, 193 RDF observations, and the page-8 global total of `$15.87T`.

Deployed views:

- [HTML Atlas](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/)
- [Interactive Map](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/global_interactive.html)
- [Full Data View](https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/full_data.html)

Generate the full current atlas:

```bash
python -m src.generate_enclosure_map
python -m src.generate_atlas_ebook
python -m src.generate_html_atlas
```

### v2026.8.2 (Eurozone report)

This release adds a focused **RTLDI 2026 Eurozone Capital Exclusion Map** as a scoped derivative of the UN member-state atlas.

- New Eurozone PDF: `outputs/atlas/RTLDI_EUROZONE_CAPITAL_EXCLUSION_MAP_2026.pdf`.
- New Eurozone data outputs: `outputs/atlas/rtl_di_atlas_eurozone_2026.csv` and `outputs/atlas/rtl_di_atlas_eurozone_summary_2026.json`.
- Scope: 21 euro-area member states as of 2026, including Bulgaria from January 1, 2026; excludes non-EU microstates using the euro by monetary agreement.
- Uses the corrected canonical global atlas model: `eta = 0.36` with the 25% contextual cap, so the Eurozone figures remain directly comparable to the main UN atlas.
- Current Eurozone total capital exclusions: approximately `$887.1B` annually.

Generate it after the main atlas data exists:
```bash
python -m src.generate_eurozone_atlas
```

See the [full Releases page](https://github.com/SJAH9/rtldi-atlas/releases) for v2026.8.1 and earlier.

### v2026.8.1 (France map geometry fix)

Patch release correcting France map geometry in Plotly choropleths:

- France no longer appears as a colored territory in South America on the global interactive map.
- Western Europe, France-only, and Eurozone fitted map views stay framed in Europe instead of being distorted by French Guiana.
- The print atlas PDF and HTML atlas map bundle were regenerated from the corrected map generator.

### v2026.8 (Redesigned web and PDF)

Refreshed the RTLDI Atlas presentation across print, HTML, and the interactive map:

- Redesigned full PDF visual system and regenerated the 237-page print atlas.
- Rebuilt the HTML atlas into a cleaner analytical interface.
- Upgraded the global interactive map from hover-only exploration to click-driven national detail.
- Added the root GitHub Pages landing redirect.

### v2026.7 (Capital exclusions focus)

**RTLDI** = Right to Life Deficit Index (source: Zenodo 10.5281/zenodo.19468550). Extended via population-weighted regression (25% conservative cap) to quantify **capital exclusions** — the lost potential GDP (on the order of 15 trillion dollars globally) where capital is excluded from the economy because the nine protections required for it to operate are not present.

The atlas is the map that makes this excluded capital visible so nations can activate the low-cost levers and bring it back in.

- Full PDF + self-contained HTML (front + regions) with the capital exclusions framing.
- Same 2026 data rule and 25% cap.
- Vector maps and tables now surface capital exclusions (lost potential GDP per lever and per region).
- Fully executed in the browser (vanilla JS + Tailwind):
  - Live searchable, sortable, filterable 193-nation summary table (color-coded by R threshold, region pills, click-to-filter).
  - Full static regional summaries (matching the print regions.pdf): each with vector SVG choropleth, aggregates, description, 9-lever breakdown with associated capital exclusions, and member table ending in REGIONAL TOTAL.
  - Global 9-lever breakdown of capital exclusions as clear bars.
- Perfect for NGOs, quick sharing, offline use, embedding, or hosting. The HTML + SVGs live alongside the PDF artifacts so the release contains both the print book and the web companion for the front + regions.

**To generate it yourself** (after the Quick Start data + map steps below):
```bash
python -m src.generate_html_atlas
```
This produces `outputs/html-atlas/` with everything needed for a bit-for-bit match to the released version.

The 4-part PDF system and all prior launch polish (stripped first-principles front matter, centralized "Nested Causal Modelling/Mapping" section, clean 9 levers, LaTeX removal, etc.) remain unchanged.

See the [full Releases page](https://github.com/SJAH9/rtldi-atlas/releases) for v2026.6 and earlier.

### v2026.6 (Public launch preparation, June 21 2026)

**RTLDI ATLAS 2026** — clean, instantly accessible guide for every human. Full concatenated ebook (front + regions + nations + back). The parallel LaTeX version and `src/generate_atlas_latex.py` have been removed entirely; the only supported, reproducible path is the pure Python/fpdf2 modular generator.

- Front matter radically trimmed for 2-second attention: no philosophical prose, no rambling, no distracting references, no language that invites doubt. Everything is grounded in first principles, international best practices, data hygiene, and the bibliographic network (V-Dem + World Bank).

- All justification for the atlas figures and the high global lost-GDP number now lives in one dedicated front-matter section: **"Nested Causal Modelling/Mapping"**.
  - Explains the data-science discipline used: analysis of nested causal enclosures in highly correlated graph data to identify systems that provide causal support for a target condition (maximal GDP).
  - The three laws of the continuum (always an enclosing system, a system is always enclosed, enclosures scale infinitely with an enclosure between any two).
  - R (0.0–1.0) = enclosure strength = simple average of the 9 binary indicators.
  - The 9 indicators were located by nested causal modelling of the full UN cross-section with target = maximal GDP (Sid).
  - The 25% cap is explicitly a limiting factor placed on projections to control volatility; the regression on the data alone suggested a value closer to 0.33.
  - Example for one lever: "most of the 9 levers dont carry a high annual cost, they are all force multipliers of economic velocity. ... though it may not be apparent why whistleblower protections would have a causal relationship with gdp, one must simply make their protection the law and listen for the whistles to blow and tell you where the corruption is in your government."

- The nine levers themselves are described in the modelling section as simple binary conditions (present or absent). When present, each is a low-cost force multiplier for economic velocity. Full "why GDP grows" explanations are centralized here. A user can read the 9 levers once and immediately understand the value they are missing and what concrete action (pass and enforce the law) their society can take.

- Every number in the atlas is a concrete dollar figure of capital exclusions (lost potential GDP) associated with the absence of the nine protections. The main cartographic page shows the global 9-lever breakdown of those exclusions + planet total (~15T). Nation pages and region summaries do the same. Focus is on the opportunity to bring excluded capital back in.

- Back matter is minimal and useful: data attribution, short note on the conditional nature of Malthusian outcomes, alphabetical index of terms (includes the 9 indicators), credits.

- Anticipated adversarial responses ("turtleneck sweater" correlation objections, "RTLDI can exceed entire GDP", "no credit for baseline", methodology skepticism) are baked into the design via the 25% cap, the linear floor on the Conservative Marginal Coefficient (η=0.30), the transparent single-section derivation, and the first-principles lever language. Nothing distracts or loses gatekeepers.

- 4-part modular system (front / regions / nations / back) + `--concat-only` for the release ebook remains the fast-iteration and final-release workflow.

The Quick Start below (with the required choropleth step) reproduces the attached release ebook exactly.

See the [full Releases page](https://github.com/SJAH9/rtldi-atlas/releases) for v2026.5 and earlier.

### v2026.5 and earlier

Previous releases contained longer back-matter appendices (expanded Malthus/geodesic framing) that have been trimmed for the public launch version. The 4-part system, 2026 data rule, core equation, and all per-nation/region data are continuous. The current version is the one prepared for broad accessibility.

## Goals
- Transparent, data-driven computation of RTLP (R) and RTLDI (ΔG per capita + aggregate) for every UN member.
- High-quality indicator mapping from the 9 binary questions to observable variables.
- Reproducible pipeline (fetch → clean → score → compute → export).
- Multiple outputs: master dataset (CSV/Parquet/XLSX), summaries, ranks, time series where available, methodology documentation.
- Foundation for maps, dashboards, further analysis (e.g., correlations with other indices, historical trends, scenario modeling with η). The 2026 release includes a global choropleth of enclosure strength (RTLP R).

## Core RTLDI (from source)
See [docs/RTLDI_SPEC.md](docs/RTLDI_SPEC.md) for the verbatim 9 indicators, equation, examples, and notes.

Bounded: ΔG = min( η × (1 − R) × G0 , 0.25 × G0 )
(with η ≈ 0.30 from population-weighted 2026 cross-section;
the 25% cap is the conservative adjustment from the regression)
Total capital exclusions ≈ ΔG × population

RTLDI = Right to Life Deficit Index (from the source document). Extended here via population-weighted regression (25% cap) to quantify capital exclusions — the lost potential GDP where capital is excluded from the economy because the nine protections necessary for it to operate are not present. The levers are the conditions whose activation brings that excluded capital back in.

## Project Layout
```
.
├── README.md
├── Causality_and_Attraction_Hubbard_2026V3.pdf   # source document (local copy)
├── Causality_and_Attraction_Hubbard_2026V3.txt   # full text extraction
├── data/
│   ├── raw/          # downloaded V-Dem CSVs, codebooks, WB downloads, UN list
│   └── processed/    # cleaned intermediate tables
├── src/              # Python modules: data acquisition, scoring, atlas builder
├── notebooks/        # exploration, mapping decisions, validation
├── docs/             # RTLDI_SPEC.md, methodology.md, indicator_crosswalk.md, etc.
├── outputs/
│   ├── atlas/        # final master tables, XLSX, summary stats
│   └── figures/      # charts, maps data
└── (future: tests/, docker/, etc.)
```

## For NGOs and Researchers (Recommended Use)
This toolkit is designed so NGOs and analysts can run their own RTLDI ATLAS using the **latest official open data** from V-Dem and the World Bank — no need to bundle the (large) data files in the repo.

### Quick Start (2026 data) — reproduces the full released atlas from scratch
To clone the repo, acquire the public data, and produce an atlas **identical in content and appearance** (including all choropleths) to the one attached to the latest release on this repo:

```bash
git clone https://github.com/SJAH9/rtldi-atlas.git
cd rtldi-atlas

# Install all dependencies required for data processing + PDF generation + choropleth maps
python3 -m pip install --break-system-packages pandas numpy scipy requests openpyxl wbgapi country-converter plotly kaleido fpdf2 PyPDF2 qrcode[pil]

# 1. Build the core data (uses live World Bank API + your local V-Dem CSV)
python3 -m src.build_atlas --year 2026 --eta 0.36

# 2. Generate the choropleth maps (global + 22 regional) that get embedded in the PDF
#    This step is REQUIRED to match the released atlas. It produces PNGs (for embedding),
#    a vector PDF, and an interactive HTML version.
python3 -m src.generate_enclosure_map --year 2026

# 3. Generate the print-ready PDF ebook (five modular parts + concatenated release)
#    Because the maps were generated in step 2, the PDFs will contain the actual choropleths
#    (global map in front matter, per-region maps, per-nation country views) instead of placeholders.
#    The finalizer adds continuous folios, PDF outline navigation, metadata, and print-to-web QR gateways.
python3 -m src.generate_atlas_ebook

# 4. (Optional for the launch web companion) Generate the self-contained HTML atlas
#    (front matter + all 22 regional summaries with the exact same data).
#    Produces outputs/html-atlas/index.html (open directly in a browser) plus vector SVG
#    choropleths (global + 22 regions) in outputs/html-atlas/maps/.
python3 -m src.generate_html_atlas

# 5. (Optional focused report) Generate the Eurozone capital exclusion report
#    using the canonical global eta=0.36 and the same 25% cap as the UN atlas.
python3 -m src.generate_eurozone_atlas
```

The HTML atlas is not a separate data product. It is generated from the same canonical pipeline as the PDF (`src.generate_atlas_ebook.prepare_atlas_data()`), and its nation table must contain the same 193 UN Member States as the master 2026 atlas table. Do not substitute a separately computed frontend JSON or alternate scoring pipeline for official releases.

**Exact expected outputs for a successful full reproduction (matching the current release):**
- `outputs/atlas/rtl_di_atlas_un_members_2026.csv` and `.xlsx`
- `outputs/atlas/rtl_di_atlas_summary_2026.json`
- `data/processed/rtl_di_nation_breakdown_2026.json` (and .csv)
- `outputs/figures/rtl_di_enclosure_strength_2026_choropleth.png` (and .pdf + .html)
- `outputs/figures/regional_choropleths/*.png` (22 files)
- `outputs/atlas/RTLDI_ATLAS_2026_front.pdf`
- `outputs/atlas/RTLDI_ATLAS_2026_regions.pdf`
- `outputs/atlas/RTLDI_ATLAS_2026_nations.pdf`
- `outputs/atlas/RTLDI_ATLAS_2026_ebook.pdf` (full concatenated release)
- `outputs/html-atlas/index.html` (self-contained front + regions edition with capital exclusions framing)
- `outputs/html-atlas/maps/global.svg` + 22 regional `*.svg` (vector choropleths)
- `outputs/html-atlas/data.json` (the embedded data for the HTML)
- `outputs/atlas/RTLDI_EUROZONE_CAPITAL_EXCLUSION_MAP_2026.pdf` (focused Eurozone report)
- `outputs/atlas/rtl_di_atlas_eurozone_2026.csv`
- `outputs/atlas/rtl_di_atlas_eurozone_summary_2026.json`

**Verification checklist** (run these after the commands above to confirm you have reproduced the release):
- The four main PDFs exist and `RTLDI_ATLAS_2026_ebook.pdf` is the largest.
- `outputs/figures/` contains the global choropleth PNG and the `regional_choropleths/` directory with 22 PNGs.
- `outputs/html-atlas/` exists with `index.html`, `data.json`, and `maps/` containing `global.svg` + 22 regional SVGs (plus the copied PNGs and interactive global HTML).
- Open `outputs/html-atlas/index.html` in a browser: the interactive nation table, static regional summaries (full blocks with maps, descriptions, 9-lever breakdowns, REGIONAL TOTAL), and all numbers must match the print (same R, same capital exclusions from the 25% cap regression, same 9-lever attributions). The global total of excluded capital (~15T) is the key figure.
- Open (or text-extract) the ebook and confirm it contains:
  - The "Nested Causal Modelling/Mapping" section explaining the source RTLDI extended via population-weighted regression (25% cap) to quantify capital exclusions (lost potential GDP).
  - The nine levers as the low-cost conditions whose presence allows capital to operate without being excluded.
  - Concrete high-dollar capital exclusions figures on the global cartographic page (with 9-lever breakdown + planet total), every region summary, and every nation page.
  - Short Malthus note in the back matter.
  - Alphabetical index of terms that includes the 9 levers.
  - All 193 nation profiles and 22 regional summaries.
- Open the Eurozone PDF and confirm it states the canonical global eta (`0.30`), the 25% cap, and the 21 euro-area member-state scope.
- No placeholder text like "[Global map could not be embedded]" appears.

If you skip the `generate_enclosure_map` step, the PDFs will still contain all text, tables, and the modelling section, but the choropleth images will be missing or replaced by placeholders. This is why the map step is required to match the released version.

You can also iterate on sections without a full rebuild:
```bash
python3 -m src.generate_atlas_ebook --front
python3 -m src.generate_atlas_ebook --regions
python3 -m src.generate_atlas_ebook --nations
python3 -m src.generate_atlas_ebook --back
python3 -m src.generate_atlas_ebook --concat-only
```

The final concatenated `RTLDI_ATLAS_2026_ebook.pdf` (front + regions + nations + Eurozone + evidence/reference back matter) is the artifact attached to the GitHub release.

### Getting the V-Dem Data (one-time, ~few hundred MB)
1. Go to https://www.v-dem.net/data/the-v-dem-dataset/
2. Download the latest **Country-Year: V-Dem Full+Others** (or Core if you want smaller).
3. Unzip and place the main CSV in this repo as:
   `data/raw/V-Dem-CY-Full+Others-v16.csv` (or whatever the version is; the loader auto-detects common names).
4. Re-run `python3 -m src.build_atlas --year 2026`

The loader only reads the ~12 columns it needs.

### World Bank Data
No manual download required for the core indicators. The code uses `wbgapi` to pull exactly:
- NY.GDP.PCAP.CD (G0)
- SP.POP.TOTL (population)
- SN.ITK.DEFC.ZS (undernourishment for socio #9)
- SI.POV.DDAY (poverty headcount for socio #9)

If you prefer offline bulk, download the corresponding API_*.csv from data.worldbank.org and place in data/raw/ — the loaders will prefer local files.

### Visualizations: Enclosure Strength Choropleth (part of the full release)
The choropleth maps are an integral part of the released PDF (global map in front matter, regional maps on every region page, and per-nation regional focus maps on every nation page). They are generated by the command in the Quick Start above and are required to match the published release.

"Enclosure strength" = the RTLP R score (0–1 average of the 9 binary indicators of right-to-life protection).

```bash
python -m src.generate_enclosure_map --year 2026
```

Produces:
- High-resolution PNG (scale=2, suitable for print/PDF embedding)
- Vector PDF
- Interactive HTML (hover any country for R, ΔG, capital exclusions, vintage years, region)

All outputs carry the exact 2026 rule footnote: V-Dem components 2024 + 2026 G₀ baseline. See the committed example in `outputs/figures/rtl_di_enclosure_strength_2026_choropleth.*`.

*Built with the document as the north star. The map is the territory only when the data is honest.*

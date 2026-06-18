# RTLDI ATLAS — UN Member States

**Project**: Build a comprehensive, reproducible **RTLDI ATLAS** of all 193 United Nations Member States using the Right to Life Deficit Index (RTLDI) from the source document (Zenodo 10.5281/zenodo.19468550), extended to quantify **capital exclusions** — the lost potential GDP where capital is excluded from the economy because the nine protections necessary for it to operate are not present. The global total is on the order of 15 trillion dollars in excluded capital waiting to be brought back in through the levers.

> Sid J.A. Hubbard, *Causality and Attraction: A Continuum of Steady States* (Version 3, May 2026).  
> DOI: [10.5281/zenodo.19468550](https://doi.org/10.5281/zenodo.19468550)

## License

The **RTLDI Atlas** in this repository (code, data processing pipeline, documentation, and generated outputs) is licensed under the [MIT License](LICENSE).

**Important clarification**: Only the RTLDI Atlas materials in this repository are covered by the MIT License. The underlying theoretical framework and content from the book *Causality and Attraction: A Continuum of Steady States* remain under their original copyright (CC BY-NC-ND 4.0) and are **not** licensed under this MIT License.

## Releases

All releases (including the full PDF ebook as an asset) are available on the [GitHub Releases page](https://github.com/SJAH9/rtldi-atlas/releases).

### v2026.7 (Current — Capital exclusions focus)

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
python3 -m pip install --break-system-packages pandas numpy requests openpyxl wbgapi country-converter plotly kaleido

# 1. Build the core data (uses live World Bank API + your local V-Dem CSV)
python3 -m src.build_atlas --year 2026 --eta 0.30

# 2. Generate the choropleth maps (global + 22 regional) that get embedded in the PDF
#    This step is REQUIRED to match the released atlas. It produces PNGs (for embedding),
#    a vector PDF, and an interactive HTML version.
python3 -m src.generate_enclosure_map --year 2026

# 3. Generate the print-ready PDF ebook (four modular parts + concatenated release)
#    Because the maps were generated in step 2, the PDFs will contain the actual choropleths
#    (global map in front matter, per-region maps, per-nation regional zooms) instead of placeholders.
python3 -m src.generate_atlas_ebook

# 4. (Optional for the launch web companion) Generate the self-contained HTML atlas
#    (front matter + all 22 regional summaries with the exact same data).
#    Produces outputs/html-atlas/index.html (open directly in a browser) plus vector SVG
#    choropleths (global + 22 regions) in outputs/html-atlas/maps/.
python3 -m src.generate_html_atlas
```

**Exact expected outputs for a successful full reproduction (matching the released v2026.7 asset):**
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

The final concatenated `RTLDI_ATLAS_2026_ebook.pdf` (front + regions + nations + back) is the artifact attached to the GitHub release.

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


# RTLDI ATLAS — UN Member States

**Project**: Build a comprehensive, reproducible **RTLDI ATLAS** of all 193 United Nations Member States using the Right-to-Life Deficit Index (RTLDI) equations and framework from:

> Sid J.A. Hubbard, *Causality and Attraction: A Continuum of Steady States* (Version 3, May 2026).  
> DOI: [10.5281/zenodo.19468550](https://doi.org/10.5281/zenodo.19468550)

The ATLAS operationalizes the 9-indicator RTLP score and the RTLDI equation (ΔG = η(1−R)·G₀, η≈0.05) with real-world data, primarily **V-Dem** (Varieties of Democracy) and **World Bank** WDI datasets.

## Releases

All releases (including the full PDF ebook as an asset) are available on the [GitHub Releases page](https://github.com/SJAH9/rtldi-atlas/releases).

### v2026.5 (Current — branch merge + expanded Malthus falsification with full choice framing)

**RTLDI ATLAS 2026 v5** — full ebook 241 pages (back matter 7 pages).

- Merged `main` and `master` branches for a cleaner history (local work continues on `master`; remote default remains `main` — see prior discussion).
- Significantly expanded the back-matter appendix **"Falsification of Malthusian Scarcity: Geodesic Populations and Equal Protection of Life"**:
  - The Malthusian conditions (greater population equating only to a greater drain on resources) are true but misleading when protections are absent — more people then equate to less available resource per person.
  - When the right to life is equally protected, GDP rises for multiple reasons and rises exponentially via the f³ scaling seen in geodesics, because societal stresses are distributed evenly among a more productive and more capable society.
  - Details the concrete mechanisms: the core levers (freedom from torture, freedom from arbitrary detention, and an independent judiciary) together make a nation "investible" — attracting external businesses and stimulating domestic startups, since the risk of death or arbitrary imprisonment no longer stops capital from flowing in.
  - Whistleblower protections, once in place, allow exposure of corruption and theft at scales previously unknown.
  - Crucial distinction: this falsification does **not** negate the efficacy of Malthusian regimes and regulations. A nation can choose the Malthusian path (receive the expected drain on resources and plan for the expected disastrous "trimming" of the population) or choose to raise its RTLP score as high as possible and enjoy the f³ cubic exponential scaling of resilience, the conditions for capital investment, and entrepreneurship arising from the people themselves in an optimized enclosure capable of generating the resources needed to prosper under the protections of a highly organized and stable society.
  - Nations can now clearly see the cost of not caring for the lives of their people equally and have a real choice between the expansion of corruption or the stimulation of domestic industrial productivity.
- This provides important background for the potential causal relationship in the nested causal model.
- Full concatenated `RTLDI_ATLAS_2026_ebook.pdf` (241 pages). Modular parts updated in `outputs/atlas/`.

**Note**: The `outputs/atlas/` directory always holds the most current of each part. Run `--front --regions --concat-only` after descriptive or back-matter changes; `--nations` only when the underlying per-country data or profile layout changes.

### v2026.4 (Previous — Malthus falsification, geodesic population model, and back-matter expansion)

**Note**: The `outputs/atlas/` directory always holds the most current of each part. Run `--front --regions --concat-only` after descriptive or back-matter changes; `--nations` only when the underlying per-country data or profile layout changes.

### v2026.3 (Previous — equation refinement + contextual bounding)

**RTLDI ATLAS 2026 v3** — modular parts in `outputs/atlas/`, full ebook via concat.

- Added explicit **contextual bounding** (25% institutional share cap) to answer the baseline/omitted-factors critique.
- Bounded equation: `ΔG = min( η × (1 − R) × G₀ , 0.25 × G₀ )` with η = 0.30.
- New front-matter "Contextual Bounding" section with archetypal nation studies (Qatar, South Korea, Singapore, Botswana, etc.) and the 25% cap rationale.
- All figures, descriptions, and index updated to use bounded values (raw global ~18.76T → ~17.49T after cap).
- 4-part system and 2026 data rule unchanged.

See prior notes for full details on v2026.3.

### v2026.2

**RTLDI ATLAS 2026 v2** — 4-part modular system + region-page UX and map fixes (see prior release notes). Full concatenated ebook was 233–236 pages depending on exact front-matter length. Improvements to region pages (text flow, table positioning, aspect-corrected choropleths) noted for replication on nation pages.

### v2026.1

**RTLDI ATLAS 2026 Release 1** — [View on GitHub](https://github.com/SJAH9/rtldi-atlas/releases/tag/v2026.1)

- Initial full PDF ebook with all 193 nation profiles, UN Regional Summaries, global/regional choropleths (Mollweide), 3-year trend plots, and diagnostic guide.
- First public release of the 4-part generation pipeline and reproducible build.

See the full history of releases on the [Releases page](https://github.com/SJAH9/rtldi-atlas/releases).

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
the 25% cap is the template-derived limit so the nine indicators are never credited
with more than one-quarter of observed G0 once industry, resources, history, location
and human capital are given due weight — see the "Contextual Bounding" section in the atlas)
Total bounded disparity ≈ ΔG × population

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

### Quick Start (2026 data)
```bash
git clone https://github.com/SJAH9/rtldi-atlas.git
cd rtldi-atlas
python3 -m pip install --break-system-packages pandas numpy requests openpyxl wbgapi country-converter
python3 -m src.build_atlas --year 2026 --eta 0.30
# Optional (for choropleth maps of enclosure strength / other figures):
python3 -m pip install plotly kaleido
python3 -m src.generate_enclosure_map --year 2026
```

The code will:
- Fetch the required World Bank indicators live via the official API (always up-to-date).
- Look for your V-Dem CSV in `data/raw/` (see "Getting the Data" below).
- Compute the full 9-component RTLP score using the published crosswalk.
- Output CSV + XLSX + summary in `outputs/atlas/`.

After the atlas is built you can generate the choropleth of enclosure strength (RTLP R):
```bash
python3 -m src.generate_enclosure_map --year 2026
```
Outputs land in `outputs/figures/` (PNG at print resolution, PDF vector, interactive HTML with full hover details + vintage labels).

You can also (re)build the print PDF ebook. The generator now produces **four** separate parts (front / regions / nations / back) so you can iterate quickly on any section without regenerating the others:
```bash
# Build everything and concatenate the release
python3 -m src.generate_atlas_ebook

# Fast iteration examples
python3 -m src.generate_atlas_ebook --front      # title, exec, method, diagnostic, carto+map+global lost table, TOC, 193 summary table
python3 -m src.generate_atlas_ebook --regions    # the 22 UN Regional Summaries (maps, descriptions, tables, breakdowns)
python3 -m src.generate_atlas_ebook --back       # attribution, alphabetical index of terms, credits
python3 -m src.generate_atlas_ebook --concat-only   # final release step: combine the four current parts into the full ebook

# Heavy step (only when per-country data or nation-page layout changes)
python3 -m src.generate_atlas_ebook --nations
```
Outputs (always the most current of each):
- `outputs/atlas/RTLDI_ATLAS_2026_front.pdf`
- `outputs/atlas/RTLDI_ATLAS_2026_regions.pdf`
- `outputs/atlas/RTLDI_ATLAS_2026_nations.pdf`
- `outputs/atlas/RTLDI_ATLAS_2026_back.pdf`
- `outputs/atlas/RTLDI_ATLAS_2026_ebook.pdf` (concatenated release — front + regions + nations + back — this is the one you publish / attach to a GitHub release)

The final step before tagging a release is the concatenation of the four parts. This structure prevents any repetition/duplication during generation and lets you iterate on front matter, regional analysis, nation profiles, or back matter completely independently.

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

### Visualizations: Enclosure Strength Choropleth
"Enclosure strength" = the RTLP R score (0–1 average of the 9 binary indicators of right-to-life protection).

```bash
python -m src.generate_enclosure_map --year 2026
```

Produces:
- High-resolution PNG (scale=2, suitable for print/PDF embedding)
- Vector PDF
- Interactive HTML (hover any country for R, ΔG, total deficit, vintage years, region)

All outputs carry the exact 2026 rule footnote: V-Dem components 2024 + 2026 G₀ baseline. See the committed example in `outputs/figures/rtl_di_enclosure_strength_2026_choropleth.*`.

## Current Status
See the private repo history for the full development log. The public launch version will include the 2026 ATLAS (tables + 206-page print ebook), enclosure strength choropleth maps, improved NGO UX, and full documentation.

## Project Layout (committed files only)
```
.
├── .gitignore          # ensures no data sets are committed
├── README.md
├── data/raw/
│   └── un_member_states.csv   # tiny canonical list (committed)
├── src/                # the full pipeline
├── docs/               # specs + crosswalk + methodology
├── outputs/atlas/      # example 2023/2026 real ATLAS (committed as demo)
├── outputs/figures/    # committed example choropleth of enclosure strength (R) for 2026
└── ...
```

Large V-Dem CSVs, WB bulk downloads, and generated 202x atlases are intentionally **not** in the repo.

## Core RTLDI (from source)
See `docs/RTLDI_SPEC.md`.

ΔG (per capita) = η × (1 − R) × G0  (η≈0.30 from population-weighted current UN data) 
Total = ΔG × population

R is computed from the exact 9 binary RTLP questions mapped to V-Dem + WB variables (see `docs/indicator_crosswalk.md`).

## Updating to 2026+
- Set `--year 2026` (or future).
- Provide the latest V-Dem release CSV (when published).
- WB data is live via API and will reflect the most recent releases.
- The crosswalk and binarization thresholds are versioned in docs/ for transparency and sensitivity analysis.

## License / Attribution
- RTLDI equations, 9 indicators, paradigm: © Sid J.A. Hubbard (Zenodo 10.5281/zenodo.19468550)
- Code: MIT (or similar — to be confirmed at public launch)
- V-Dem & World Bank data: follow their respective terms (open for research / with attribution)

This repo was initialized privately and will be made public at launch.

## Data Sources (target)
- **V-Dem Dataset** (Country-Year, latest release): https://www.v-dem.net/data/the-v-dem-dataset/ — rich indicators on rule of law, judicial independence, physical violence (killings, torture), freedom of expression, arbitrary power, etc.
- **World Bank World Development Indicators (WDI)**: GDP per capita (current USD or constant), population, and socioeconomic proxies (poverty, health access, undernourishment, etc.) for indicator #9 and G0.
- UN Member States: Official list (193) for filtering and canonical names/ISO3 codes.

## Key Design Decisions (to be refined)
- **Binarization**: How to turn V-Dem continuous/ordinal scores into the 9 "yes/no". Default proposal: literature- or distribution-based cutoffs (e.g. ≥ median of democracies or ≥0.5 on 0-1 scales). Fully documented + sensitivity analysis.
- **Missing data**: Conservative rules (e.g. treat missing component as 0 for protection, or use multiple imputation / last-observation; flag heavily).
- **Year**: Primary "ATLAS snapshot" = most recent year with good coverage (e.g. 2023 or 2024 depending on V-Dem v14+). Also produce multi-year panel.
- **η**: Base = 0.30 (population-weighted empirical from 2026 data: ~30.5% higher g0 per RTLP indicator in weighted log regression across 187 nations); the original 0.05 was a conservative structural parameter from source analysis. Use --eta to override for scenarios.
- **Output units**: USD (current or constant as per WB series chosen). Document choice.
- **Sovereignty filter**: Strictly the 193 UN members (excludes observers, disputed territories unless matching UN list).

## Getting Started / Running
(Once implemented)
```bash
# e.g.
python -m src.fetch_un_members
python -m src.fetch_vdem --year 2023
python -m src.fetch_wdi
python -m src.build_rtl_di_atlas --year 2023 --output outputs/atlas/rtl_di_atlas_2023.csv
```

See notebooks/ for exploratory mapping.

## Contributing to Indicator Mapping
The heart of the project is a defensible, transparent crosswalk from the 9 questions → V-Dem (and WB) variables. See future `docs/indicator_crosswalk.md`.

All decisions must be:
- Justified with reference to V-Dem codebook / question wording.
- Reversible / sensitivity-testable.
- Aligned with the spirit of the source document (protection of life against arbitrary state or structural violence/interruption).

## License / Attribution
- The RTLDI equations, 9 indicators, and conceptual framework © Sid J.A. Hubbard (per the Zenodo deposit).
- Code and data pipeline in this repo: to be decided (likely MIT or similar).
- V-Dem data: see their license/terms (usually CC or academic use).
- World Bank: open data, attribution required.

## Contact / Notes
This worktree (rtldi-3) is dedicated to the ATLAS. Related to the "Causality and Attraction" / RTLDI thread in the source.

Initial work: 2026-06-03.

---

*Built with the document as the north star. The map is the territory only when the data is honest.*

## LaTeX Design Refinement (in progress)

A parallel LaTeX-based version of the atlas is under active refinement in the `latex/` directory (generated by `src/generate_atlas_latex.py`).

**Goals of the LaTeX path**:
- Superior typography and micro-typographic control (booktabs tables, proper long tables for the 193-row summary, consistent spacing).
- Better support for complex layouts (tcolorbox/tikz for economic impact callouts, side-by-side images for trend + regional zoom on nation pages, precise figure placement).
- Explicit embodiment of the source document's cartographic philosophy (the new "Cartographic Approach and the Nested Map" section in the PDF, the hybrid Mollweide + canonical global view model).
- Professional print quality while preserving 100% fidelity to the 2026 data rule, the 9 verbatim RTLP indicators, the ΔG equation, the per-country breakdowns, the regional aggregates + member tables with totals rows, the 3-year trends, and the Mollweide choropleths.

**Current status (begin phase)**:
- `latex/main.tex` is generated from the same 2026 data (CSV + breakdown JSON) used by the fpdf version.
- Includes the full global summary table (longtable + booktabs), the hybrid cartographic section with the canonical global choropleth embedded, methodology, diagnostic guide content, and design stubs/examples for regional pages (with the nations table + RTLP/G0/Pop/RTLD I + totals row) and nation profiles.
- Images are referenced from `../outputs/figures/` (global canonical copied into `latex/figures/` during generation; full set of per-nation/regional/trend PNGs can be copied for a self-contained build).

**To compile (requires LaTeX — MacTeX / TeX Live recommended)**:
```bash
python -m src.generate_atlas_latex   # (re)generates latex/main.tex and copies key images
cd latex
lualatex -interaction=nonstopmode main.tex   # run 2–3 times for TOC, references, etc.
# or pdflatex (core packages are standard)
```

The LaTeX source is intended to be the foundation for ongoing design refinement (better fonts, custom tikz elements for the 9 indicators or nested-enclosure diagrams, improved index, vector output options, etc.) while the Python/fpdf version remains for quick iteration and the "easy to regenerate with your own data" promise to NGOs.

All core content, data vintage rules, equations, and the hybrid cartographic model are identical between the two versions.

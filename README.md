# RTLDI ATLAS — UN Member States

**Project**: Build a comprehensive, reproducible **RTLDI ATLAS** of all 193 United Nations Member States using the Right-to-Life Deficit Index (RTLDI) equations and framework from:

> Sid J.A. Hubbard, *Causality and Attraction: A Continuum of Steady States* (Version 3, May 2026).  
> DOI: [10.5281/zenodo.19468550](https://doi.org/10.5281/zenodo.19468550)

The ATLAS operationalizes the 9-indicator RTLP score and the RTLDI equation (ΔG = η(1−R)·G₀, η≈0.05) with real-world data, primarily **V-Dem** (Varieties of Democracy) and **World Bank** WDI datasets.

## Goals
- Transparent, data-driven computation of RTLP (R) and RTLDI (ΔG per capita + aggregate) for every UN member.
- High-quality indicator mapping from the 9 binary questions to observable variables.
- Reproducible pipeline (fetch → clean → score → compute → export).
- Multiple outputs: master dataset (CSV/Parquet/XLSX), summaries, ranks, time series where available, methodology documentation.
- Foundation for maps, dashboards, further analysis (e.g., correlations with other indices, historical trends, scenario modeling with η). The 2026 release includes a global choropleth of enclosure strength (RTLP R).

## Core RTLDI (from source)
See [docs/RTLDI_SPEC.md](docs/RTLDI_SPEC.md) for the verbatim 9 indicators, equation, examples, and notes.

ΔG (per capita loss) = 0.05 × (1 − R) × G0  
Total deficit ≈ ΔG × population

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
python3 -m src.build_atlas --year 2026 --eta 0.05
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

ΔG (per capita) = 0.05 × (1 − R) × G0  
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
- **η**: Base = 0.05; variants for 0.03 / 0.07 etc. in scenarios.
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

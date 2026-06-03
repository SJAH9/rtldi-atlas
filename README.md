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
- Foundation for maps, dashboards, further analysis (e.g., correlations with other indices, historical trends, scenario modeling with η).

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

## Current Status (2026-06-03)
- ✅ Document (v3) fetched, full text extracted, spec documented (`docs/RTLDI_SPEC.md`).
- ✅ Project layout, UN 193 list (with ISO3), V-Dem v16 codebook downloaded.
- ✅ Indicator crosswalk researched + written (`docs/indicator_crosswalk.md`).
- ✅ Core RTLDI equation + binarization + socio scoring implemented (`src/rtl_di.py`).
- ✅ WB data acquisition (wbgapi, batched, mrv + year) for GDP pc, pop, undernourish, poverty — 193 UN members.
- ✅ V-Dem loader stub ready (download instructions + usecols subsetter).
- ✅ **First RTLDI ATLAS produced** (outputs/atlas/): 193 countries, real WB G0 + pop + socio, *placeholder R* (socio real + avg on other 8, modulated), exact ΔG + totals + ranks. Global est. ~$2.19T (close to source illustration). Includes CSV + formatted XLSX.
- ✅ **Real 9-component RTLDI ATLAS (2023)** now available using your V-Dem v15 Full+Others CSV (symlinked) + your local WB GDP download: `rtl_di_atlas_un_members_2023.csv` / `.xlsx`. Real R from the exact crosswalk (8 V-Dem integrity/rule/expression/access components + WB socio #9). Avg R ~0.35, 10 countries at R=1.0 on components, 57 at R=0, global est. deficit ~$2.44T. Uses user's downloaded files directly (no API for G0).
- 📝 Methodology for v0 placeholder in `docs/methodology_v0_placeholder.md`.
- Next: drop in V-Dem CSV → replace placeholder R with true 9-component scores per crosswalk; add scenarios, full docs, perhaps maps.

## Quick Start / Reproduce First ATLAS
```bash
# Ensure deps (one-time)
python3 -m pip install --break-system-packages pandas numpy requests openpyxl wbgapi country-converter

# (Optional but recommended) Download V-Dem Core/Full v16 CSV to data/raw/ per src/fetch_vdem.py docstring

# Build real version (uses your local V-Dem symlink + local WB GDP download + crosswalk)
python3 -m src.build_atlas --year 2023 --eta 0.05

# Or the legacy placeholder for comparison
python3 -m src.build_atlas --year 2023 --eta 0.05  # (defaults to real now)

# Outputs:
#   outputs/atlas/rtl_di_atlas_un_members_2024_placeholder.csv
#   outputs/atlas/rtl_di_atlas_un_members_2024_placeholder.xlsx
#   outputs/atlas/rtl_di_atlas_summary_2024.json
```

See `src/fetch_wb.py` (can re-fetch), `src/build_atlas.py`, and the docs/ for mapping decisions.

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

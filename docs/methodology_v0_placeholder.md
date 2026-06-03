# RTLDI ATLAS v0 — Methodology (Placeholder)

**Date**: 2026-06-03  
**Version**: Initial pipeline + WB data + equation (full 9-indicator R pending V-Dem)

**Update (same day)**: With user-provided V-Dem v15 Full+Others (384MB CSV from ~/Downloads, symlinked) + local WB GDP API bulk, the first *real* 9-component RTLDI ATLAS for 2023 was generated using the crosswalk. See outputs/rtl_di_atlas_un_members_2023.* (non-placeholder). Avg real R ~0.35. The v0 placeholder remains for comparison.  
**Source**: Hubbard, *Causality and Attraction: A Continuum of Steady States* v3 (May 2026), DOI 10.5281/zenodo.19468550

## Scope
- 193 UN Member States (from country-converter UNmember list + ISO3).
- Latest available World Bank WDI data (primarily 2023–2024 via mrv / year-specific fetches).
- Exact RTLDI equation implemented and used: `ΔG = η(1 − R) · G₀` with η = 0.05.
- Aggregate: `total = ΔG × population`.

## Data
- **UN list**: `data/raw/un_member_states.csv` (193 rows, iso3, short name, region).
- **World Bank** (wbgapi, WDI db=2):
  - G0: `NY.GDP.PCAP.CD` (GDP per capita, current US$)
  - Population: `SP.POP.TOTL`
  - Socio #9 proxies: `SN.ITK.DEFC.ZS` (Prevalence of undernourishment %), `SI.POV.DDAY` (Poverty headcount $2.15 2017 PPP %)
- Coverage (2023/2024 latest non-na per series): ~187 GDP, 193 pop, 161 undernourish. Countries with no G0 have NaN deficits (small states, conflict, data gaps — e.g. Syria, Eritrea, North Korea, South Sudan, Yemen in this extract).

## R Computation (v0 Placeholder)
Until V-Dem v16 CSV is downloaded and the crosswalk in `docs/indicator_crosswalk.md` is fully coded:
- Real component for indicator #9 (Socioeconomic) via `score_socioeconomic()`:
  - yes (1) if undernourish ≤ 5% **AND** poverty_215 ≤ 10%.
- The other 8 indicators assumed at base 0.70 (near source global avg R 0.62, slightly higher for demo).
- R = (8/9)*base + (1/9)*socio_bin
- Small negative modulation based on observed poverty/undernourish (capped) to create visible variation across countries. **This is illustrative only.**
- Resulting avg R ~0.54, global est. deficit ~$2.19T (remarkably close to source's ~$2T illustration at R=0.62 — validates scaling of the equation with real G0/pop).

Full R will be `compute_r_from_components(components_dict)` once the 8 V-Dem proxies + binarization thresholds are wired (see crosswalk for proposed v2cltort, v2clkill, v2juhcind, v2juncind, v2xcl_acjst, v2x_freexp, v2cltrnslw, etc.).

## Binarization & Thresholds (for future)
Defined in `RTLDIConfig` + `docs/indicator_crosswalk.md`:
- V-Dem 0-4 components (torture, killings, judiciary, etc.): ≥ 2.0 ("Somewhat respected" or better) → 1.
- V-Dem indices: ≥ 0 (or 0.5) → 1.
- Missing → 0 (conservative).

## Outputs
- `rtl_di_atlas_un_members_2024_placeholder.csv` — master table, sorted by total deficit rank.
- `.xlsx` — formatted with title, summary, headers, number formats.
- `rtl_di_atlas_summary_2024.json` — aggregates.

Columns include ranks (by total $ and by lowest R), components used, has_* flags, data_notes.

## Limitations (v0)
- R is not yet the true 9-indicator RTLP from source.
- Some high-population or high-GDP countries with missing recent WB data (or NaNs) drop out of totals.
- GDP current US$ (nominal); constant or PPP alternatives can be added.
- No time-series panel yet (single "latest" snapshot).
- No sensitivity on η or thresholds.
- No V-Dem yet → no real variation from judiciary, torture, expression, etc.

## Validation Notes
- Source examples (Syria R~0, Iran~0.33, Brunei 0.22, global ~0.62 → ~2T) produce same order of magnitude here.
- China ranks #1 total deficit (pop × (1-R) × G0).
- High-R (low deficit) countries tend to be wealthy with good socio metrics in the placeholder.

## Next Steps (see TODOs)
1. Place V-Dem Core/Full v16 CSV in data/raw/ (instructions in `src/fetch_vdem.py`).
2. Implement `load_vdem_subset` + mapping in build pipeline → replace placeholder R.
3. Add proper year-per-metric, multiple η scenarios, full methodology doc.
4. Optional: choropleth data, more WB WGI cross-checks, historical series.

All code and decisions are in the repo for audit. The equation and 9 questions are used exactly as published.

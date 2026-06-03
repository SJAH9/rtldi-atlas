# RTLDI Indicator Crosswalk: 9 RTLP Questions → V-Dem + World Bank Variables

**Project**: RTLDI ATLAS of UN Member States  
**Source Spec**: See `docs/RTLDI_SPEC.md` (verbatim from Hubbard v3, DOI 10.5281/zenodo.19468550)  
**Data Releases Targeted**: V-Dem v16 (2026, data to 2025), World Bank WDI latest available.  
**Date of this mapping**: 2026-06

## Principles for Mapping
- Stay as close as possible to the *spirit* of each binary question (protection against *arbitrary* interruption of life / equal safeguarding).
- Prefer **V-Dem** "C" (component) variables and high-level "D" indices that directly address personal integrity, judicial autonomy, access, expression.
- All V-Dem "C" indicators are expert-coded, measurement-modeled to interval scale (typically ~-3.5 to +3.5, higher = better protection/respect).
- **Binarization**: We convert the best proxy to 0/1 ("yes" = protection adequate / respected at a meaningful level). 
  - Default rule (to be confirmed/sensitivity-tested): For 0-4 ordinal-derived: **≥ 2.0** ("Somewhat respected" / "About half" or better) = 1 (yes). 
  - For standardized indices (often 0-1 or centered): **≥ 0.5** or **≥ 0** (mean) depending on distribution and substantive meaning.
  - For WB socioeconomic: substantive thresholds (e.g. undernourishment ≤5%, extreme poverty low).
- Missing data: In base case, treat missing component as 0 (conservative: no credit for unknown protection). Alternatives (mean imputation, last obs carried forward, listwise) will be options in code.
- Gender disaggregation: V-Dem often splits men/women; we average or take the lower (more conservative for "equal" protection) or use the index version where available.
- "Conflict zones" and "law enforcement": captured in the *degree* to which killings/torture occur and whether leaders are preventing or inciting (see clarifications in codebook).
- **#1 (Legal / de jure)** is the weakest direct match; almost all modern states have some constitutional language. We proxy via *functioning legal predictability / transparent enforcement* (de facto rule of law foundation).

## Proposed Mapping Table

| # | RTLP Indicator (verbatim question) | Best V-Dem / WB Proxy(ies) | Variable Code(s) | Scale / Notes | Proposed Binarization Threshold for "yes"=1 | Rationale / Codebook Excerpt |
|---|------------------------------------|----------------------------|------------------|---------------|-----------------------------------------------|--------------------------------|
| 1 | Existence of Legal Protections: Does the entity have provisions explicitly protecting the right to life? | Transparent laws with predictable enforcement (or rigorous & impartial public admin as fallback). (De jure right-to-life is near-universal; variance is enforcement + explicit equal protection.) | `v2cltrnslw` (primary); fallback `v2clrspct` | 0-4 (higher=better) | `v2cltrnslw >= 2` | "Transparent laws with predictable enforcement" directly supports legal protections being real. Codebook: impartial public admin, transparent laws. |
| 2 | Independent Judiciary: Is there an independent judiciary capable of upholding right-to-life laws? | High court independence + Lower court independence. (Core of judicial autonomy.) | `v2juhcind`, `v2juncind` (average or min for conservatism) | 0-4 (higher=more independent, "Never merely reflects government wishes") | avg >= 2.0 | Direct match to "independent judiciary". High values mean courts decide on legal record, not wishes. Also feeds `v2x_rule`. |
| 3 | Law Enforcement Accountability: Are law enforcement agencies accountable for unlawful killings? | Freedom from political killings (clarification explicitly covers whether killings "incited and approved by top leaders" or leaders "actively working to prevent"). Complemented by torture. | `v2clkill` (primary); `v2cltort` secondary | 0-4 | `v2clkill >= 2` | "Political killings are practiced in a few isolated cases but ... not incited or approved..." = level 3. Lower levels indicate lack of accountability at leadership / agency level. |
| 4 | Protection Against Arbitrary Detention: Is arbitrary detention prohibited with legal recourse? | Access to justice (men/women) + transparent laws + impartial public administration. (No single "habeas corpus / arbitrary arrest" var in core V-Dem; this is the closest cluster for recourse against state overreach.) | `v2xcl_acjst` or avg(`v2clacjstm`, `v2clacjstw`); + `v2cltrnslw` | ~ -3.5..3.5 or 0-4 | `v2xcl_acjst >= 0` (or component >=2) | Access to justice explicitly includes "effective ability to seek redress if public authorities violate their rights". Combined with predictable enforcement. |
| 5 | Freedom from Torture and Inhumane Treatment: Are measures in place to prevent torture? | Freedom from torture (state officials / agents) | `v2cltort` | 0-4 | `v2cltort >= 2` ("Somewhat" or better: "Torture is practiced occasionally but is typically not approved by top leaders") | Direct. Higher categories indicate active prevention / non-systematic. |
| 6 | Civilian Protection in Conflict Zones: In conflict areas, are mechanisms protecting civilians? | Physical violence index (overall) + Freedom from political killings (in practice the main measure of state violence against persons, including in internal conflict/repression). Low killings even in tense periods. | `v2x_clphy` (Physical violence index); `v2clkill` | Index (higher=less violence); 0-4 | `v2clkill >= 1.5` or `v2x_clphy >= 0` (tunable) | v2clkill clarification covers deliberate lethal force by state agents (police, security, paramilitary) — exactly the risk in conflict zones. Overall phy index aggregates. (V-Dem also has conflict incidence in Full+Others if needed.) |
| 7 | Access to Justice: Do individuals have fair access to remedies for right-to-life violations? | Access to justice index / components (secure and effective access: bring cases, fair trials, redress, counsel, appeal) | `v2xcl_acjst` (index); `v2clacjstm`, `v2clacjstw` | Interval / 0-4 components | `v2xcl_acjst >= 0` or avg components >= 1.5-2 | Verbatim match to question wording in codebook. |
| 8 | Freedom of Expression and Whistleblower Protections: Are expression/whistleblower rights upheld? | Freedom of expression and alternative sources of information index (includes discussion, media, criticism of govt). Whistleblower aspect proxied by tolerance of dissent / counter-arguments. | `v2x_freexp` (primary index); components e.g. `v2cldiscm`/`w`, `v2clrspct` (rigorous admin also relates to info) | ~0-1 or interval | `v2x_freexp >= 0.5` | Core civil liberty for exposing violations (whistleblowing requires space to speak without fear). Codebook sources for freexp include respect for counterarguments etc. |
| 9 | Socioeconomic Conditions: Is access to healthcare, food, and shelter adequate to sustain life? | World Bank WDI: Prevalence of undernourishment (%); Poverty headcount at low lines (e.g. $2.15 or $3.65 2017 PPP); possibly access to electricity / improved water / under-5 mortality as health/shelter proxies. | `SN.ITK.DEFC.ZS` (undernourishment); `SI.POV.DDAY` or similar (poverty); `SP.DYN.IMRT.IN` or `NY.GDP.PCAP.CD` not for this. | % or rates | "yes" if undernourishment <=5% AND poverty headcount at intl poverty line <=10% (or a simple 0-1 subscore >0.7). Alternative: life expectancy at birth >68-70 or composite basic needs index. | Direct match to "food... adequate to sustain life", healthcare/shelter via mortality/water proxies. Avoids using GDP itself (which is the *outcome* in RTLDI). Thresholds are conventional "low" levels from FAO/WB. |

**Composite indices as robustness**: V-Dem's `v2x_rule` (Rule of law), `v2x_civlib` (Civil liberties), `v2x_clphy` (Physical violence) can be used for sensitivity or as overall "protection" checks.

## Data Notes
- **V-Dem v16 (March 2026 release)**: Country-Year data, years 1789–2025. We will use the most recent year with broad coverage (likely 2024 or 2025) for the primary ATLAS snapshot, plus a panel for trends.
- Preferred column in CSV: the main point estimate (e.g. `v2cltort`). There are also `_mean`, `_sd`, `_codelow`/`_codehigh`, `_ord`, `_osp` etc. Use the interval point estimate for continuous proxy.
- Gender: For equality spirit, one option is to use the *min* of men/women scores for a component (worst-off gender determines if "equal" protection holds).
- **World Bank**: Use `wbgapi` (or direct bulk). Series chosen for latest year available per country. GDP per capita: `NY.GDP.PCAP.CD` (current US$) or constant for real comparisons. Population: `SP.POP.TOTL`.
- Matching: Use ISO3 (`country_text_id` or `ISO3` in V-Dem? V-Dem uses `country_name`, `country_id`, `COWcode` etc. country-converter + manual map for V-Dem names to ISO3.
- V-Dem coverage: Excellent for ~180+ countries in recent decades; some microstates or new members may have gaps (e.g. South Sudan from 2011+).

## Open Questions / To Be Decided in Code + Sensitivity
- Exact cutoffs (will implement as parameters, default as above, produce variants).
- How to aggregate the 9 binaries when some proxies are indices vs components.
- Treatment of gender split: average vs. min (for "equal protection").
- #1 (Legal): Is there a better de jure measure? (V-Dem has limited pure de jure for "right to life" specifically; constitutions almost universally have Art. 6-like language per ICCPR.)
- Conflict zones (#6): Enhance with explicit conflict-year flag if available in Full dataset (e.g. battle deaths or internal conflict vars from other sources in Full+Others).
- η sensitivity and alternative G0 (constant USD, PPP, etc.).

## Sources
- V-Dem Codebook v16 (local `data/raw/codebook_v16.pdf`).
- Variable questions/clarifications extracted directly.
- World Bank WDI metadata via `wbgapi.wb.series()` / indicators search.
- Original: Hubbard (2026) v3, "grounded in real human rights data" (V-Dem Human Rights Index cited as key).

## Next
- Implement in `src/` a `crosswalk.py` or config with these mappings + binarize functions.
- Validation: recompute for source examples (Syria ~0, Iran ~0.33, Brunei 0.22) and see if our proxies + cutoffs reproduce rough order of magnitude.
- Full methodology in `docs/methodology.md` (will include chosen cutoffs + justification + any deviations).

*This crosswalk is an operationalization. It is not part of the original source document; all credit for the 9 questions and RTLDI equation belongs to the author.*

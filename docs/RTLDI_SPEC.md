# RTLDI Specification (from Causality and Attraction v3)

**Source Document**: Sid J.A. Hubbard, *Causality and Attraction: A Continuum of Steady States*, Version 3 (May 2026). DOI: 10.5281/zenodo.19468550

**Extracted**: 2026-06 from local PDF/text.

## Core Equation (D.4 / 5.1)

ΔG = η × (1 − R) × G₀

Where:
- **ΔG** : Annual GDP per capita loss (lost output per person due to incomplete right-to-life protection).
- **η** : Sensitivity coefficient ≈ 0.05 (5% growth "premium" per full RTLP unit improvement, derived from human rights–economic growth correlations in literature).
- **R** : RTLP score, normalized [0, 1].
- **G₀** : Baseline GDP per capita (World Bank data).

**Aggregate national cost** (inferred for examples in source):
Total annual deficit ≈ ΔG × Population

**Global illustration** (source): At average R ≈ 0.62, ~$2 trillion annual global deficit.

## RTLP Score (Right to Life Protection)

Scored via **9 binary indicators** (yes=1 / no=0). Each "yes" reflects alignment with biological steady states (sustaining life without arbitrary interruption).

RTLP = (count of "yes") / 9

R = RTLP ∈ [0,1]

### The 9 RTLP Indicators (verbatim)

1. **Existence of Legal Protections**: Does the entity have provisions explicitly protecting the right to life?
2. **Independent Judiciary**: Is there an independent judiciary capable of upholding right-to-life laws?
3. **Law Enforcement Accountability**: Are law enforcement agencies accountable for unlawful killings?
4. **Protection Against Arbitrary Detention**: Is arbitrary detention prohibited with legal recourse?
5. **Freedom from Torture and Inhumane Treatment**: Are measures in place to prevent torture?
6. **Civilian Protection in Conflict Zones**: In conflict areas, are mechanisms protecting civilians?
7. **Access to Justice**: Do individuals have fair access to remedies for right-to-life violations?
8. **Freedom of Expression and Whistleblower Protections**: Are expression/whistleblower rights upheld?
9. **Socioeconomic Conditions**: Is access to healthcare, food, and shelter adequate to sustain life?

**Data grounding** (source): "grounded in real human rights data." Recommended sources in document: V-Dem Human Rights Index, U.S. State Department reports, World Bank, Global Peace Index.

**Notes on operationalization** (for ATLAS project):
- The source presents them as binary questions for a simple, transparent index.
- In practice (ATLAS), we proxy each using continuous/ordinal V-Dem indicators (primarily) + World Bank/WDI for #9.
- Binarization rule to be defined per-indicator (e.g., V-Dem score ≥ 0.5 or literature-based threshold for "yes"/adequate protection). This introduces a modeling choice that must be documented and sensitivity-tested.
- Time-series capable: V-Dem provides historical data.

## Examples from Source (v3)

- Syria (R ≈ 0.00): $660 million annual deficit
- Iran (R ≈ 0.33): $7.3 billion
- Brunei (R = 0.22): $593 million
- Global avg R ≈ 0.62 → $2T annual deficit

(These appear to be *total* national figures; per-capita equation is the formal definition.)

## Related Concepts in the Paradigm

- Nested within "Human Rights and Economic Outcomes" (Ch. 5) and "Economics – Enclosing Human Exchange" (App. C).
- Interpreted as an entropic cost / drag on biological and economic steady states.
- Part of broader "enclosure" where equal protection of right to life is a structural parameter enabling higher-order resilience (also used in Malthus critique via f³ geodesic scaling).
- Complements (does not replace) existing indices.

## Implementation Notes for ATLAS

- Primary data: V-Dem Country-Year dataset (for indicators 1-8), World Bank WDI (GDP pc current or constant USD, population, for #9 + G0 + aggregates).
- UN Member States filter (193).
- Output: per-country R, component scores (or raw proxies), ΔG_per_capita, total_deficit, rank, data_year, missingness flags.
- η fixed at 0.05 for base case; allow parameter variation for scenarios.
- Latest available year for "current atlas" + historical series where possible.
- Reproducibility: scripts + pinned data versions + methodology doc.

## References in Source

- V-Dem (primary for human rights / physical integrity / rule of law).
- World Bank (GDP, and socioeconomic for #9).
- Cross-referenced with U.S. State Dept human rights reports, Global Peace Index.

---

*This spec is derived directly from the document text. Any operational mapping decisions for data are project extensions and will be documented separately in methodology.md.*

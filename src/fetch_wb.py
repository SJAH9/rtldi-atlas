"""
World Bank data fetcher for RTLDI ATLAS (GDP pc, population, socioeconomic indicators).

Uses wbgapi. Requires internet.
"""

from __future__ import annotations
import pandas as pd
import wbgapi as wb
from typing import List, Optional, Dict
import warnings


DEFAULT_INDICATORS = {
    "gdp_pc_current": "NY.GDP.PCAP.CD",
    "population": "SP.POP.TOTL",
    "undernourish": "SN.ITK.DEFC.ZS",
    # Poverty headcount at $2.15/day (2017 PPP) - name may evolve; check wb.series.get
    "poverty_215": "SI.POV.DDAY",
}

# Alternative / supplemental for #9
SOCIO_INDICATORS = [
    "SN.ITK.DEFC.ZS",   # undernourish
    "SI.POV.DDAY",      # $2.15
    "SP.DYN.LE00.IN",   # life expectancy at birth (supplement)
]


def get_un_iso3_list(un_csv: str = "data/raw/un_member_states.csv") -> List[str]:
    df = pd.read_csv(un_csv)
    return df["ISO3"].dropna().unique().tolist()


def fetch_wdi(
    iso3_list: Optional[List[str]] = None,
    indicators: Optional[Dict[str, str]] = None,
    years: Optional[List[int]] = None,
    db: int = 2,  # WDI
    mrv: Optional[int] = None,  # if set, fetch most recent N values (ignores years)
    batch_size: int = 80,  # to avoid large request drops
) -> pd.DataFrame:
    """
    Fetch selected WDI series for given countries/years or most recent values.

    Uses batching + optional mrv for robustness with 193 countries.
    Returns dataframe in the shape returned by wb.data.DataFrame (reset_indexed).
    """
    if indicators is None:
        indicators = DEFAULT_INDICATORS
    if iso3_list is None:
        iso3_list = get_un_iso3_list()

    econ_list = [e for e in iso3_list if e]
    series_list = list(indicators.values())

    print(f"Fetching {len(series_list)} indicators for {len(econ_list)} economies (mrv={mrv}, batch={batch_size})...")

    frames = []
    for i in range(0, len(econ_list), batch_size):
        batch = econ_list[i : i + batch_size]
        try:
            if mrv:
                part = wb.data.DataFrame(series_list, batch, mrv=mrv, db=db, labels=True)
            else:
                part = wb.data.DataFrame(series_list, batch, time=years, db=db, numericTimeKeys=True, labels=True)
            frames.append(part.reset_index())
        except Exception as e:
            print(f"  Batch {i//batch_size} failed: {e}. Retrying smaller or skipping...")
            # Could split further, but for now collect what we have
    if not frames:
        raise RuntimeError("All batches failed to fetch WB data.")
    df = pd.concat(frames, ignore_index=True)

    # Rename known series ids to friendly names where possible
    rename_map = {v: k for k, v in indicators.items()}
    df = df.rename(columns=rename_map)
    return df


def get_latest_values(
    df: pd.DataFrame,
    iso3_col: str = "economy",  # wbgapi default column for economy
    year_cols_prefix: str = "YR",
) -> pd.DataFrame:
    """
    For each economy + series, take the most recent non-NaN value.
    Returns tidy df: iso3, indicator, year, value
    """
    # Expect df with columns like economy, series, YR2015 ... YR2025 or after rename some indicators
    id_vars = [c for c in df.columns if not c.startswith(year_cols_prefix) and c not in ["series"]]
    if "series" not in df.columns:
        # already partially renamed case
        warnings.warn("DataFrame may already be pivoted; get_latest_values expects series + YR cols.")
        return df

    long = df.melt(id_vars=id_vars + ["series"], var_name="year_str", value_name="value")
    long["year"] = long["year_str"].str.replace("YR", "").astype(int)
    long = long.dropna(subset=["value"])

    # latest per economy+series
    latest = (
        long.sort_values(["economy", "series", "year"], ascending=[True, True, False])
        .groupby(["economy", "series"], as_index=False)
        .first()
    )
    latest = latest.rename(columns={"economy": "iso3"})
    return latest[["iso3", "series", "year", "value"]]


if __name__ == "__main__":
    # Quick smoke test
    isos = get_un_iso3_list()[:5]  # small for test
    print("Sample ISOs:", isos)
    raw = fetch_wdi(iso3_list=isos, years=[2020, 2023, 2024])
    print(raw.head())
    latest = get_latest_values(raw)
    print(latest.head(10))

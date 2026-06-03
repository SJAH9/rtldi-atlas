"""
V-Dem data handling for RTLDI ATLAS.

Because the official download page uses a form/POST for the large ZIP (v16 Full+Others or Core ~ hundreds of MB),
this module:
- Documents the exact steps to obtain the CSV.
- Provides a loader that reads the extracted CSV with usecols for only the variables we need (memory friendly).
- Can validate presence of required columns against the crosswalk.

Recommended (as of v16, March 2026):
1. Go to https://www.v-dem.net/data/the-v-dem-dataset/
2. Download "Country-Year: V-Dem Core version 16" (smaller, sufficient for most of our indicators) 
   OR "Full+Others" if you need extra conflict or other vars.
3. Unzip and place the CSV (usually named something like "V-Dem-CY-Core-v16.csv" or "V-Dem-CY-Full+Others-v16.csv")
   into data/raw/ as e.g. V-Dem-CY-Core-v16.csv

Then run loaders.
"""

from __future__ import annotations
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import warnings

# Core variables we care about from crosswalk (add more as needed)
# Use the main point estimate column (no suffix)
VDEM_NEEDED: List[str] = [
    "country_name",
    "country_text_id",  # often 3-letter
    "year",
    # Personal integrity / violence
    "v2cltort",         # torture
    "v2clkill",         # political killings
    # Judiciary
    "v2juhcind",        # high court ind.
    "v2juncind",        # lower court ind.
    # Access / impartial
    "v2cltrnslw",       # transparent laws
    "v2clrspct",        # rigorous impartial admin (for legal / arb)
    "v2clacjstm", "v2clacjstw",  # access to justice m/w
    "v2xcl_acjst",      # access to justice index (D)
    # Expression
    "v2x_freexp",       # freedom of expression index
    # High level (good for robustness / missing fill)
    "v2x_rule",         # rule of law index
    "v2x_clphy",        # physical violence index
    "v2x_civlib",       # civil liberties index
]

# V-Dem often also provides *_mean, *_sd etc. We primarily use the plain name (measurement model point est.)

DEFAULT_VDEM_CSV = "data/raw/V-Dem-CY-Core-v16.csv"


def find_vdem_csv(preferred: Optional[str] = None) -> Optional[Path]:
    candidates = [
        preferred,
        DEFAULT_VDEM_CSV,
        "data/raw/V-Dem-CY-Full+Others-v16.csv",
        "data/raw/V-Dem-CY-Core-v16.csv",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    # Search for any likely
    for p in Path("data/raw").glob("*V-Dem*CY*.csv"):
        return p
    return None


def load_vdem_subset(
    csv_path: Optional[str] = None,
    years: Optional[List[int]] = None,
    iso3_filter: Optional[List[str]] = None,
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Load only needed columns + filter to recent years + UN members if provided.
    Returns df with at least the requested columns + year + identifiers.
    """
    path = find_vdem_csv(csv_path)
    if path is None:
        raise FileNotFoundError(
            "No V-Dem CSV found. See module docstring for download instructions. "
            "Place extracted CSV in data/raw/ as V-Dem-CY-*-v16.csv"
        )

    use_cols = columns or VDEM_NEEDED
    # Always ensure basics
    for must in ["country_name", "year"]:
        if must not in use_cols:
            use_cols = [must] + use_cols

    print(f"Loading V-Dem subset from {path} (usecols={len(use_cols)})...")
    df = pd.read_csv(path, usecols=lambda c: c in use_cols or c in ["country_name", "year", "country_text_id"])

    if years:
        df = df[df["year"].isin(years)]

    if iso3_filter:
        # V-Dem country_text_id is often 3-letter like "AFG", but verify in your extract.
        # Fall back to name matching via country-converter if needed.
        if "country_text_id" in df.columns:
            df = df[df["country_text_id"].isin(iso3_filter)]
        else:
            warnings.warn("No country_text_id; name matching not implemented here yet.")

    df = df.sort_values(["country_name", "year"])
    return df


def get_vdem_for_iso3_year(
    df: pd.DataFrame,
    iso3: str,
    year: int,
    var: str,
) -> Optional[float]:
    """Helper to pull a single value after loading."""
    row = df[(df.get("country_text_id") == iso3) & (df["year"] == year)]
    if len(row) == 0:
        # try name match? skipped for now
        return None
    val = row[var].iloc[0] if var in row.columns else None
    return float(val) if pd.notna(val) else None


if __name__ == "__main__":
    path = find_vdem_csv()
    print("V-Dem CSV present?", path)
    if path:
        # Small test load
        sm = load_vdem_subset(years=[2023, 2024], columns=["v2cltort", "v2clkill", "v2x_rule"])
        print(sm.head())
        print("Unique countries in slice:", sm["country_name"].nunique())


# --- Real RTLP computation from crosswalk (for ATLAS) ---

VDEM_R_VARS = [
    "country_text_id", "year",
    "v2cltrnslw",   # 1 legal
    "v2juhcind", "v2juncind",  # 2 judiciary
    "v2clkill",     # 3+6 law_enforce + civilian
    "v2cltort",     # 5 torture
    "v2xcl_acjst",  # 4+7 arb + access (index)
    "v2x_freexp",   # 8 expression
]

def load_vdem_for_rtlp(year: int = 2026, vdem_csv: Optional[str] = None) -> pd.DataFrame:
    """Load the minimal columns for the 8 V-Dem RTLP components for a given year.
    If the exact year is not present, falls back to the maximum year available in the file (for 2026+ updates).
    """
    path = find_vdem_csv(vdem_csv)
    if path is None:
        raise FileNotFoundError("V-Dem CSV not found. Place or symlink it in data/raw/ or pass path.")
    df = pd.read_csv(path, usecols=lambda c: c in VDEM_R_VARS)
    if year in df["year"].values:
        df = df[df["year"] == year].copy()
    else:
        max_year = df["year"].max()
        print(f"Warning: year {year} not in V-Dem file (max={max_year}). Using {max_year}.")
        df = df[df["year"] == max_year].copy()
    return df


def compute_rtlp_vdem_row(row: pd.Series, cfg: Optional["RTLDIConfig"] = None) -> float:
    """Return the 0-1 score from the 8 V-Dem components for one row (socio #9 added outside)."""
    from .rtl_di import binarize_vdem_component, binarize_vdem_index, RTLDIConfig
    import numpy as _np
    cfg = cfg or RTLDIConfig()
    bins = []
    # 1. Legal: v2cltrnslw (component 0-4)
    bins.append(binarize_vdem_component(row.get("v2cltrnslw"), cfg.thresh_vdem_0_4))
    # 2. Judiciary
    j = float(_np.nanmean([row.get("v2juhcind"), row.get("v2juncind")])) if pd.notna(row.get("v2juhcind")) or pd.notna(row.get("v2juncind")) else _np.nan
    bins.append(binarize_vdem_component(j, cfg.thresh_vdem_0_4))
    # 3. Law enforcement accountability
    bins.append(binarize_vdem_component(row.get("v2clkill"), cfg.thresh_vdem_0_4))
    # 4. Arbitrary detention (use access index as strong proxy)
    bins.append(binarize_vdem_index(row.get("v2xcl_acjst"), 0.5))
    # 5. Torture
    bins.append(binarize_vdem_component(row.get("v2cltort"), cfg.thresh_vdem_0_4))
    # 6. Civilian protection in conflict (reuse killings)
    bins.append(binarize_vdem_component(row.get("v2clkill"), cfg.thresh_vdem_0_4))
    # 7. Access to justice
    bins.append(binarize_vdem_index(row.get("v2xcl_acjst"), 0.5))
    # 8. Expression + whistleblower
    bins.append(binarize_vdem_index(row.get("v2x_freexp"), 0.5))
    yes = sum(b for b in bins if pd.notna(b))
    # Return as fraction of 8 for now; caller will combine with #9 to /9
    return yes / 8.0


def get_vdem_r_for_iso3s(year: int = 2026, iso3s: Optional[list] = None) -> pd.DataFrame:
    """Return df with iso3 (from country_text_id), r_vdem8 (0-1 from 8 components)."""
    df = load_vdem_for_rtlp(year)
    df["iso3"] = df["country_text_id"].astype(str).str.upper()
    if iso3s:
        df = df[df["iso3"].isin([i.upper() for i in iso3s])]
    df["r_vdem8"] = df.apply(compute_rtlp_vdem_row, axis=1)
    return df[["iso3", "r_vdem8", "year"]].copy()

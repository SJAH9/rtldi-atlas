"""
RTLDI core computation (from Hubbard, Causality and Attraction v3).

Equation (D.4 / 5.1):
    ΔG = η × (1 − R) × G₀

Where:
- ΔG : annual GDP per capita loss (current or constant USD)
- η  : 0.05 (base)
- R  : RTLP score [0,1]
- G₀ : baseline GDP per capita

Also supports aggregate = ΔG * population.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import numpy as np


@dataclass
class RTLDIConfig:
    """Configuration for RTLDI calculation."""
    eta: float = 0.05
    # Binarization defaults (see docs/indicator_crosswalk.md for justification)
    # For V-Dem 0-4 components (higher=better protection)
    thresh_vdem_0_4: float = 2.0
    # For V-Dem indices (typically centered or 0-1; 0 is roughly mean in many)
    thresh_vdem_index: float = 0.0
    # For WB socioeconomic (example: undernourish <=5% AND poverty low)
    undernourish_max_pct: float = 5.0
    poverty_headcount_max_pct: float = 10.0
    # How to handle gender splits (min = conservative for "equal")
    gender_strategy: str = "avg"  # or "min"


def compute_delta_g(r: float, g0: float, eta: float = 0.05) -> float:
    """
    Compute annual GDP per capita loss ΔG.

    Parameters
    ----------
    r : float
        RTLP score in [0, 1]. 1 = full protection.
    g0 : float
        Baseline GDP per capita (e.g. current US$).
    eta : float
        Sensitivity (default 0.05 per source).

    Returns
    -------
    float
        ΔG in same units as g0.
    """
    if not (0.0 <= r <= 1.0):
        raise ValueError(f"R (RTLP) must be in [0,1], got {r}")
    if g0 < 0:
        raise ValueError(f"G0 must be non-negative, got {g0}")
    return eta * (1.0 - r) * g0


def total_deficit(delta_g: float, population: float) -> float:
    """Aggregate national annual deficit = per capita loss × population."""
    if delta_g < 0 or population < 0:
        raise ValueError("delta_g and population must be non-negative")
    return delta_g * population


def compute_rtlp_from_binaries(yes_count: int, total: int = 9) -> float:
    """Simple RTLP from count of yes answers (0-9)."""
    if not (0 <= yes_count <= total):
        raise ValueError(f"yes_count {yes_count} out of range for total={total}")
    return yes_count / total


def binarize_vdem_component(value: Optional[float], thresh: Optional[float] = None) -> int:
    """
    Binarize a V-Dem component (typically interval from 0-4 ordinal model).
    Higher value = stronger protection.
    """
    if value is None or np.isnan(value):
        return 0  # conservative: no credit for missing
    t = thresh if thresh is not None else RTLDIConfig().thresh_vdem_0_4
    return 1 if value >= t else 0


def binarize_vdem_index(value: Optional[float], thresh: Optional[float] = None) -> int:
    """Binarize a V-Dem index (higher = better)."""
    if value is None or np.isnan(value):
        return 0
    t = thresh if thresh is not None else RTLDIConfig().thresh_vdem_index
    return 1 if value >= t else 0


def score_socioeconomic(
    undernourish_pct: Optional[float],
    poverty_pct: Optional[float],
    config: Optional[RTLDIConfig] = None,
) -> int:
    """
    Binarize indicator #9 using WB data.
    "yes" if food insecurity and extreme poverty are both low.
    """
    cfg = config or RTLDIConfig()
    if undernourish_pct is None or np.isnan(undernourish_pct):
        undernourish_pct = 100.0  # conservative fail
    if poverty_pct is None or np.isnan(poverty_pct):
        poverty_pct = 100.0

    food_ok = undernourish_pct <= cfg.undernourish_max_pct
    poverty_ok = poverty_pct <= cfg.poverty_headcount_max_pct
    return 1 if (food_ok and poverty_ok) else 0


def compute_r_from_components(
    components: Dict[str, Any],
    config: Optional[RTLDIConfig] = None,
) -> float:
    """
    Compute R (0-1) from a dict of (possibly continuous) component proxies.

    Expected keys (see crosswalk):
      legal, judiciary, law_enforce, arb_detention, torture,
      civilian_conflict, access_justice, expression, socioeconomic

    Values can be raw V-Dem/WB numbers; will be binarized internally.
    """
    cfg = config or RTLDIConfig()
    bins: List[int] = []

    # 1 legal
    bins.append(binarize_vdem_component(components.get("legal"), cfg.thresh_vdem_0_4))
    # 2 judiciary (use avg if list/tuple of two)
    jval = components.get("judiciary")
    if isinstance(jval, (list, tuple)) and len(jval) == 2:
        jval = np.nanmean([x for x in jval if x is not None])
    bins.append(binarize_vdem_component(jval, cfg.thresh_vdem_0_4))
    # 3 law_enforce
    bins.append(binarize_vdem_component(components.get("law_enforce"), cfg.thresh_vdem_0_4))
    # 4 arb_detention (prefer index)
    bins.append(binarize_vdem_index(components.get("arb_detention"), cfg.thresh_vdem_index))
    # 5 torture
    bins.append(binarize_vdem_component(components.get("torture"), cfg.thresh_vdem_0_4))
    # 6 civilian_conflict
    bins.append(binarize_vdem_component(components.get("civilian_conflict"), cfg.thresh_vdem_0_4))
    # 7 access_justice (index)
    bins.append(binarize_vdem_index(components.get("access_justice"), cfg.thresh_vdem_index))
    # 8 expression (index)
    bins.append(binarize_vdem_index(components.get("expression"), cfg.thresh_vdem_index))
    # 9 socioeconomic (special)
    bins.append(
        score_socioeconomic(
            components.get("undernourish_pct"),
            components.get("poverty_pct"),
            cfg,
        )
    )

    yes = sum(bins)
    return yes / 9.0


# Convenience for full row computation
def compute_rtl_di_for_row(
    r: float,
    g0: float,
    population: Optional[float] = None,
    eta: float = 0.05,
) -> Dict[str, float]:
    """Return dict with per_capita_loss and (if pop given) total_deficit."""
    dg = compute_delta_g(r, g0, eta)
    out = {"r": r, "g0": g0, "eta": eta, "delta_g_per_capita": dg}
    if population is not None and population > 0:
        out["total_deficit"] = total_deficit(dg, population)
        out["population"] = population
    return out

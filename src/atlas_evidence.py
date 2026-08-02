"""Shared provenance, crosswalk, and regression evidence for atlas outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .lever_display import LEVER_DISPLAY


VDEM_DATASET_URL = "https://www.v-dem.net/data/the-v-dem-dataset/"
VDEM_CORE_URL = "https://www.v-dem.net/data/the-v-dem-dataset/country-year-v-dem-core-v16/"
VDEM_ARCHIVE_URL = "https://www.v-dem.net/data/dataset-archive/"
VDEM_CODEBOOK_URL = "https://www.v-dem.net/documents/70/codebook_v16.pdf"
VDEM_V15_SOURCE_URL = "https://raw.githubusercontent.com/vdeminstitute/vdemdata/V15/data/vdem.RData"
VDEM_V15_SHA256 = "4b715190a1e351a81daf11cbe6f9f77e67d8914f0ed612b93e2d8fba5523e540"
WORLD_BANK_DATA_URL = "https://data.worldbank.org/"
WORLD_BANK_API_URL = "https://api.worldbank.org/v2/"


# This table describes the executable nine-distinct-lever 2026 pipeline.
LEVER_CROSSWALK: dict[int, dict[str, Any]] = {
    1: {
        "question": "Does the entity have provisions explicitly protecting the right to life?",
        "source": "V-Dem",
        "fields": ["v2cltrnslw"],
        "transform": "v2cltrnslw >= 2.0",
        "proxy": "Transparent laws with predictable enforcement",
        "caveat": "Operational de-facto proxy; it is not a direct constitutional right-to-life field.",
    },
    2: {
        "question": "Is there an independent judiciary capable of upholding right-to-life laws?",
        "source": "V-Dem",
        "fields": ["v2juhcind", "v2juncind"],
        "transform": "mean(v2juhcind, v2juncind) >= 2.0",
        "proxy": "High-court and lower-court independence",
        "caveat": "The two available court estimates are averaged when either is present.",
    },
    3: {
        "question": "Are law-enforcement agencies accountable for unlawful killings?",
        "source": "V-Dem",
        "fields": ["v2clkill"],
        "transform": "v2clkill >= 2.0",
        "proxy": "Freedom from political killings",
        "caveat": "Outcome/accountability proxy for unlawful state killings.",
    },
    4: {
        "question": "Is arbitrary detention prohibited with legal recourse?",
        "source": "V-Dem",
        "fields": ["v2xcl_acjst"],
        "transform": "v2xcl_acjst >= 0.5",
        "proxy": "Access to justice index",
        "caveat": "There is no direct arbitrary-detention field in the current Core crosswalk; access to justice is used as the closest recourse proxy.",
    },
    5: {
        "question": "Are measures in place to prevent torture and inhumane treatment?",
        "source": "V-Dem",
        "fields": ["v2cltort"],
        "transform": "v2cltort >= 2.0",
        "proxy": "Freedom from torture",
        "caveat": "Direct substantive proxy, converted from the model estimate to a binary atlas score.",
    },
    6: {
        "question": "In conflict areas, are mechanisms protecting civilians?",
        "source": "V-Dem",
        "fields": ["v2x_clphy"],
        "transform": "v2x_clphy >= 0.5",
        "proxy": "Physical violence index",
        "caveat": "High-level physical-integrity proxy, distinct from lever 3's political-killings component.",
    },
    7: {
        "question": "Can individuals obtain fair remedies for right-to-life violations?",
        "source": "V-Dem",
        "fields": ["v2clrspct"],
        "transform": "v2clrspct >= 2.0",
        "proxy": "Rigorous and impartial public administration",
        "caveat": "Administrative impartiality is the distinct operational proxy for whether remedies are applied fairly.",
    },
    8: {
        "question": "Are expression and whistleblower rights upheld?",
        "source": "V-Dem",
        "fields": ["v2x_freexp"],
        "transform": "v2x_freexp >= 0.5",
        "proxy": "Freedom of expression and alternative information index",
        "caveat": "Expression is the operational proxy; the current crosswalk has no direct whistleblower-law variable.",
    },
    9: {
        "question": "Are food and minimum material conditions adequate to sustain life?",
        "source": "World Bank WDI",
        "fields": ["SN.ITK.DEFC.ZS", "SI.POV.DDAY"],
        "transform": "undernourishment <= 5% AND poverty headcount <= 10%",
        "proxy": "Prevalence of undernourishment and international-poverty headcount",
        "caveat": "Missing values are conservatively treated as failure. This is an outcome-based basic-needs proxy, not a V-Dem field.",
    },
}


def ncm_isolated_entity_note() -> str:
    return (
        "NCM Isolated Entity is not a V-Dem variable. In this atlas it names the focal unit of analysis: "
        "one UN member state observed for one reference year, temporarily treated as a bounded entity so its "
        "nine conditions and GDP can be compared consistently. The country is not assumed to be causally isolated; "
        "trade, geography, resources, history, conflict, and regional systems remain outside this reduced cross-section."
    )


def lever_totals(data: dict[str, Any]) -> dict[int, float]:
    if data.get("global_indicator_losts"):
        return {i + 1: float(value or 0) for i, value in enumerate(data["global_indicator_losts"])}
    return {
        int(item.get("num", i + 1)): float(item.get("attributable_lost_gdp") or 0)
        for i, item in enumerate(data.get("indicators", []))
    }


def _fit(y: np.ndarray, x: np.ndarray, weights: np.ndarray | None = None) -> dict[str, Any]:
    mask = np.isfinite(y) & np.isfinite(x)
    if weights is not None:
        mask &= np.isfinite(weights) & (weights > 0)
    y, x = y[mask], x[mask]
    w = np.ones(len(y)) if weights is None else weights[mask].astype(float)
    w = w / np.mean(w)
    X = np.column_stack((np.ones(len(x)), x))
    xtw = X.T * w
    beta = np.linalg.solve(xtw @ X, xtw @ y)
    resid = y - X @ beta
    bread = np.linalg.inv(xtw @ X)
    meat = X.T @ (X * (w * resid)[:, None] ** 2)
    cov = bread @ meat @ bread * (len(y) / max(1, len(y) - X.shape[1]))
    se = np.sqrt(np.diag(cov))
    dof = max(1, len(y) - X.shape[1])
    t_value = beta[1] / se[1] if se[1] else np.nan
    p_value = float(2 * stats.t.sf(abs(t_value), dof)) if np.isfinite(t_value) else np.nan
    ybar = np.average(y, weights=w)
    ss_res = float(np.sum(w * resid**2))
    ss_tot = float(np.sum(w * (y - ybar) ** 2))
    return {
        "n": int(len(y)), "intercept": float(beta[0]), "slope": float(beta[1]),
        "se": float(se[1]), "p": p_value, "r2": 1 - ss_res / ss_tot if ss_tot else np.nan,
    }


def regression_evidence(rows: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame([
        {
            "iso3": row.get("iso3"), "gdp": float(row.get("g0") or np.nan),
            "population": float(row.get("population") or np.nan),
            "lever_count": sum(int(c.get("bin", 0)) for c in row.get("components", [])),
        }
        for row in rows
    ])
    main = _fit(np.log(frame["gdp"].to_numpy()), frame["lever_count"].to_numpy(), frame["population"].to_numpy())
    main["eta"] = float(np.exp(main["slope"]) - 1)
    main["ci_low"] = float(np.exp(main["slope"] - 1.96 * main["se"]) - 1)
    main["ci_high"] = float(np.exp(main["slope"] + 1.96 * main["se"]) - 1)

    wb = pd.read_csv("data/processed/wb_un_members_2023_2024_latest.csv").rename(columns={"economy": "iso3"})
    merged = frame.merge(wb, on="iso3", how="left")
    comparators = []
    for field, label, log_x in [
        ("population_y", "Population", True),
        ("undernourish_pct", "Undernourishment", False),
        ("poverty_215_pct", "Extreme-poverty headcount", False),
    ]:
        x = merged[field].to_numpy(dtype=float)
        if log_x:
            x = np.log(x)
        fit = _fit(np.log(merged["gdp"].to_numpy()), x)
        fit.update({"label": label, "outcome": "log GDP per capita", "weighted": False})
        comparators.append(fit)

    growth = None
    raw_path = Path("data/processed/wb_2023_2024_raw.csv")
    if raw_path.exists():
        raw = pd.read_csv(raw_path)
        g = raw[raw["series"] == "NY.GDP.PCAP.CD"][["economy", "2023", "2024"]].copy()
        g["growth"] = (g["2024"] / g["2023"] - 1) * 100
        gm = frame.merge(g, left_on="iso3", right_on="economy", how="inner")
        growth = _fit(gm["growth"].to_numpy(), gm["lever_count"].to_numpy())
        growth.update({"outcome": "2023-2024 current-US$ GDP-per-capita change", "weighted": False})
    return {"main": main, "comparators": comparators, "growth": growth}


def evidence_bundle(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "crosswalk": LEVER_CROSSWALK,
        "lever_totals": lever_totals(data),
        "regression": regression_evidence(data["detailed_all"]),
        "ncm_note": ncm_isolated_entity_note(),
        "lever_display": LEVER_DISPLAY,
    }

"""Small map-geometry corrections for RTLDI Plotly choropleths."""

from __future__ import annotations

from typing import Optional

import pandas as pd

try:
    from plotly.colors import sample_colorscale
except Exception:  # pragma: no cover - only used when Plotly is installed
    sample_colorscale = None


# Plotly's built-in ISO-3 geometry for FRA includes French Guiana. The atlas is
# scored at the UN member-state level, but the European print/web maps should
# display metropolitan France so the fitted map bounds do not jump to South
# America.
METROPOLITAN_FRANCE_LON = [
    -5.15,
    -4.25,
    -2.00,
    0.20,
    2.10,
    4.15,
    6.15,
    7.70,
    7.55,
    6.35,
    5.35,
    4.00,
    3.10,
    1.45,
    -1.30,
    -2.50,
    -4.40,
    -5.15,
]
METROPOLITAN_FRANCE_LAT = [
    48.55,
    49.65,
    50.15,
    50.95,
    50.75,
    49.95,
    49.10,
    48.25,
    44.20,
    43.00,
    43.20,
    43.45,
    42.45,
    42.60,
    43.30,
    46.00,
    47.70,
    48.55,
]


def split_france_for_metropolitan_display(df: pd.DataFrame) -> tuple[pd.DataFrame, Optional[dict]]:
    """Return choropleth rows without FRA plus the France row for custom drawing."""
    if "iso3" not in df.columns:
        return df, None
    iso = df["iso3"].astype(str).str.upper()
    france_rows = df[iso == "FRA"]
    if france_rows.empty:
        return df, None
    return df[iso != "FRA"].copy(), france_rows.iloc[0].to_dict()


def _r_color(r: float) -> str:
    if sample_colorscale:
        return sample_colorscale("Viridis", [max(0.0, min(1.0, float(r)))])[0]
    return "#35b779"


def add_metropolitan_france_trace(fig, france: Optional[dict], *, showlegend: bool = False) -> None:
    """Draw metropolitan France after removing Plotly's FRA ISO geometry."""
    if not france:
        return
    r = float(france.get("r") or 0.0)
    country = str(france.get("country") or "France")
    fig.add_scattergeo(
        lon=METROPOLITAN_FRANCE_LON,
        lat=METROPOLITAN_FRANCE_LAT,
        mode="lines",
        fill="toself",
        fillcolor=_r_color(r),
        line=dict(color="rgba(80,80,80,0.45)", width=0.5),
        name=country,
        text=[country] * len(METROPOLITAN_FRANCE_LON),
        customdata=[[france.get("iso3", "FRA"), r]] * len(METROPOLITAN_FRANCE_LON),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "iso3=%{customdata[0]}<br>"
            "R=%{customdata[1]:.3f}<extra></extra>"
        ),
        showlegend=showlegend,
    )


def apply_european_france_bounds(fig, *, kind: str) -> None:
    """Keep fitted France maps in Europe after replacing the FRA choropleth geometry."""
    if kind == "france":
        fig.update_geos(
            lonaxis_range=[-6.5, 9.5],
            lataxis_range=[41.0, 52.0],
            center=dict(lon=2.0, lat=46.5),
        )
    elif kind == "western_europe":
        fig.update_geos(
            lonaxis_range=[-7.5, 10.5],
            lataxis_range=[41.0, 55.5],
            center=dict(lon=1.5, lat=48.0),
        )
    elif kind == "eurozone":
        fig.update_geos(
            lonaxis_range=[-11.5, 35.5],
            lataxis_range=[34.0, 71.5],
            center=dict(lon=12.0, lat=51.0),
        )

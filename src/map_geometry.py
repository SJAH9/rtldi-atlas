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
# America. Coordinates are a simplified European-France boundary extracted from
# datasets/geo-countries GeoJSON (mainland + Corsica only).
METROPOLITAN_FRANCE_LON = [
    2.522, 2.587, 2.787, 3.129, 3.271, 3.608, 3.697, 4.003, 4.198, 4.132,
    4.646, 4.816, 4.849, 5.259, 5.456, 5.746, 5.961, 6.403, 6.714, 6.914,
    7.043, 7.274, 7.410, 7.635, 8.200, 7.810, 7.751, 7.586, 7.621, 7.512,
    7.586, 7.379, 6.973, 6.867, 7.037, 6.443, 6.429, 6.118, 6.094, 5.955,
    5.959, 6.140, 6.281, 6.214, 6.269, 6.483, 6.787, 6.766, 7.022, 6.801,
    6.796, 7.161, 7.055, 6.603, 6.745, 7.007, 7.055, 6.836, 6.918, 6.866,
    6.983, 7.331, 7.656, 7.690, 7.476, 6.731, 6.591, 6.693, 6.680, 6.193,
    6.180, 5.347, 5.294, 5.034, 5.026, 5.226, 5.029, 5.051, 4.868, 4.856,
    4.695, 4.820, 3.953, 3.114, 3.042, 3.181, 2.934, 2.662, 2.277, 1.996,
    1.712, 1.722, 1.429, 1.343, 0.813, 0.656, 0.644, -0.039, -0.323, -0.569,
    -0.760, -1.286, -1.457, -1.404, -1.622, -1.796, -1.477, -1.257, -1.187,
    -1.045, -1.172, -1.260, -1.085, -0.766, -0.535, -0.596, -0.494, -0.656,
    -0.795, -1.247, -1.164, -0.987, -1.152, -1.049, -1.211, -1.111, -1.795,
    -2.119, -1.991, -2.241, -2.161, -1.727, -2.010, -2.278, -2.542, -2.436,
    -2.556, -2.392, -2.495, -2.364, -2.909, -2.741, -2.707, -2.919, -2.975,
    -2.940, -3.123, -3.132, -3.201, -3.118, -3.358, -3.283, -3.358, -3.283,
    -3.446, -4.132, -4.185, -4.372, -4.435, -4.728, -4.285, -4.379, -4.557,
    -4.626, -4.547, -4.187, -4.454, -4.290, -4.768, -4.765, -3.974, -3.852,
    -3.810, -3.585, -3.515, -3.230, -3.221, -3.091, -3.125, -3.008, -2.682,
    -2.316, -2.214, -2.052, -1.980, -2.029, -1.946, -1.844, -1.796, -1.357,
    -1.554, -1.603, -1.508, -1.594, -1.610, -1.548, -1.816, -1.935, -1.607,
    -1.263, -1.306, -1.123, -0.219, 0.411, 0.493, 0.077, 0.236, 1.221,
    1.521, 1.673, 1.542, 1.610, 1.581, 2.522, None, 8.566, 8.688, 8.549,
    8.709, 9.118, 9.292, 9.347, 9.464, 9.443, 9.528, 9.560, 9.403, 9.402,
    9.223, 8.792, 8.923, 8.655, 8.805, 8.614, 8.586, 8.745, 8.566,
]
METROPOLITAN_FRANCE_LAT = [
    51.088, 50.845, 50.723, 50.779, 50.527, 50.477, 50.298, 50.344, 50.258, 49.975,
    49.984, 50.161, 49.794, 49.691, 49.499, 49.549, 49.441, 49.465, 49.159, 49.207,
    49.108, 49.105, 49.169, 49.038, 48.959, 48.615, 48.341, 48.130, 47.971, 47.707,
    47.585, 47.431, 47.489, 47.354, 47.330, 46.944, 46.761, 46.583, 46.253, 46.200,
    46.130, 46.150, 46.240, 46.315, 46.375, 46.449, 46.414, 46.152, 45.925, 45.826,
    45.718, 45.411, 45.214, 45.103, 44.908, 44.822, 44.685, 44.534, 44.436, 44.372,
    44.242, 44.125, 44.176, 44.067, 43.765, 43.408, 43.269, 43.273, 43.202, 43.109,
    43.036, 43.216, 43.355, 43.335, 43.409, 43.480, 43.559, 43.429, 43.421, 43.342,
    43.579, 43.346, 43.540, 43.106, 42.629, 42.431, 42.470, 42.339, 42.429, 42.349,
    42.494, 42.610, 42.595, 42.709, 42.832, 42.838, 42.684, 42.685, 42.843, 42.773,
    42.947, 43.109, 43.045, 43.243, 43.247, 43.374, 43.580, 44.556, 44.665, 44.669,
    44.778, 44.627, 45.569, 45.326, 44.895, 45.025, 44.998, 45.099, 45.477, 45.710,
    45.807, 45.717, 45.868, 46.039, 46.175, 46.303, 46.495, 46.820, 47.035, 47.142,
    47.271, 47.211, 47.320, 47.246, 47.300, 47.307, 47.383, 47.424, 47.491, 47.506,
    47.558, 47.551, 47.643, 47.596, 47.664, 47.561, 47.599, 47.478, 47.640, 47.732,
    47.697, 47.691, 47.711, 47.787, 47.705, 47.924, 47.813, 47.807, 47.976, 48.041,
    48.115, 48.232, 48.177, 48.287, 48.347, 48.308, 48.335, 48.432, 48.345, 48.520,
    48.733, 48.630, 48.733, 48.683, 48.842, 48.872, 48.794, 48.871, 48.760, 48.821,
    48.509, 48.699, 48.582, 48.650, 48.514, 48.643, 48.699, 48.712, 48.616, 48.643,
    48.747, 48.849, 49.034, 49.029, 49.216, 49.225, 49.384, 49.724, 49.650, 49.696,
    49.558, 49.345, 49.280, 49.452, 49.494, 49.535, 49.729, 49.979, 50.215, 50.193,
    50.278, 50.371, 50.869, 51.088, None, 42.209, 42.273, 42.377, 42.579, 42.732,
    42.675, 43.004, 42.990, 42.641, 42.564, 42.147, 41.953, 41.706, 41.373, 41.561,
    41.695, 41.750, 41.907, 41.901, 41.969, 42.057, 42.209,
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
        line=dict(color="rgba(255,255,255,0.35)", width=0.2),
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

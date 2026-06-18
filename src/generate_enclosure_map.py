#!/usr/bin/env python3
"""
Generate choropleth map(s) of "enclosure strength" (RTLP R score, 0-1) across the 193 UN Member States.

Uses Mollweide (equal-area) projection for the world view (good area preservation for choropleths).
True Dymaxion or Goode's butterfly/interrupted projections are not supported by Plotly's geo engine;
Mollweide is the recommended low-distortion alternative within the current stack.

Uses the pre-built 2026 ATLAS data (R computed from 8 V-Dem 2024 indicators + 1 real WB socioeconomic per the source crosswalk;
G₀ = 2026-fresh GDP per capita as the more dynamic variable per project rule).

Outputs (to outputs/figures/):
- rtl_di_enclosure_strength_2026_choropleth.png  (high-res static for print / ebook)
- rtl_di_enclosure_strength_2026_choropleth.pdf  (vector)
- rtl_di_enclosure_strength_2026_choropleth.html (interactive with hover for all details)

Usage:
  python3 -m src.generate_enclosure_map
  # or with year override (future data)
  python3 -m src.generate_enclosure_map --year 2026 --input outputs/atlas/rtl_di_atlas_un_members_2026.csv

Requires (beyond core atlas): plotly (already in some envs), kaleido (for static export).
Add to pip:  pip install plotly kaleido

The map visualizes "enclosure strength" directly as the RTLP R from the source document
(Hubbard 2026V3): higher R = stronger protection of the right to life within the nested causal enclosures.

Fidelity: exactly 193 UN members, R in [0,1], vintage labels on every artifact.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio

# Default output base (committed as demo per .gitignore whitelist)
DEFAULT_ATLAS_CSV = "outputs/atlas/rtl_di_atlas_un_members_2026.csv"
OUT_DIR = Path("outputs/figures")
BASE_NAME = "rtl_di_enclosure_strength_2026_choropleth"


def load_atlas_for_map(path: str | None = None) -> pd.DataFrame:
    """Load the master atlas table and keep only columns needed for the choropleth + hover."""
    csv_path = Path(path) if path else Path(DEFAULT_ATLAS_CSV)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Atlas CSV not found at {csv_path}. Run `python -m src.build_atlas --year 2026` first."
        )
    df = pd.read_csv(csv_path)

    # Standardize / select
    keep = ["iso3", "country", "UNregion", "r", "g0", "g0_year", "vdem_year",
            "delta_g_per_capita", "total_deficit_usd", "population", "rank_by_r_lowest"]
    cols = [c for c in keep if c in df.columns]
    df = df[cols].copy()

    # Drop rows without usable R or iso3 (should be none for 193)
    df = df.dropna(subset=["r", "iso3"])
    df["iso3"] = df["iso3"].astype(str).str.upper()

    # Ensure r is float in [0,1]
    df["r"] = pd.to_numeric(df["r"], errors="coerce")
    df = df[(df["r"] >= 0) & (df["r"] <= 1)]

    print(f"Loaded {len(df)} countries with valid R from {csv_path}")
    return df


def make_choropleth(df: pd.DataFrame, atlas_year: int = 2026) -> px.choropleth:
    """Build a clean, publication-grade choropleth figure with full vintage/source annotation."""
    # Title + subtitle
    title = (
        f"Enclosure Strength (RTLP R) — UN Member States<br>"
        f"<sub>RTLDI ATLAS {atlas_year} | R = Right-to-Life Protection score (0 = weakest, 1 = strongest)</sub>"
    )

    fig = px.choropleth(
        df,
        locations="iso3",
        locationmode="ISO-3",
        color="r",
        color_continuous_scale="Viridis",
        range_color=[0.0, 1.0],
        hover_name="country",
        hover_data={
            "r": ":.3f",
            "UNregion": True,
            "vdem_year": True,
            "g0_year": True,
            "delta_g_per_capita": ":.2f",
            "total_deficit_usd": ":.0f",
            "population": ":,.0f",
        },
        labels={
            "r": "Enclosure Strength R",
            "UNregion": "UN Region",
            "vdem_year": "V-Dem year",
            "g0_year": "GDP baseline year",
            "delta_g_per_capita": "ΔG per capita (USD)",
            "total_deficit_usd": "Total annual capital exclusions (USD)",
            "population": "Population",
        },
    )

    # Improve geo aesthetics and projection.
    # Using "mollweide" (equal-area pseudocylindrical) for better area preservation
    # in a world choropleth than the previous "natural earth".
    # Note: True Dymaxion (icosahedral/butterfly) or Goode's interrupted homolosine
    # are not supported in Plotly's built-in geo projections. Mollweide is a strong
    # low-distortion choice for thematic maps of enclosure strength.
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="rgba(180,180,180,0.6)",
        showland=True,
        landcolor="rgba(245,245,245,0.9)",
        showocean=True,
        oceancolor="rgba(230,242,255,0.6)",
        showlakes=True,
        lakecolor="rgba(230,242,255,0.6)",
        projection_type="mollweide",
        lataxis_showgrid=False,
        lonaxis_showgrid=False,
        framecolor="rgba(150,150,150,0.5)",
    )

    # Colorbar styling
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text="Enclosure<br>Strength R<br>(0–1)", font=dict(size=11)),
            tickmode="array",
            tickvals=[0.0, 0.25, 0.5, 0.75, 1.0],
            ticktext=["0.00", "0.25", "0.50", "0.75", "1.00"],
            len=0.6,
            thickness=12,
        ),
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=16)),
        margin=dict(l=10, r=10, t=70, b=95),
        height=820,
        width=1380,
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    # Prominent data vintage + source footnote (visible in static exports)
    # Positioned below the map area
    note = (
        "R from 8 V-Dem components (crosswalk, year=2024) + 1 World Bank socioeconomic indicator (#9) + 2026-fresh G₀ (GDP per capita current US$). "
        "GDP is the more dynamic variable; V-Dem RTLP components use the file's latest available year (2024). "
        "ΔG = 0.05 × (1 − R) × G₀ per Hubbard (2026V3). Source: 10.5281/zenodo.19468550 | 193 UN Member States."
    )
    fig.add_annotation(
        text=note,
        x=0.5,
        y=-0.035,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=8.5, color="#444444"),
        align="center",
        bordercolor="rgba(200,200,200,0.4)",
        borderwidth=0.5,
        borderpad=3,
        bgcolor="rgba(255,255,255,0.85)",
    )

    # Small footer credit line (right side, subtle)
    fig.add_annotation(
        text="RTLDI ATLAS 2026 — generated from exact equations in Causality and Attraction v3 (Hubbard)",
        x=0.99,
        y=0.005,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=7, color="#888888"),
        align="right",
    )

    return fig


def main():
    parser = argparse.ArgumentParser(description="Generate enclosure strength choropleth from RTLDI ATLAS data.")
    parser.add_argument("--year", type=int, default=2026, help="Atlas year label (default 2026)")
    parser.add_argument(
        "--input",
        default=None,
        help=f"Path to rtl_di_atlas_un_members_*.csv (default: {DEFAULT_ATLAS_CSV})",
    )
    parser.add_argument(
        "--out-dir", default=str(OUT_DIR), help="Directory for map outputs (default outputs/figures)"
    )
    args = parser.parse_args()

    df = load_atlas_for_map(args.input)

    # Sanity
    n = len(df)
    r_min, r_max = float(df["r"].min()), float(df["r"].max())
    print(f"Countries with R: {n} | R range: [{r_min:.3f}, {r_max:.3f}]")
    if n < 190:
        print("WARNING: fewer than ~193 rows — some countries may be missing iso3 or r values.")

    fig = make_choropleth(df, atlas_year=args.year)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = f"rtl_di_enclosure_strength_{args.year}_choropleth"

    # Interactive (great for exploration; hover shows full per-country impact + vintage)
    html_path = out_dir / f"{stem}.html"
    fig.write_html(html_path, include_plotlyjs="cdn")
    print(f"Saved interactive: {html_path}")

    # Static PNG (high-res for print, reports, ebook embedding)
    png_path = out_dir / f"{stem}.png"
    fig.write_image(png_path, width=1380, height=820, scale=2)
    print(f"Saved PNG (scale=2): {png_path}  ({png_path.stat().st_size / 1024:.0f} KB)")

    # Vector PDF (high-quality for print docs, reports, and embedding)
    pdf_path = out_dir / f"{stem}.pdf"
    fig.write_image(pdf_path, width=1380, height=820)
    print(f"Saved PDF: {pdf_path}  ({pdf_path.stat().st_size / 1024:.0f} KB)")

    print("\nDone. Enclosure strength = RTLP R (higher = stronger protection allowing capital to operate without exclusion).")
    print("To re-run with fresh data: python -m src.build_atlas --year 2026 && python -m src.generate_enclosure_map")


if __name__ == "__main__":
    main()

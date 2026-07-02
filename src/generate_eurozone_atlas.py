#!/usr/bin/env python3
"""Generate the RTLDI 2026 Eurozone Capital Exclusion Map.

This is a focused derivative of the 2026 UN member-state atlas. It keeps the
same print information design, equation, component crosswalk, R scale, and
country profile layout, but scopes every summary to the 21 euro-area member
states as of 2026.

Run:
  python -m src.generate_eurozone_atlas

Outputs:
  outputs/atlas/rtl_di_atlas_eurozone_2026.csv
  outputs/atlas/rtl_di_atlas_eurozone_summary_2026.json
  outputs/atlas/RTLDI_EUROZONE_CAPITAL_EXCLUSION_MAP_2026.pdf
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from fpdf.enums import XPos, YPos

from .generate_atlas_ebook import (
    ACCENT_COLOR,
    BLACK,
    CONTENT_WIDTH,
    FONT_NAME,
    HEADER_COLOR,
    INK,
    MARGIN,
    MUTED,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    PANEL_ALT,
    PANEL_BG,
    RULE,
    YES_COLOR,
    NO_COLOR,
    RTLDIAtlasPDF,
    ETA,
    _bounded_drag,
    format_money,
    get_nation_country_map,
    load_g0_series,
    load_iso2_lookup,
)
from .map_geometry import (
    add_metropolitan_france_trace,
    apply_european_france_bounds,
    split_france_for_metropolitan_display,
)

try:
    import plotly.express as px

    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False


EUROZONE_MEMBERS_2026 = [
    ("AUT", "Austria"),
    ("BEL", "Belgium"),
    ("BGR", "Bulgaria"),
    ("HRV", "Croatia"),
    ("CYP", "Cyprus"),
    ("EST", "Estonia"),
    ("FIN", "Finland"),
    ("FRA", "France"),
    ("DEU", "Germany"),
    ("GRC", "Greece"),
    ("IRL", "Ireland"),
    ("ITA", "Italy"),
    ("LVA", "Latvia"),
    ("LTU", "Lithuania"),
    ("LUX", "Luxembourg"),
    ("MLT", "Malta"),
    ("NLD", "Netherlands"),
    ("PRT", "Portugal"),
    ("SVK", "Slovakia"),
    ("SVN", "Slovenia"),
    ("ESP", "Spain"),
]
EUROZONE_ISOS = {iso for iso, _ in EUROZONE_MEMBERS_2026}

OUT_PDF = Path("outputs/atlas/RTLDI_EUROZONE_CAPITAL_EXCLUSION_MAP_2026.pdf")
OUT_CSV = Path("outputs/atlas/rtl_di_atlas_eurozone_2026.csv")
OUT_SUMMARY = Path("outputs/atlas/rtl_di_atlas_eurozone_summary_2026.json")


class EurozonePDF(RTLDIAtlasPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_y(7)
            self.set_font(FONT_NAME, "", 7.5)
            self.set_text_color(*MUTED)
            self.cell(0, 4, "RTLDI EUROZONE CAPITAL EXCLUSION MAP 2026", align="L")
            self.set_x(MARGIN)
            self.cell(0, 4, "Right to Life Deficit Index | Euro area member states", align="R")
            self.set_draw_color(*RULE)
            self.line(MARGIN, 13, PAGE_WIDTH - MARGIN, 13)
            self.ln(7)

    def footer(self):
        self.set_y(-12)
        self.set_font(FONT_NAME, "", 8)
        self.set_text_color(*MUTED)
        self.cell(
            0,
            10,
            f"Page {self.page_no()} | RTLDI 2026 | V-Dem 2024 + World Bank 2026 baseline",
            align="C",
        )


def _canonical_eta_note(rows: list[dict]) -> dict:
    """Return the canonical global eta metadata used by the UN atlas."""
    return {
        "eta": ETA,
        "n": len(rows),
        "intercept": None,
        "slope_per_lever_log": None,
        "slope_full_r_log": None,
        "weighted_r_squared": None,
        "note": "Canonical global UN-atlas eta; no Eurozone-scoped eta recalculation is used in this report.",
    }


def _load_eurozone_rows() -> tuple[list[dict], dict]:
    with open("data/processed/rtl_di_nation_breakdown_2026.json") as f:
        all_rows = json.load(f)
    rows = [d for d in all_rows if d.get("iso3") in EUROZONE_ISOS]
    found = {d["iso3"] for d in rows}
    missing = sorted(EUROZONE_ISOS - found)
    if missing:
        raise RuntimeError(f"Missing Eurozone countries in RTLDI processed data: {', '.join(missing)}")

    regression = _canonical_eta_note(rows)
    eta = regression["eta"]

    for d in rows:
        g0 = float(d.get("g0") or 0)
        r = float(d.get("r") or 0)
        pop = float(d.get("population") or 0)
        raw_dg = eta * (1.0 - r) * g0 if g0 > 0 else 0.0
        capped_dg = _bounded_drag(g0, r, eta=eta)
        raw_total = raw_dg * pop if pop > 0 else 0.0
        capped_total = capped_dg * pop if pop > 0 else 0.0
        d["raw_delta_g_per_capita"] = raw_dg
        d["delta_g_per_capita"] = capped_dg
        d["raw_total_deficit_usd"] = raw_total
        d["total_deficit_usd"] = capped_total
        d["cap_ratio"] = (capped_total / raw_total) if raw_total > 0 else 1.0
        d["capped"] = capped_total < raw_total - 1e-6
        d["eta"] = eta

    rows_by_loss = sorted(rows, key=lambda x: x.get("total_deficit_usd") or 0, reverse=True)
    for rank, d in enumerate(rows_by_loss, start=1):
        d["eurozone_rank_by_total_deficit"] = rank
    return rows, regression


def _aggregate(rows: list[dict], regression: dict) -> dict:
    total_pop = sum(float(d.get("population") or 0) for d in rows)
    total_lost = sum(float(d.get("total_deficit_usd") or 0) for d in rows)
    weighted_r = (
        sum(float(d.get("r") or 0) * float(d.get("population") or 0) for d in rows) / total_pop
        if total_pop > 0
        else 0.0
    )
    mean_r = sum(float(d.get("r") or 0) for d in rows) / len(rows)
    mean_g0 = sum(float(d.get("g0") or 0) for d in rows) / len(rows)

    indicators = []
    if rows and rows[0].get("components"):
        for i in range(9):
            comps = [d["components"][i] for d in rows if len(d.get("components", [])) > i]
            bins = [int(c.get("bin", 0)) for c in comps]
            raws = []
            for c in comps:
                raw = c.get("raw")
                if raw is not None:
                    try:
                        raws.append(float(raw))
                    except (TypeError, ValueError):
                        pass
            attr_lost = 0.0
            for d in rows:
                if len(d.get("components", [])) > i and int(d["components"][i].get("bin", 0)) == 0:
                    g0 = float(d.get("g0") or 0)
                    pop = float(d.get("population") or 0)
                    attr_lost += regression["eta"] * (1.0 / 9.0) * g0 * pop * float(d.get("cap_ratio", 1.0))
            indicators.append(
                {
                    "num": i + 1,
                    "name": comps[0].get("name", f"Indicator {i + 1}") if comps else f"Indicator {i + 1}",
                    "desc": comps[0].get("desc", "") if comps else "",
                    "frac_yes": sum(bins) / len(bins) if bins else 0,
                    "n_yes": sum(bins),
                    "n_countries": len(bins),
                    "avg_raw": sum(raws) / len(raws) if raws else 0,
                    "attributable_lost_gdp": attr_lost,
                }
            )

    return {
        "n_countries": len(rows),
        "total_pop": total_pop,
        "total_lost_gdp": total_lost,
        "weighted_r": weighted_r,
        "mean_r": mean_r,
        "mean_g0": mean_g0,
        "indicators": indicators,
        "members": rows,
        "eta": regression["eta"],
        "regression": regression,
    }


def _save_tables(rows: list[dict], summary: dict) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows_by_loss = sorted(rows, key=lambda x: x.get("total_deficit_usd") or 0, reverse=True)
    table = pd.DataFrame(
        [
            {
                "eurozone_rank_by_total_deficit": d.get("eurozone_rank_by_total_deficit"),
                "iso3": d.get("iso3"),
                "country": d.get("country"),
                "un_region": d.get("un_region"),
                "r": d.get("r"),
                "g0": d.get("g0"),
                "g0_year": d.get("g0_year"),
                "vdem_year": d.get("vdem_year"),
                "delta_g_per_capita": d.get("delta_g_per_capita"),
                "population": d.get("population"),
                "total_deficit_usd": d.get("total_deficit_usd"),
                "eta": d.get("eta"),
            }
            for d in rows_by_loss
        ]
    )
    table.to_csv(OUT_CSV, index=False)
    OUT_SUMMARY.write_text(
        json.dumps(
            {
                "atlas_year": 2026,
                "scope": "Eurozone member states",
                "n_countries": summary["n_countries"],
                "total_population": summary["total_pop"],
                "weighted_r": summary["weighted_r"],
                "mean_r": summary["mean_r"],
                "mean_g0": summary["mean_g0"],
                "eta": summary["eta"],
                "regression": summary["regression"],
                "total_eurozone_capital_exclusions_usd": summary["total_lost_gdp"],
                "membership_note": "21 euro-area member states as of 2026, including Bulgaria from 2026-01-01; excludes non-EU microstates using the euro by monetary agreement.",
            },
            indent=2,
        )
    )


def _get_eurozone_map(rows: list[dict]) -> Optional[Path]:
    if not HAS_PLOTLY:
        return _get_eurozone_point_map(rows)
    out = Path("outputs/figures/eurozone_choropleth_2026.png")
    fallback = Path("outputs/figures/eurozone_capital_exclusion_point_map_2026.png")
    if fallback.exists():
        return _get_eurozone_point_map(rows)
    df = pd.DataFrame(
        [{"iso3": d["iso3"], "country": d["country"], "r": float(d.get("r") or 0)} for d in rows]
    )
    map_df, france = split_france_for_metropolitan_display(df)
    fig = px.choropleth(
        map_df,
        locations="iso3",
        locationmode="ISO-3",
        color="r",
        color_continuous_scale="Viridis",
        range_color=[0.0, 1.0],
        hover_name="country",
        hover_data={"r": ":.3f"},
    )
    add_metropolitan_france_trace(fig, france)
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="rgba(180,180,180,0.7)",
        showland=True,
        landcolor="rgba(245,245,245,0.95)",
        showocean=True,
        oceancolor="rgba(230,242,255,0.65)",
        projection_type="mollweide",
    )
    apply_european_france_bounds(fig, kind="eurozone")
    fig.update_layout(
        coloraxis_colorbar=dict(title=dict(text="R", font=dict(size=7)), len=0.45, thickness=7),
        title=dict(text="Eurozone member states - Enclosure Strength (R)", font=dict(size=10)),
        margin=dict(l=1, r=1, t=18, b=1),
        height=260,
        width=520,
        paper_bgcolor="white",
    )
    try:
        fig.write_image(out, width=520, height=260, scale=1.5)
    except Exception as e:
        print(f"Eurozone choropleth render failed ({e}); using Matplotlib point-map fallback.")
        return _get_eurozone_point_map(rows)
    return out


def _get_eurozone_point_map(rows: list[dict]) -> Optional[Path]:
    """Offline fallback map when Plotly/Kaleido cannot export country polygons."""
    out = Path("outputs/figures/eurozone_capital_exclusion_point_map_2026.png")
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        print(f"Matplotlib fallback map unavailable ({e}).")
        return None

    coords = {
        "AUT": (14.6, 47.6),
        "BEL": (4.5, 50.7),
        "BGR": (25.5, 42.7),
        "HRV": (16.4, 45.1),
        "CYP": (33.0, 35.0),
        "EST": (25.0, 58.7),
        "FIN": (26.0, 64.5),
        "FRA": (2.2, 46.2),
        "DEU": (10.4, 51.2),
        "GRC": (22.0, 39.0),
        "IRL": (-8.0, 53.3),
        "ITA": (12.6, 42.7),
        "LVA": (24.6, 56.9),
        "LTU": (23.9, 55.2),
        "LUX": (6.1, 49.8),
        "MLT": (14.4, 35.9),
        "NLD": (5.3, 52.2),
        "PRT": (-8.2, 39.6),
        "SVK": (19.7, 48.7),
        "SVN": (14.9, 46.1),
        "ESP": (-3.7, 40.4),
    }
    ordered = [d for d in rows if d["iso3"] in coords]
    if not ordered:
        return None

    xs = [coords[d["iso3"]][0] for d in ordered]
    ys = [coords[d["iso3"]][1] for d in ordered]
    rs = [float(d.get("r") or 0) for d in ordered]
    losses = np.array([float(d.get("total_deficit_usd") or 0) for d in ordered])
    max_loss = float(losses.max()) if len(losses) else 1.0
    sizes = 55 + 520 * np.sqrt(losses / max_loss)

    fig, ax = plt.subplots(figsize=(7.4, 3.7), dpi=160)
    ax.set_facecolor("#f7fafc")
    fig.patch.set_facecolor("white")
    ax.set_xlim(-12, 36)
    ax.set_ylim(33, 66.5)
    ax.grid(color="#d6dee5", linewidth=0.55)
    ax.set_xlabel("Longitude", fontsize=7, color="#5b6770")
    ax.set_ylabel("Latitude", fontsize=7, color="#5b6770")
    ax.tick_params(labelsize=6, colors="#5b6770")
    sc = ax.scatter(
        xs,
        ys,
        c=rs,
        s=sizes,
        cmap="viridis",
        vmin=0,
        vmax=1,
        edgecolors="#2f3b45",
        linewidths=0.7,
        alpha=0.94,
        zorder=3,
    )
    label_offsets = {
        "BEL": (0.5, 0.5),
        "NLD": (0.5, 0.55),
        "LUX": (0.6, -0.8),
        "DEU": (0.5, 0.4),
        "AUT": (0.5, -0.8),
        "SVN": (0.5, -0.75),
        "HRV": (0.6, -0.65),
        "MLT": (0.45, -0.75),
        "CYP": (-3.4, -0.65),
        "SVK": (0.55, 0.45),
        "LVA": (0.45, 0.5),
        "LTU": (0.45, -0.7),
        "EST": (0.5, 0.45),
    }
    for d, x, y in zip(ordered, xs, ys):
        dx, dy = label_offsets.get(d["iso3"], (0.45, 0.35))
        ax.text(x + dx, y + dy, d["iso3"], fontsize=6.3, color="#18202b", weight="bold", zorder=4)
    ax.set_title("Eurozone Capital Exclusion Map 2026", fontsize=10, color="#1f4e79", pad=7)
    cbar = fig.colorbar(sc, ax=ax, fraction=0.032, pad=0.018)
    cbar.set_label("RTLP R", fontsize=7)
    cbar.ax.tick_params(labelsize=6)
    ax.text(
        0.01,
        0.01,
        "Color = enclosure strength R; marker area = annual capital exclusions (capped).",
        transform=ax.transAxes,
        fontsize=6.5,
        color="#5b6770",
        va="bottom",
    )
    fig.tight_layout(pad=0.9)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def _format_trend_text(iso3: str, r: float, population: float, g0_by_year: dict, eta: float) -> str:
    points = []
    for year in (2023, 2024, 2025):
        g0 = g0_by_year.get(year)
        if g0 is None or pd.isna(g0) or r is None or population is None or population <= 0:
            continue
        dg = _bounded_drag(float(g0), float(r), eta=eta)
        points.append((year, dg, dg * float(population)))
    if not points:
        return "Three-year RTLDI projection: insufficient recent GDP data for a reliable 3-position text trend."
    pieces = [f"{year}: {format_money(total)} total capital exclusions (${dg:,.0f}/cap)" for year, dg, total in points]
    if len(points) >= 2:
        change = points[-1][2] - points[0][2]
        direction = "increase" if change > 0 else "decrease" if change < 0 else "no change"
        return (
            "Three-position RTLDI projection (R fixed at latest V-Dem value; canonical global eta fixed at "
            f"{eta:.2f}; G0 varies by year): "
            + "; ".join(pieces)
            + f". Net {direction} from {points[0][0]} to {points[-1][0]}: {format_money(abs(change))}."
        )
    return "Three-position RTLDI projection (partial data): " + "; ".join(pieces) + "."


def _write_summary_table(pdf: EurozonePDF, rows_by_loss: list[dict]) -> None:
    pdf.section_label("Eurozone member states sorted by capital exclusions", HEADER_COLOR)
    pdf.ln(0.5)
    col_widths = [8, 38, 18, 22, 28, 30, 28]
    headers = ["#", "Country", "R", "G0", "Per Capita Excl.", "Capital Exclusions", "Population"]
    pdf.set_font(FONT_NAME, "", 7)
    pdf.set_fill_color(*HEADER_COLOR)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 5, h, border=1, fill=True, align="C")
    pdf.ln()
    for idx, d in enumerate(rows_by_loss):
        zebra = idx % 2 == 0
        pdf.set_fill_color(*PANEL_BG) if zebra else pdf.set_fill_color(255, 255, 255)
        r_val = d.get("r")
        if r_val is not None and r_val >= 0.6:
            pdf.set_text_color(*YES_COLOR)
        elif r_val is not None and r_val <= 0.2:
            pdf.set_text_color(*NO_COLOR)
        else:
            pdf.set_text_color(*BLACK)
        pdf.set_font(FONT_NAME, "", 6.5)
        pdf.cell(col_widths[0], 4.3, str(d["eurozone_rank_by_total_deficit"]), border=1, align="C", fill=zebra)
        pdf.cell(col_widths[1], 4.3, d["country"][:28], border=1, fill=zebra)
        pdf.cell(col_widths[2], 4.3, f"{d.get('r', 0):.2f}", border=1, align="C", fill=zebra)
        pdf.set_text_color(*BLACK)
        pdf.cell(col_widths[3], 4.3, f"${float(d.get('g0') or 0):,.0f}", border=1, align="R", fill=zebra)
        pdf.cell(col_widths[4], 4.3, f"${float(d.get('delta_g_per_capita') or 0):,.0f}", border=1, align="R", fill=zebra)
        pdf.cell(
            col_widths[5],
            4.3,
            format_money(float(d.get("total_deficit_usd") or 0)),
            border=1,
            align="R",
            fill=zebra,
        )
        pop = float(d.get("population") or 0)
        pdf.cell(
            col_widths[6],
            4.3,
            f"{pop/1e6:,.1f}m",
            border=1,
            align="R",
            fill=zebra,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )


def _build_pdf(rows: list[dict], summary: dict) -> Path:
    pdf = EurozonePDF()
    rows_by_loss = sorted(rows, key=lambda x: x.get("total_deficit_usd") or 0, reverse=True)
    rows_alpha = sorted(rows, key=lambda x: x["country"])

    pdf.add_page()
    pdf.set_fill_color(247, 250, 252)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, style="F")
    pdf.set_fill_color(*HEADER_COLOR)
    pdf.rect(0, 0, 18, PAGE_HEIGHT, style="F")
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.rect(18, 0, 4, PAGE_HEIGHT, style="F")
    pdf.set_y(38)
    pdf.set_x(34)
    pdf.set_font(FONT_NAME, "", 27)
    pdf.set_text_color(*INK)
    pdf.multi_cell(150, 11, "RTLDI 2026 Eurozone Capital Exclusion Map")
    pdf.set_x(34)
    pdf.set_font(FONT_NAME, "", 14)
    pdf.set_text_color(*HEADER_COLOR)
    pdf.cell(0, 8, "Right to Life Deficit Index for the 21 euro-area member states", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(34)
    pdf.set_font(FONT_NAME, "", 10.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(145, 5.2, "Identifying capital exclusions: lost potential GDP associated with missing foundational protections. Same RTLDI information design and canonical global eta as the UN member-state atlas, scoped to the Eurozone.")
    card_y = 112
    card_w = 42
    gap = 5
    pdf.metric_card(34, card_y, card_w, 28, "Eurozone exclusions", format_money(summary["total_lost_gdp"]), "annual, capped", PANEL_ALT)
    pdf.metric_card(34 + card_w + gap, card_y, card_w, 28, "Member states", "21", "euro area")
    pdf.metric_card(34 + (card_w + gap) * 2, card_y, card_w, 28, "Coefficient eta", f"{summary['eta']:.2f}", "global canonical")
    pdf.set_xy(34, 159)
    pdf.set_font(FONT_NAME, "", 8.8)
    pdf.set_text_color(*INK)
    pdf.multi_cell(142, 4.8, "Scope: euro-area member states as of 2026, including Bulgaria from January 1, 2026. Non-EU microstates using the euro by monetary agreement are excluded from this member-state map.")

    pdf.add_page()
    pdf.chapter_title("Executive Description")
    pdf.body_text(
        "This focused atlas applies the RTLDI 2026 model to the Eurozone. It uses the same nine-protection RTLP score, V-Dem 2024 component crosswalk, World Bank GDP baseline, population weighting, canonical global eta, and 25% contextual cap used in the UN member-state atlas.\n\n"
        f"Across the 21 euro-area member states, the bounded model identifies {format_money(summary['total_lost_gdp'])} in annual capital exclusions. These are measured as lost potential GDP associated with missing or incomplete foundational protections necessary for capital to operate safely."
    )
    pdf.body_text(
        "The map is not a judgment on Eurozone members. It is an economic intelligence view: which levers are not yet fully activated, where the largest excluded-capital volumes sit, and how each member state's current RTLP profile compares inside the shared currency area."
    )

    pdf.add_page()
    pdf.chapter_title("Methodology and Data Sources")
    pdf.body_text(
        "R is the simple average of nine binary indicators. Eight are derived from V-Dem v15 using the same thresholds as the UN atlas; the ninth uses World Bank undernourishment and poverty data. This Eurozone report intentionally does not recalculate eta on the smaller regional sample. It uses the canonical global UN-atlas coefficient so the Eurozone figures are directly comparable to the main atlas.\n\n"
        f"The canonical coefficient is eta = {summary['eta']:.2f}. The economic projection is therefore:\n\n"
        f"Delta G per capita = min({summary['eta']:.2f} x (1 - R) x G0, 0.25 x G0).\n\n"
        "Total capital exclusions = Delta G per capita x population. G0 is the most recent published World Bank GDP per capita value used in the 2026 atlas baseline. V-Dem components reflect 2024 data, the latest source year available in this pipeline."
    )
    pdf.small_text("Full crosswalk: docs/indicator_crosswalk.md. Source framework: Hubbard, Causality and Attraction v3, DOI 10.5281/zenodo.19468550.")

    pdf.add_page()
    pdf.chapter_title("Cartographic Approach and Eurozone Summary")
    map_path = _get_eurozone_map(rows)
    y0 = pdf.get_y()
    if map_path and map_path.exists():
        map_w = 100
        map_h = 50
        pdf.image(str(map_path), x=PAGE_WIDTH - MARGIN - map_w, y=y0, w=map_w, h=map_h)
        is_point_map = "point_map" in map_path.name
        pdf.set_xy(MARGIN, y0)
        pdf.set_font(FONT_NAME, "", 9)
        pdf.set_text_color(*INK)
        map_text = (
            "The Eurozone point map keeps the same Viridis 0-1 R scale as the UN atlas and adds marker area for annual capital exclusions. The subset view makes the shared-currency area visible as a capital-exclusion diagnostic without changing the underlying score design."
            if is_point_map
            else "The Eurozone choropleth uses the same Mollweide equal-area projection and Viridis 0-1 R scale as the UN atlas. The subset map makes the shared-currency area visible as a capital-exclusion diagnostic without changing the underlying score design."
        )
        pdf.multi_cell(CONTENT_WIDTH - map_w - 6, 4.2, map_text)
        pdf.set_y(y0 + map_h + 4)
    else:
        pdf.small_text("[Eurozone map could not be embedded; table and profile data remain available.]")
    metric_y = pdf.get_y()
    metric_w = (CONTENT_WIDTH - 9) / 4
    pdf.metric_card(MARGIN, metric_y, metric_w, 22, "Countries", str(summary["n_countries"]))
    pdf.metric_card(MARGIN + metric_w + 3, metric_y, metric_w, 22, "Population", f"{summary['total_pop']/1e6:,.1f}m")
    pdf.metric_card(MARGIN + (metric_w + 3) * 2, metric_y, metric_w, 22, "Weighted R", f"{summary['weighted_r']:.2f}", fill=PANEL_ALT)
    pdf.metric_card(MARGIN + (metric_w + 3) * 3, metric_y, metric_w, 22, "Eta / exclusions", f"{summary['eta']:.3f}", format_money(summary["total_lost_gdp"]))
    pdf.set_y(metric_y + 26)

    pdf.section_label("Capital exclusions by RTLP lever", HEADER_COLOR)
    tcols = [7, 69, 34, 16]
    headers = ["#", "Indicator", "Annual Exclusions", "% total"]
    pdf.set_font(FONT_NAME, "", 7.2)
    pdf.set_fill_color(*HEADER_COLOR)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(tcols[i], 4.2, h, border=1, fill=True, align="C" if i != 1 else "L")
    pdf.ln()
    for rank, ind in enumerate(sorted(summary["indicators"], key=lambda x: x["attributable_lost_gdp"], reverse=True)):
        zebra = rank % 2 == 0
        pdf.set_fill_color(*PANEL_BG) if zebra else pdf.set_fill_color(255, 255, 255)
        lost = ind["attributable_lost_gdp"]
        pct = lost / summary["total_lost_gdp"] * 100 if summary["total_lost_gdp"] else 0
        pdf.set_font(FONT_NAME, "", 7.2)
        pdf.set_text_color(*BLACK)
        pdf.cell(tcols[0], 4, str(ind["num"]), border=1, align="C", fill=zebra)
        pdf.cell(tcols[1], 4, ind["name"][:40], border=1, fill=zebra)
        pdf.cell(tcols[2], 4, format_money(lost), border=1, align="R", fill=zebra)
        pdf.cell(tcols[3], 4, f"{pct:.1f}%", border=1, align="C", fill=zebra, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    _write_summary_table(pdf, rows_by_loss)

    pdf.add_page()
    pdf.chapter_title("Eurozone Member-State Profiles")
    pdf.small_text("Detailed profiles are ordered alphabetically by country name. The layout, metrics, trend text, country map, and RTLP component breakdown mirror the UN member-state atlas.")

    g0_series = load_g0_series([d["iso3"] for d in rows])
    iso2_lookup = load_iso2_lookup()
    for d in rows_alpha:
        pdf.add_page()
        iso2 = iso2_lookup.get(d["iso3"], "")
        yes_count = sum(c["bin"] for c in d["components"])
        pdf.section_label("Eurozone member-state profile", HEADER_COLOR)
        pdf.set_font(FONT_NAME, "", 16)
        pdf.set_text_color(*INK)
        pdf.cell(0, 7, f"{d['country']} ({d['iso3']})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font(FONT_NAME, "", 9)
        pdf.set_text_color(*MUTED)
        flag_text = f" | Flag code: {iso2}" if iso2 else ""
        pdf.multi_cell(
            0,
            5,
            f"UN Region: {d.get('un_region', 'N/A')} | Eurozone rank: {d['eurozone_rank_by_total_deficit']} | RTLP R = {d['r']:.3f} ({yes_count}/9) | V-Dem year: {d['vdem_year']} | G0 year: {d['g0_year']}{flag_text}",
        )
        pdf.ln(2)
        pop = float(d.get("population") or 0)
        pop_str = f"{pop/1e6:,.1f} million" if pop >= 100000 else f"{pop:,.0f}"
        metric_y = pdf.get_y()
        metric_w = (CONTENT_WIDTH - 9) / 4
        pdf.metric_card(MARGIN, metric_y, metric_w, 22, "GDP per capita G0", f"${float(d.get('g0') or 0):,.0f}")
        pdf.metric_card(MARGIN + metric_w + 3, metric_y, metric_w, 22, "Capital exclusions / cap", f"${float(d.get('delta_g_per_capita') or 0):,.0f}", fill=PANEL_ALT)
        pdf.metric_card(MARGIN + (metric_w + 3) * 2, metric_y, metric_w, 22, "Annual total", format_money(float(d.get("total_deficit_usd") or 0)))
        pdf.metric_card(MARGIN + (metric_w + 3) * 3, metric_y, metric_w, 22, "Population", pop_str)
        pdf.set_y(metric_y + 25)
        trend_y = pdf.get_y()
        pdf.set_fill_color(*PANEL_BG)
        pdf.set_draw_color(*RULE)
        pdf.rect(MARGIN, trend_y, CONTENT_WIDTH, 16, style="DF")
        pdf.set_xy(MARGIN + 2.5, trend_y + 2)
        pdf.set_font(FONT_NAME, "", 6.8)
        pdf.set_text_color(*INK)
        pdf.multi_cell(CONTENT_WIDTH - 5, 3.1, _format_trend_text(d["iso3"], d.get("r"), d.get("population"), g0_series.get(d["iso3"], {}), summary["eta"]))
        pdf.set_y(trend_y + 18)

        country_map = get_nation_country_map(d["iso3"], d["country"], d.get("r"))
        if country_map and country_map.exists():
            pdf.set_font(FONT_NAME, "", 6.8)
            pdf.set_text_color(*HEADER_COLOR)
            pdf.cell(0, 3.2, "Country View - Enclosure Strength (R)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            y_map = pdf.get_y()
            map_w = CONTENT_WIDTH - 60
            map_h = map_w * (180 / 380)
            pdf.image(str(country_map), x=MARGIN + 30, y=y_map, w=map_w, h=map_h)
            pdf.set_y(y_map + map_h + 1)
            pdf.set_font(FONT_NAME, "", 5)
            pdf.set_text_color(95, 95, 95)
            pdf.multi_cell(0, 2.1, "Country-only local view fitted to the national boundary; no regional comparison map is used on member-state pages.")
            pdf.ln(0.3)

        pdf.section_label("RTLP score breakdown - 9 indicators", HEADER_COLOR)
        for c in d["components"]:
            yes = c["yes"]
            pdf.set_font(FONT_NAME, "", 6.5)
            pdf.set_text_color(*(YES_COLOR if yes == "Yes" else NO_COLOR))
            pdf.cell(0, 3.1, f"{c['num']}. {c['name']} [{yes}]", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font(FONT_NAME, "", 5.5)
            pdf.set_text_color(80, 80, 80)
            pdf.set_x(MARGIN + 3)
            raw_str = str(c["raw"])[:50] if c.get("raw") is not None else "N/A"
            pdf.multi_cell(0, 2.6, f"raw: {raw_str} - {c['desc']}")
            pdf.set_x(MARGIN)
        pdf.set_font(FONT_NAME, "", 5.5)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 2.8, "Note: [Yes] contributes +1 to R. Thresholds and component meanings are identical to the UN member-state atlas.")

    pdf.add_page()
    pdf.chapter_title("Data Attribution and Sources")
    pdf.body_text(
        "Primary data: V-Dem Country-Year Full+Others v15, World Bank World Development Indicators, and the existing RTLDI 2026 processed member-state table. Scope is the 21 euro-area member states as of 2026.\n\n"
        f"Source framework: Sid J.A. Hubbard, Causality and Attraction: A Continuum of Steady States (Version 3, May 2026), DOI 10.5281/zenodo.19468550. The Eurozone atlas is a scoped derivative: it does not change the RTLDI equation, thresholds, component crosswalk, canonical global eta, or 25% contextual cap. This report uses eta={summary['eta']:.2f}."
    )
    pdf.body_text(
        "Membership note: Bulgaria is included because it adopted the euro on January 1, 2026. The scope excludes Andorra, Monaco, San Marino, Vatican City, Kosovo, and Montenegro because they are not Eurozone member states, even where the euro is used."
    )

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(OUT_PDF)
    print(f"Eurozone PDF written to: {OUT_PDF} ({pdf.page_no()} pages)")
    return OUT_PDF


def main() -> int:
    rows, regression = _load_eurozone_rows()
    summary = _aggregate(rows, regression)
    _save_tables(rows, summary)
    out = _build_pdf(rows, summary)
    print(f"CSV written to: {OUT_CSV}")
    print(f"Summary written to: {OUT_SUMMARY}")
    print(f"Done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

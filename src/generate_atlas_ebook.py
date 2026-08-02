#!/usr/bin/env python3
"""
Generate a print-ready PDF ebook for the RTLDI ATLAS 2026 (modular parts + concatenated release).
RTLDI = Right to Life Deficit Index (source: Zenodo 10.5281/zenodo.19468550). Extended via population-weighted regression (25% cap) to estimate capital exclusions associated with missing protections.

Structure (five separately-generated parts for fast iteration; no duplicated nation generation):
  FRONT MATTER
  - Cover, publication record, About, authorship, production disclosure, and contents
  - Executive description, methodology, causal projection, reader guide, and limitations
  - Global choropleth, global capital exclusions by nine levers, and 193-country summary
  - Full-page Web Atlas gateway before regional summaries

  REGIONS (22 UN regional summary pages)
  - One page per region: choropleth, aggregates, two-para cumulative description,
    member-nations table with REGIONAL TOTAL, 9-lever breakdown + opportunity callout if applicable

  NATIONS (individual country pages — the 193-page section)
  - Detailed profiles: one page per nation (A-Z order), with capital exclusions figures + full 9-lever
    RTLDI breakdown + three-year RTLDI trend stated in text + country-only map

  EUROZONE FOCUS
  - Cover, executive description, methods, Web Atlas gateway, map, 21 profiles, and sources

  BACK MATTER
  - Executable crosswalk, regression evidence, datasets, attribution, citation, and licensing
  - Full-page source-code and data gateway
  - Expanded glossary, credits, acknowledgments, and print colophon

Usage (recommended for fast iteration):
  python -m src.generate_atlas_ebook                 # build all four parts + concatenate release
  python -m src.generate_atlas_ebook --front         # only front matter (title through 193 summary table)
  python -m src.generate_atlas_ebook --regions       # only the 22 region summary pages
  python -m src.generate_atlas_ebook --nations       # only the 193 nation pages (heavy; rare)
  python -m src.generate_atlas_ebook --back          # only attribution/index/credits
  python -m src.generate_atlas_ebook --concat-only   # combine existing parts (front+regions+nations+back) into release (final step)

Outputs (always the most current of each):
  outputs/atlas/RTLDI_ATLAS_2026_front.pdf
  outputs/atlas/RTLDI_ATLAS_2026_regions.pdf
  outputs/atlas/RTLDI_ATLAS_2026_nations.pdf
  outputs/atlas/RTLDI_ATLAS_2026_back.pdf
  outputs/atlas/RTLDI_ATLAS_2026_ebook.pdf   # concatenated release (front + regions + nations + back)

The final step before tagging a GitHub release is the concatenation of the five modular parts.
This split prevents re-generating heavy sections when iterating on front matter or regions.
"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos
import json
from pathlib import Path
import math
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List
import argparse
import subprocess
import sys
from src.lever_display import LEVER_DISPLAY, format_compact_usd, lever_description, lever_name, lever_short
from src.atlas_evidence import (
    LEVER_CROSSWALK,
    VDEM_ARCHIVE_URL,
    VDEM_CODEBOOK_URL,
    VDEM_DATASET_URL,
    VDEM_V15_SHA256,
    VDEM_V15_SOURCE_URL,
    WORLD_BANK_API_URL,
    WORLD_BANK_DATA_URL,
    evidence_bundle,
)
from src.map_geometry import (
    RTLDI_COLOR_SCALE,
    add_small_country_markers,
    add_metropolitan_france_trace,
    apply_atlas_choropleth_style,
    apply_atlas_geo_style,
    apply_european_france_bounds,
    split_france_for_metropolitan_display,
)
from src.print_access import (
    FULL_DATA_URL,
    INTERACTIVE_MAP_URL,
    REPOSITORY_URL,
    WEB_ATLAS_URL,
    draw_mini_link,
    draw_qr_gateway,
    draw_section_opener,
)

# PDF concatenation (PyPDF2 is already available in the env; pypdf is a modern alternative)
try:
    from PyPDF2 import PdfReader, PdfWriter
    HAS_PYPDF = True
except Exception:
    HAS_PYPDF = False

try:
    import plotly.express as px
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False

# Page setup (A4 for print ebook, good margins)
PAGE_WIDTH = 210
PAGE_HEIGHT = 297
MARGIN = 15  # mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

# Font (Unicode capable on macOS)
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
FONT_NAME = "ArialUnicode"

# Colors
HEADER_COLOR = (31, 78, 121)  # dark blue
ACCENT_COLOR = (16, 126, 101)
INK = (24, 32, 43)
MUTED = (91, 103, 112)
RULE = (198, 209, 218)
PANEL_BG = (247, 250, 252)
PANEL_ALT = (235, 244, 241)
YES_COLOR = (0, 128, 0)
NO_COLOR = (180, 0, 0)
LIGHT_GRAY = (240, 240, 240)
BLACK = (0, 0, 0)

# Current model parameters (keep in sync with src/rtl_di.py)
# eta from population-weighted cross-section; cap from the "Contextual Bounding" template
# (study of archetypal nations to limit claims to what is plausible once industry/locale/history are credited).
ETA = 0.36
MAX_INSTITUTIONAL_SHARE = 0.25

# Modular PDF part filenames (outputs/atlas always holds the most current of each)
FRONT_PDF = "outputs/atlas/RTLDI_ATLAS_2026_front.pdf"
REGIONS_PDF = "outputs/atlas/RTLDI_ATLAS_2026_regions.pdf"
NATIONS_PDF = "outputs/atlas/RTLDI_ATLAS_2026_nations.pdf"
EUROZONE_PDF = "outputs/atlas/RTLDI_EUROZONE_CAPITAL_EXCLUSION_MAP_2026.pdf"


def _bounded_drag(g0: float, r: float, eta: float = ETA, cap: float = MAX_INSTITUTIONAL_SHARE) -> float:
    """Per-capita drag bounded by the contextual institutional share cap.
    Matches the logic in src/rtl_di.py compute_delta_g with the current defaults.
    """
    if g0 <= 0 or pd.isna(g0) or pd.isna(r):
        return 0.0
    raw = eta * (1.0 - float(r)) * float(g0)
    return min(raw, cap * float(g0))
BACK_PDF = "outputs/atlas/RTLDI_ATLAS_2026_back.pdf"
RELEASE_PDF = "outputs/atlas/RTLDI_ATLAS_2026_ebook.pdf"

class RTLDIAtlasPDF(FPDF):
    def __init__(self):
        super().__init__(format="A4", unit="mm")
        self.add_font(FONT_NAME, "", FONT_PATH)
        self.add_font(FONT_NAME, "B", FONT_PATH)  # reuse for bold, fpdf2 will fake or use same
        self.set_auto_page_break(auto=True, margin=MARGIN)
        self.page_count_for_toc = 0  # not used in v1
        self._suppress_next_header = False
        self._chromeless_pages: set[int] = set()
        self.set_title("RTLDI Atlas 2026: UN Member States")
        self.set_author("RTLDI Atlas Project; Sid J.A. Hubbard, Principal Investigator")
        self.set_subject("Right to Life Deficit Index, RTLP scores, capital exclusions, and nine-lever country profiles")
        self.set_keywords("RTLDI, RTLP, V-Dem, World Bank, capital exclusions, atlas")
        self.set_creator("RTLDI Atlas open-source publication pipeline")
        self.set_producer("fpdf2 and PyPDF2")

    def add_chromeless_page(self):
        self._suppress_next_header = True
        self.add_page()
        self._chromeless_pages.add(self.page_no())

    def header(self):
        if self._suppress_next_header:
            self._suppress_next_header = False
            return
        if self.page_no() > 1:
            self.set_y(7)
            self.set_font(FONT_NAME, "", 7.5)
            self.set_text_color(*MUTED)
            self.cell(0, 4, "RTLDI ATLAS 2026", align="L")
            self.set_x(MARGIN)
            self.cell(0, 4, "Right to Life Deficit Index | Capital Exclusions", align="R")
            self.set_draw_color(*RULE)
            self.line(MARGIN, 13, PAGE_WIDTH - MARGIN, 13)
            self.ln(7)

    def footer(self):
        # Continuous physical folios are applied once, after modular PDF assembly.
        return

    def chapter_title(self, title):
        self.set_font(FONT_NAME, "", 15)
        self.set_text_color(*INK)
        self.multi_cell(0, 7, title, align="L")
        self.set_draw_color(*ACCENT_COLOR)
        self.set_line_width(0.8)
        self.line(MARGIN, self.get_y() + 1, MARGIN + 32, self.get_y() + 1)
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(MARGIN + 34, self.get_y() + 1, PAGE_WIDTH - MARGIN, self.get_y() + 1)
        self.ln(6)

    def body_text(self, text, size=10):
        self.set_font(FONT_NAME, "", size)
        self.set_text_color(*INK)
        self.multi_cell(0, 5, text, align="L")
        self.ln(2)

    def small_text(self, text):
        self.set_font(FONT_NAME, "", 8)
        self.set_text_color(*MUTED)
        self.multi_cell(0, 4, text, align="L")
        self.ln(1)

    def section_label(self, text, color=ACCENT_COLOR):
        self.set_font(FONT_NAME, "", 7)
        self.set_text_color(*color)
        self.cell(0, 4, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def metric_card(self, x, y, w, h, label, value, note="", fill=PANEL_BG):
        self.set_fill_color(*fill)
        self.set_draw_color(*RULE)
        self.rect(x, y, w, h, style="DF")
        self.set_xy(x + 2.2, y + 2.2)
        self.set_font(FONT_NAME, "", 6.2)
        self.set_text_color(*MUTED)
        self.multi_cell(w - 4.4, 2.7, label.upper())
        self.set_xy(x + 2.2, y + 9)
        self.set_font(FONT_NAME, "", 13)
        self.set_text_color(*INK)
        self.cell(w - 4.4, 5, value)
        if note:
            self.set_xy(x + 2.2, y + h - 5)
            self.set_font(FONT_NAME, "", 5.8)
            self.set_text_color(*MUTED)
            self.cell(w - 4.4, 3, note)

def load_detailed_data():
    path = Path("data/processed/rtl_di_nation_breakdown_2026.json")
    with open(path) as f:
        data = json.load(f)
    # Sort alpha for profiles
    data_sorted = sorted(data, key=lambda x: x["country"])
    return data, data_sorted


def load_g0_series(iso3_list, years=(2023, 2024, 2025)):
    """Load up to 3 years of G0 (GDP per capita current US$) for the given ISO3s.
    Prefers local WB files used by the pipeline, then fills any gaps via wbgapi.
    Returns dict iso3 -> {year: g0_value or None}
    """
    iso3s = {i.upper() for i in iso3_list}
    g0s = {iso: {y: None for y in years} for iso in iso3s}
    bulk = Path("data/raw/wb_gdp/API_NY.GDP.PCAP.CD_DS2_en_csv_v2_46.csv")
    has_bulk_data = False
    if bulk.exists():
        try:
            df = pd.read_csv(bulk, skiprows=4)
            df["iso3"] = df["Country Code"].astype(str).str.upper()
            for y in years:
                col = str(y)
                if col in df.columns:
                    sub = df[df["iso3"].isin(iso3s)][["iso3", col]].dropna(subset=[col])
                    for _, r in sub.iterrows():
                        g0s[r["iso3"]][y] = float(r[col])
                    has_bulk_data = True
            if has_bulk_data:
                print("  Recent G0: loaded available years from local bulk")
        except Exception as e:
            print(f"  3yr G0 bulk load failed ({e}), trying wbgapi...")

    processed = Path("data/processed/wb_2023_2024_raw.csv")
    has_processed_data = False
    if processed.exists():
        try:
            df = pd.read_csv(processed)
            df = df[df["series"] == "NY.GDP.PCAP.CD"].copy()
            df["iso3"] = df["economy"].astype(str).str.upper()
            for y in years:
                col = str(y)
                if col in df.columns:
                    sub = df[df["iso3"].isin(iso3s)][["iso3", col]].dropna(subset=[col])
                    for _, r in sub.iterrows():
                        g0s[r["iso3"]][y] = float(r[col])
                    has_processed_data = True
            if has_processed_data:
                print("  Recent G0: loaded available years from canonical processed World Bank data")
        except Exception as e:
            print(f"  Processed G0 load failed ({e}), trying wbgapi...")

    # Fallback to live API (requires wbgapi; already used in core pipeline)
    try:
        import wbgapi as wb
        # numericTimeKeys for int years
        df = wb.data.DataFrame("NY.GDP.PCAP.CD", list(iso3s), time=list(years), labels=False, numericTimeKeys=True)
        df = df.reset_index().rename(columns={"index": "iso3"})
        df["iso3"] = df["iso3"].astype(str).str.upper()
        for y in years:
            if y in df.columns:
                sub = df[df["iso3"].isin(iso3s)][["iso3", y]].dropna(subset=[y])
                for _, r in sub.iterrows():
                    g0s[r["iso3"]][y] = float(r[y])
        print("  Recent G0: filled available years via wbgapi")
    except Exception as e:
        if has_bulk_data or has_processed_data:
            print(f"  Live G0 refresh unavailable ({e}); using canonical local years.")
        else:
            print(f"  Recent G0 wbgapi failed ({e}); trends will be missing for some nations.")
    return g0s


def load_iso2_lookup(path: str = "data/raw/un_member_states.csv") -> Dict[str, str]:
    """Map ISO3 -> ISO2 for flag labels in nation profiles."""
    try:
        df = pd.read_csv(path)
    except Exception:
        return {}
    out = {}
    for _, row in df.iterrows():
        iso3 = str(row.get("ISO3", "")).upper()
        iso2 = str(row.get("ISO2", "")).strip().upper()
        if iso3 and len(iso2) == 2 and iso2.isalpha():
            out[iso3] = iso2
    return out


def format_money(n: float) -> str:
    return format_compact_usd(n)


def format_trend_text(iso3: str, r: float, population: float, g0_by_year: dict,
                      years=(2023, 2024, 2025)) -> str:
    """Compact text replacement for the previous trend graphic."""
    points = []
    for y in years:
        g0 = g0_by_year.get(y)
        if g0 is None or (isinstance(g0, float) and np.isnan(g0)):
            continue
        if r is None or population is None or population <= 0:
            continue
        dg = _bounded_drag(float(g0), float(r))
        total = dg * float(population)
        points.append((int(y), float(g0), float(dg), float(total)))
    if not points:
        return "Recent RTLDI projection: insufficient GDP data for an up-to-three-year text trend."
    pieces = [f"{year}: {format_money(total)} total capital exclusions (${dg:,.0f}/cap)" for year, _, dg, total in points]
    if len(points) >= 2:
        start = points[0][3]
        end = points[-1][3]
        change = end - start
        direction = "increase" if change > 0 else "decrease" if change < 0 else "no change"
        return (
            "Recent RTLDI projection (up to three years; R fixed at latest V-Dem value; G0 varies by year): "
            + "; ".join(pieces)
            + f". Net {direction} from {points[0][0]} to {points[-1][0]}: {format_money(abs(change))}."
        )
    return "Recent RTLDI projection (partial data): " + "; ".join(pieces) + "."


def get_nation_country_map(iso3: str, country: str, r: float) -> Optional[Path]:
    """Generate a country-only local map for a nation profile.
    This intentionally does not include the rest of the UN region; it is a focused country view.
    """
    if not HAS_PLOTLY:
        return None
    out_dir = Path("outputs/figures/nation_country_maps")
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{iso3}_country.png"

    focus_df = pd.DataFrame([{"iso3": iso3, "r": float(r or 0.0), "country": country}])
    map_df, france = split_france_for_metropolitan_display(focus_df)

    fig = px.choropleth(
        map_df,
        locations="iso3",
        locationmode="ISO-3",
        color="r",
        color_continuous_scale=RTLDI_COLOR_SCALE,
        range_color=[0.0, 1.0],
        hover_name="country",
        hover_data={"r": ":.3f"},
    )
    apply_atlas_choropleth_style(fig)
    add_metropolitan_france_trace(fig, france)
    add_small_country_markers(fig, map_df, marker_size=7, show_text=True)
    apply_atlas_geo_style(fig, projection_type="natural earth", show_grid=False)

    if france:
        apply_european_france_bounds(fig, kind="france")
    else:
        fig.update_geos(
            fitbounds="locations",
        )

    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text="R", font=dict(size=7)),
            len=0.4,
            thickness=6,
        ),
        title=dict(text=f"{country} — country-only view (R={float(r or 0.0):.2f})", font=dict(size=8)),
        margin=dict(l=1, r=1, t=16, b=4),
        height=180,
        width=380,
        paper_bgcolor="white",
    )

    fig.write_image(p, width=380, height=180, scale=1.5)
    return p


def get_regional_choropleth(region_name: str, all_nations: list) -> Optional[Path]:
    """Generate a choropleth map for all countries in a UN region (zoomed to the region).
    Saved to outputs/figures/regional_choropleths/ (gitignored; regenerated on build).
    """
    if not HAS_PLOTLY or not region_name:
        return None
    out_dir = Path("outputs/figures/regional_choropleths")
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = region_name.lower().replace(" ", "_").replace("/", "_").replace(",", "")
    p = out_dir / f"{slug}.png"
    focus = [n for n in all_nations if (n.get("un_region") or "") == region_name]
    if not focus:
        return None
    focus_df = pd.DataFrame([
        {"iso3": n["iso3"], "r": float(n.get("r", 0.0)), "country": n.get("country", n["iso3"])}
        for n in focus
    ])
    use_native_france = region_name == "Western Europe"
    map_df, france = (focus_df, None) if use_native_france else split_france_for_metropolitan_display(focus_df)
    fig = px.choropleth(
        map_df,
        locations="iso3",
        locationmode="ISO-3",
        color="r",
        color_continuous_scale=RTLDI_COLOR_SCALE,
        range_color=[0.0, 1.0],
        hover_name="country",
        hover_data={"r": ":.3f"},
    )
    apply_atlas_choropleth_style(fig)
    add_metropolitan_france_trace(fig, france)
    add_small_country_markers(fig, map_df, marker_size=7, show_text=True)
    apply_atlas_geo_style(fig, projection_type="mollweide", show_grid=True)
    if use_native_france:
        apply_european_france_bounds(fig, kind="western_europe")
    else:
        fig.update_geos(fitbounds="locations")
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text="R", font=dict(size=7)),
            len=0.4,
            thickness=6,
        ),
        title=dict(text=f"{region_name} Region — Enclosure Strength (R)", font=dict(size=8)),
        margin=dict(l=1, r=1, t=14, b=1),
        height=200,
        width=400,
        paper_bgcolor="white",
    )
    fig.write_image(p, width=400, height=200, scale=1.5)
    return p


def prepare_atlas_data():
    """Load breakdown JSON + 3yr G0 series, compute regional aggregates, global indicator losses,
    and the sorted-by-loss summary table. Returns a dict consumed by the three part builders.
    This is the single place where expensive data prep happens so nations can be skipped
    when only iterating on front or back matter.
    """
    detailed_all, detailed_alpha = load_detailed_data()

    print("Loading 3-year G0 series for nation text trends...")
    all_isos = [d["iso3"] for d in detailed_all]
    g0_series = load_g0_series(all_isos)

    # Compute on-the-fly bounded (capped) values for every nation so that all displayed
    # figures in this atlas edition respect the contextual institutional share cap.
    # The on-disk breakdown JSON/CSV retain the raw cross-sectional association for reference;
    # the published atlas applies the "what is actually possible after crediting other factors" bound.
    for d in detailed_all:
        g0 = float(d.get("g0") or 0)
        r = float(d.get("r") or 0)
        pop = float(d.get("population") or 0)
        raw_dg = ETA * (1.0 - r) * g0 if g0 > 0 else 0.0
        capped_dg = _bounded_drag(g0, r)
        raw_tot = raw_dg * pop if pop > 0 else 0.0
        capped_tot = capped_dg * pop if pop > 0 else 0.0
        cap_ratio = (capped_tot / raw_tot) if raw_tot > 0 else 1.0
        d["raw_delta_g_per_capita"] = raw_dg
        d["delta_g_per_capita"] = capped_dg          # override for downstream use
        d["raw_total_deficit_usd"] = raw_tot
        d["total_deficit_usd"] = capped_tot          # override so sorting + sums use bounded
        d["cap_ratio"] = cap_ratio
        d["capped"] = (capped_tot < raw_tot - 1e-6)

    print("Computing regional summaries for UN Regional Summaries...")
    from collections import defaultdict
    region_countries = defaultdict(list)
    for d in detailed_all:
        reg = d.get("un_region") or "Unknown"
        region_countries[reg].append(d)
    regional_data = {}
    for reg, cs in region_countries.items():
        n = len(cs)
        if n == 0:
            continue
        pops = [float(c.get("population") or 0) for c in cs]
        total_pop = sum(pops)
        rs = [float(c.get("r") or 0) for c in cs]
        mean_r = sum(rs) / n
        weighted_r = sum(r * p for r, p in zip(rs, pops)) / total_pop if total_pop > 0 else mean_r
        # Use the (now capped) total_deficit_usd that we just attached
        losts = [float(c.get("total_deficit_usd") or 0) for c in cs]
        total_lost = sum(losts)
        g0s = [float(c.get("g0") or 0) for c in cs]
        mean_g0 = sum(g0s) / n if n else 0
        # 9 levers: frac Yes + attributable capital exclusions (scaled to respect each country's cap)
        inds = []
        if cs and "components" in cs[0]:
            for i in range(9):
                comps = [c["components"][i] for c in cs if "components" in c and len(c.get("components", [])) > i]
                if not comps:
                    continue
                bins = [int(comp.get("bin", 0)) for comp in comps]
                raws = [comp.get("raw") for comp in comps]
                n_yes = sum(bins)
                frac_yes = n_yes / len(bins) if bins else 0
                valid_raws = []
                for x in raws:
                    if x is not None:
                        try:
                            valid_raws.append(float(x))
                        except (ValueError, TypeError):
                            pass
                avg_raw = sum(valid_raws) / len(valid_raws) if valid_raws else 0
                attr_lost = 0.0
                for c in cs:
                    if "components" in c and len(c.get("components", [])) > i:
                        if int(c["components"][i].get("bin", 0)) == 0:
                            g0 = float(c.get("g0") or 0)
                            pop = float(c.get("population") or 0)
                            raw_attr = ETA * (1.0 / 9.0) * g0 * pop
                            ratio = c.get("cap_ratio", 1.0)
                            attr_lost += raw_attr * ratio
                inds.append({
                    "num": i + 1,
                    "name": comps[0].get("name", ""),
                    "desc": comps[0].get("desc", ""),
                    "frac_yes": frac_yes,
                    "n_yes": n_yes,
                    "n_countries": len(bins),
                    "avg_raw": avg_raw,
                    "attributable_lost_gdp": attr_lost,
                })
        regional_data[reg] = {
            "n_countries": n,
            "total_pop": total_pop,
            "mean_r": mean_r,
            "weighted_r": weighted_r,
            "total_lost_gdp": total_lost,
            "mean_g0": mean_g0,
            "indicators": inds,
            "members": cs,
        }
    sorted_regions = sorted(regional_data.items(), key=lambda x: -x[1]["total_lost_gdp"])

    # Global capital exclusions per lever (for the full map page in front matter) — capped + scaled
    global_indicator_losts = [0.0] * 9
    global_total_lost = 0.0
    indicator_names = []
    indicator_descs = []
    for d in detailed_all:
        pop = float(d.get("population") or 0)
        g0 = float(d.get("g0") or 0)
        if d.get("total_deficit_usd"):
            global_total_lost += float(d.get("total_deficit_usd"))
        if "components" in d and d["components"]:
            if not indicator_names:
                indicator_names = [c.get("name", f"Indicator {i+1}") for i, c in enumerate(d["components"])]
                indicator_descs = [c.get("desc", "") for c in d["components"]]
            ratio = d.get("cap_ratio", 1.0)
            for i, comp in enumerate(d["components"]):
                if int(comp.get("bin", 0)) == 0:
                    raw_piece = ETA * (1.0 / 9.0) * g0 * pop
                    global_indicator_losts[i] += raw_piece * ratio

    # Summary table sorted by total loss desc
    detailed_by_loss = sorted(
        [d for d in detailed_all if d.get("total_deficit_usd")],
        key=lambda x: x["total_deficit_usd"],
        reverse=True
    )

    return {
        "detailed_all": detailed_all,
        "detailed_alpha": detailed_alpha,
        "g0_series": g0_series,
        "regional_data": regional_data,
        "sorted_regions": sorted_regions,
        "global_indicator_losts": global_indicator_losts,
        "global_total_lost": global_total_lost,
        "indicator_names": indicator_names,
        "indicator_descs": indicator_descs,
        "detailed_by_loss": detailed_by_loss,
    }


def create_pdf():
    """Backward-compatible entry point: builds all four modular parts then concatenates the release PDF.
    This is what `python -m src.generate_atlas_ebook` (no args) has always done.
    """
    data = prepare_atlas_data()
    front = build_front_matter(data)
    regions = build_regions(data)
    nations = build_nations(data)
    subprocess.run([sys.executable, "-m", "src.generate_eurozone_atlas"], check=True)
    back = build_back_matter(data)
    out = concat_pdfs(front, regions, nations, back, Path(RELEASE_PDF), Path(EUROZONE_PDF))
    print(f"Release PDF (concatenated): {out}")
    return out


def build_front_matter(data: dict) -> Path:
    """Build the front matter PDF (title, exec, method, diagnostic, carto+global indicator lost table+world total,
    TOC, and the paginated Summary Table of all 193 nations).
    Regions are now a completely separate part (see build_regions) so they can be iterated independently
    without regenerating front matter or the 193 nation pages. This split also eliminates any risk of
    accidental repeated page emission across sections.
    """
    pdf = RTLDIAtlasPDF()
    detailed_all = data["detailed_all"]
    detailed_by_loss = data["detailed_by_loss"]
    global_indicator_losts = data["global_indicator_losts"]
    global_total_lost = data["global_total_lost"]
    indicator_names = data["indicator_names"]
    indicator_descs = data["indicator_descs"]

    # ========== COVER ==========
    pdf.add_chromeless_page()
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, style="F")
    pdf.set_fill_color(*HEADER_COLOR)
    pdf.rect(18, 22, 3, PAGE_HEIGHT - 44, style="F")
    pdf.set_fill_color(*ACCENT_COLOR)
    pdf.rect(22, 22, 1.5, PAGE_HEIGHT - 44, style="F")
    pdf.set_y(42)
    pdf.set_x(34)
    pdf.set_font(FONT_NAME, "", 34)
    pdf.set_text_color(*INK)
    pdf.cell(0, 13, "RTLDI ATLAS 2026", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(34)
    pdf.set_font(FONT_NAME, "", 15)
    pdf.set_text_color(*HEADER_COLOR)
    pdf.cell(0, 8, "Right to Life Deficit Index for United Nations Member States", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(34)
    pdf.set_font(FONT_NAME, "", 11)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(145, 5.4, "Identifying capital exclusions: lost potential GDP associated with missing foundational protections. Contextually bounded with a 25% institutional cap.")

    card_y = 104
    card_w = 42
    gap = 5
    pdf.metric_card(34, card_y, card_w, 28, "Global capital exclusions", format_money(global_total_lost), "annual, capped", PANEL_ALT)
    pdf.metric_card(34 + card_w + gap, card_y, card_w, 28, "UN member states", "193", "22 regions")
    pdf.metric_card(34 + (card_w + gap) * 2, card_y, card_w, 28, "Coefficient eta", f"{ETA:.2f}", "population-weighted")

    pdf.set_xy(34, 157)
    pdf.set_font(FONT_NAME, "", 9)
    pdf.set_text_color(*INK)
    pdf.multi_cell(142, 5, "Based on Sid J.A. Hubbard, Causality and Attraction: A Continuum of Steady States (Version 3, May 2026), DOI 10.5281/zenodo.19468550")
    pdf.set_xy(34, 179)
    pdf.set_font(FONT_NAME, "", 8)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(142, 4.4, "Data: V-Dem 2024 components + latest World Bank GDP baseline as of 2026. Prepared for NGOs, researchers, policymakers, analysts, and public-interest users.")

    # ========== PUBLICATION RECORD ==========
    pdf.add_page()
    pdf.chapter_title("Publication Record, Rights, and Citation")
    pdf.section_label("Edition")
    pdf.body_text(
        "RTLDI Atlas of UN Member States, 2026 print edition. Generated from the corrected nine-lever "
        "public pipeline and synchronized with the web atlas, interactive map, Full Data View, and linked-data export."
    )
    pdf.section_label("Project and authorship")
    pdf.body_text(
        "Published by the RTLDI Atlas Project. Sid J.A. Hubbard is Principal Investigator and is responsible "
        "for the project's methods, decisions, interpretation, engineering direction, and publication."
    )
    pdf.section_label("Rights")
    pdf.body_text(
        "The RTLDI Atlas repository — code, data-processing pipeline, project documentation, and generated "
        "outputs — is open source under the MIT License. The underlying theoretical framework and book content "
        "are separate works. Causality and Attraction remains under its original copyright and CC BY-NC-ND 4.0 "
        "terms and is not relicensed by the repository's MIT License."
    )
    pdf.section_label("Recommended citation")
    pdf.body_text(
        "RTLDI Atlas Project. (2026). RTLDI Atlas of UN Member States [Data set, software, and atlas]. "
        "Sid J.A. Hubbard, Principal Investigator."
    )
    draw_mini_link(pdf, label="Atlas repository", url=REPOSITORY_URL, slug="publication-repository")
    pdf.small_text(
        "Source theory: Hubbard, Sid J.A. (2026). Causality and Attraction: A Continuum of Steady States, "
        "Volume I, Version 3."
    )
    draw_mini_link(pdf, label="Source theory DOI", url="https://doi.org/10.5281/zenodo.19468550", slug="publication-doi")

    # ========== ABOUT ==========
    pdf.add_page()
    pdf.chapter_title("About the RTLDI Atlas")
    pdf.body_text(
        "The RTLDI Atlas is an open, reproducible atlas of the conditions that protect human life and allow "
        "capital to operate across all 193 United Nations Member States. It originates in Sid J.A. Hubbard's "
        "Causality and Attraction: A Continuum of Steady States, Volume I. The Atlas operationalizes the "
        "book's Right-to-Life Protection method by translating nine protections into country classifications, "
        "an RTLP score, the Right to Life Deficit Index, and bounded estimates of capital exclusion."
    )
    pdf.section_label("Related works")
    draw_mini_link(pdf, label="Causality and Attraction, Volume I", url="https://doi.org/10.5281/zenodo.19468550", slug="about-volume-one")
    draw_mini_link(pdf, label="Nested Causal Modelling book", url="https://www.amazon.com/dp/B0H8K4C3S6", slug="about-ncm-book")
    draw_mini_link(pdf, label="Nested Causal Modelling audiobook", url="https://elevenreader.io/audiobooks/nested-causal-modelling-audiobook/8Mj5lsaUYs3WwjKAn1Xu", slug="about-ncm-audio")

    pdf.add_page()
    pdf.chapter_title("Authorship and Production Disclosure")
    pdf.section_label("Principal Investigator")
    pdf.body_text(
        "Sid J.A. Hubbard is the Principal Investigator of the RTLDI Atlas Project. He is an independent "
        "research technologist designing mathematical and architectural interventions for systemic complexity "
        "across economics, governance, technology, and AI."
    )
    draw_mini_link(pdf, label="Sid J.A. Hubbard", url="https://sidhubbard.com/", slug="pi-website")
    draw_mini_link(pdf, label="Published project work", url="https://sidhubbard.com/#interventions", slug="pi-projects")
    draw_mini_link(pdf, label="LinkedIn", url="https://www.linkedin.com/in/sidhubbard", slug="pi-linkedin")
    pdf.section_label("Production disclosure")
    pdf.body_text(
        "At this stage, the entirety of the Atlas project is written, directed, and engineered by its Principal "
        "Investigator with the assistance of multiple AI and data-science tools used in research, software "
        "development, analysis, validation, and production. Responsibility for the project's methods, decisions, "
        "interpretations, and releases rests with the Principal Investigator."
    )
    pdf.section_label("Contributing public projects")
    pdf.body_text(
        "V-Dem supplies the institutional measurements used for levers 1–8. World Bank World Development "
        "Indicators supply GDP, population, undernourishment, and poverty observations. The United Nations "
        "Member States list defines the 193-country scope. These projects provide source observations; RTLP, "
        "RTLDI, lever classifications, capital-exclusion estimates, maps, and generated atlas products are RTLDI "
        "Atlas Project outputs."
    )

    # ========== CONTENTS ==========
    pdf.add_page()
    pdf.chapter_title("Contents and Reading Sequence")
    contents = [
        ("Part I", "Project record and global overview", "About, methods, responsible interpretation, global map, and 193-country summary."),
        ("Part II", "UN regional summaries", "Twenty-two regional comparisons with common metrics, maps, and lever breakdowns."),
        ("Part III", "Nation profiles", "One page for each UN Member State, ordered alphabetically."),
        ("Part IV", "Eurozone focused report", "A 21-member shared-currency comparison using the canonical global model."),
        ("Part V", "Evidence, data, and project record", "Executable crosswalk, regression, datasets, attribution, source access, glossary, and credits."),
    ]
    for part, title, description in contents:
        pdf.section_label(part, HEADER_COLOR)
        pdf.set_font(FONT_NAME, "", 12)
        pdf.set_text_color(*INK)
        pdf.cell(0, 6, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.small_text(description)
        pdf.ln(2)
    pdf.body_text(
        "QR title pages introduce the regional summaries, nation profiles, Eurozone maps, and glossary/source "
        "section. Every other printed web link is paired with a compact QR symbol, and every destination is also "
        "printed as a URL so access does not depend on QR scanning."
    )

    # ========== EXECUTIVE DESCRIPTION ==========
    pdf.add_page()
    pdf.chapter_title("Executive Description")
    pdf.body_text(
        "The RTLDI — Right to Life Deficit Index — is taken from the source framework (Hubbard, Zenodo 10.5281/zenodo.19468550) and extended here to estimate potential GDP statistically associated with missing protections.\n\n"
        f"The Atlas calls this modeled quantity \"capital exclusions.\" The corrected 2026 cross-sectional model estimates {format_money(global_total_lost)} in bounded annual capital exclusions. It is not observed money, a causal estimate for any single lever, or a guaranteed reform dividend."
    )
    pdf.ln(3)
    pdf.body_text(
        "This 2026 Atlas applies the source RTLDI to all 193 UN Member States using V-Dem 2024 observations and the most recent World Bank baseline assembled for the edition. A population-weighted cross-sectional regression estimates the association between activated protections and GDP per capita. The projection is then bounded so the nine conditions are never assigned more than 25% of observed GDP."
    )
    pdf.ln(3)
    pdf.body_text(
        "This is practical economic intelligence, not a causal forecast or judgment on nations. The atlas identifies where specific protections are absent and reports the bounded economic scale associated with those absences. Raw observations, thresholds, regression evidence, uncertainty, and source ownership are disclosed in the evidence section."
    )

    # ========== METHODOLOGY ==========
    pdf.add_page()
    pdf.chapter_title("Methodology and Data Sources")
    pdf.body_text(
        "RTLP Score (R)\n"
        "R is the simple average of nine binary indicators (0 = no protection, 1 = full protection). "
        "Eight indicators are derived from V-Dem country-year observations (2024 score year; current reproducible workflow targets v16) using the following thresholds "
        "(higher = stronger protection):\n\n"
        "1. Legal Protections — v2cltrnslw ≥ 2.0\n"
        "2. Independent Judiciary — average(v2juhcind, v2juncind) ≥ 2.0\n"
        "3. Law Enforcement Accountability — v2clkill ≥ 2.0\n"
        "4. Protection Against Arbitrary Detention — v2xcl_acjst ≥ 0.5\n"
        "5. Freedom from Torture — v2cltort ≥ 2.0\n"
        "6. Civilian Protection in Conflict — v2x_clphy ≥ 0.5\n"
        "7. Access to Justice — v2clrspct ≥ 2.0\n"
        "8. Freedom of Expression & Whistleblower Protections — v2x_freexp ≥ 0.5\n\n"
        "9. Socioeconomic Conditions — World Bank: undernourishment ≤ 5 % AND poverty headcount ($2.15) ≤ 10 %.\n\n"
        "R = (number of 'Yes' indicators) / 9\n\n"
        "Economic Projection\n"
        f"ΔG (per-capita) = min( η × (1 − R) × G₀ , 0.25 × G₀ ) with operational η={ETA:.2f}. The regression estimate is 0.356; the separate 25% contextual cap bounds attribution. G₀ is the most recent published GDP per capita used by this edition. Total capital exclusions = ΔG × population.\n\n"
        "Data Vintage Note for 2026 Edition\n"
        "V-Dem components reflect the latest available year in the source file (2024). GDP per capita (G₀) "
        "uses the freshest published values available at the time of atlas production. This follows the "
        "principle that RTLP governance scores are relatively stable year-to-year while GDP is the more "
        "dynamic variable in the equation."
    )
    pdf.small_text(
        "Full crosswalk and binarization rules: docs/indicator_crosswalk.md\n"
        "Source equations: Sid J.A. Hubbard, Causality and Attraction v3 (2026), DOI 10.5281/zenodo.19468550"
    )

    # ========== CAUSAL PROJECTION FROM OUTER ENCLOSURES ==========
    pdf.add_page()
    pdf.chapter_title("Causal Projection from Outer Enclosures")
    pdf.body_text(
        "Causal projection distinguishes a change in what can happen from a forecast that says exactly what will happen next. An outer enclosure is a protective institutional boundary around the actions of people inside a system. Switching a lever changes that boundary and therefore changes the feasible set of responses. Movement becomes possible; its timing, scale, and path remain contingent."
    )
    pdf.ln(3)
    pdf.section_label("The projection", ACCENT_COLOR)
    pdf.ln(1)
    pdf.body_text(
        "A causal projection follows the consequences of opening or closing a pathway. While a protection is absent, benefits that require that protected pathway are structurally unavailable. Once an effective protection is present, those benefits enter the system's reachable set. This is an institutional availability claim, not a point prediction of immediate GDP movement. Implementation, credibility, enforcement, information, and the choices of real actors still determine realization."
    )
    pdf.ln(3)
    pdf.section_label("Worked example: whistleblower protection", ACCENT_COLOR)
    pdf.ln(1)
    pdf.body_text(
        "Corruption commonly produces a financial benefit for the people or organizations sustaining it. Insiders are often best placed to reveal the arrangement. Without credible protection from dismissal, prosecution, violence, or other retaliation, disclosure can impose concentrated personal costs while the beneficiaries retain the corrupt rent. Corruption is not logically guaranteed in every unprotected system, but concealment is favored and the protected inside-to-outside evidence channel is closed or severely constrained.\n\n"
        "Effective whistleblower protection opens that channel. A protected disclosure, investigation, recovery, and deterrence pathway becomes institutionally available. The reform does not guarantee that a whistleblower appears immediately, that enforcement succeeds, or that a particular sum is recovered. It does guarantee the relevant change in modeled possibility: a benefit that cannot be reached through a protected reporting channel while that channel is absent can become reachable once the channel exists and is credible."
    )
    pdf.ln(3)
    pdf.set_fill_color(*PANEL_BG)
    pdf.set_draw_color(*RULE)
    callout_y = pdf.get_y()
    pdf.rect(MARGIN, callout_y, CONTENT_WIDTH, 29, style="DF")
    pdf.set_xy(MARGIN + 4, callout_y + 3)
    pdf.set_font(FONT_NAME, "", 7)
    pdf.set_text_color(*ACCENT_COLOR)
    pdf.cell(0, 3.5, "EVIDENCE AND CLAIM BOUNDARY", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(MARGIN + 4)
    pdf.set_font(FONT_NAME, "", 8.2)
    pdf.set_text_color(*INK)
    pdf.multi_cell(
        CONTENT_WIDTH - 8,
        4.1,
        "The Atlas cross-section shows that high-RTLP countries are generally more prosperous, supporting the direction and economic relevance of the projection. It does not establish that one newly activated lever alone causes the full estimated difference. The defensible causal statement is that effective outer enclosures remove specified barriers and create institutional option value; realized gains remain empirical outcomes to measure after a lever change.",
    )

    # ========== READER GUIDE ==========
    pdf.add_page()
    pdf.chapter_title("Reading and Using the Atlas")
    pdf.body_text(
        "Begin with R, the share of nine protections meeting the operational thresholds. Read the green/red lever strip to identify which conditions are present, then inspect each raw value rather than treating the binary classification as the whole observation. G₀ is the GDP-per-capita baseline. ΔG is the bounded per-capita capital-exclusion estimate; the national total multiplies ΔG by population.\n\n"
        "Regional pages support comparison inside a shared geographic context. Nation pages support diagnosis of one country. The Eurozone report applies the same global coefficient to a shared-currency subset. Lever-level amounts allocate a country's bounded total across missing components; they are not nine independent causal estimates.\n\n"
        "Policymakers and civil society can use the profiles to identify candidate reforms and questions for deeper investigation. Analysts should use the Full Data View and source fields for comparison. Investors should treat the results as one governance-risk lens, not as investment advice or a forecast."
    )

    pdf.add_page()
    pdf.chapter_title("Interpretation, Scope, and Limitations")
    pdf.body_text(
        "Association is not causal identification. The regression is cross-sectional and may reflect omitted variables, reverse causation, measurement error, model specification, and common causes of both institutional protection and GDP. The one-year growth check reported in the evidence section is not statistically significant.\n\n"
        "R uses V-Dem 2024 observations paired with the freshest World Bank values assembled for the 2026 baseline. Binarization thresholds and proxy choices are RTLDI Atlas Project operationalizations. Missing socioeconomic observations are conservatively scored as lever 9 absent. Current-US-dollar GDP includes exchange-rate and price-level movement.\n\n"
        "The operational eta is 0.36, based on a corrected estimate of 0.356. The separate 25% contextual cap prevents the model from assigning more than one quarter of observed GDP to the nine conditions. That bound limits the claim but does not establish the counterfactual. Whether any measured exclusion is realized after reform depends on industry, resources, human capital, geography, conflict, history, implementation quality, and other conditions outside this reduced model."
    )

    pdf.small_text(
        "Source framework: Sid J.A. Hubbard, Causality and Attraction v3 (2026), DOI 10.5281/zenodo.19468550"
    )
    draw_mini_link(pdf, label="Full Data View", url=FULL_DATA_URL, slug="limitations-full-data")

    # ========== CARTOGRAPHIC APPROACH AND THE NESTED MAP ==========
    pdf.add_page()
    pdf.chapter_title("Cartographic Approach and the Nested Map")

    # Enlarged lead-in text for front-matter readability
    pdf.set_x(MARGIN)
    pdf.body_text(
        "All choropleths use the Mollweide equal-area projection via standard tools. This ensures accurate area representation, full reproducibility, and accessibility for NGOs. The maps are generated once and embedded in the PDF so that every reader sees the same visual data.",
        size=11
    )

    # Embed the canonical global map with text flowed beside it on the left
    global_map_path = "outputs/figures/rtl_di_enclosure_strength_2026_choropleth.png"
    try:
        pdf.ln(1)
        pdf.set_font(FONT_NAME, "", 8)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.cell(0, 4, "Canonical Global Choropleth — Enclosure Strength (R)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        map_h = 58
        map_w = 95
        map_x = PAGE_WIDTH - MARGIN - map_w
        y_map = pdf.get_y()

        pdf.image(global_map_path, x=map_x, w=map_w, h=map_h)

        # Flow body text to the left of the map (the "canonical whole-earth" point lives here for visual integration)
        left_w = CONTENT_WIDTH - map_w - 6
        pdf.set_xy(MARGIN, y_map)
        pdf.set_font(FONT_NAME, "", 9.5)
        pdf.set_text_color(35, 35, 35)
        pdf.multi_cell(left_w, 4.3,
            "Canonical whole-earth view: the image serves as the primary visual anchor, embodying the source's call for structurally faithful, low-distortion mapping of the global human enclosure."
        )

        # Small technical note under the flowed text / beside lower map
        pdf.set_xy(MARGIN, y_map + 22)
        pdf.set_font(FONT_NAME, "", 6.5)
        pdf.set_text_color(85, 85, 85)
        pdf.multi_cell(left_w, 3.2,
            "Mollweide equal-area projection. Primary anchor for accuracy and nested wholeness (source Ch. 2). Regional and nation views throughout the atlas use the same RTLDI atlas R scale."
        )

        # Advance past the full map height
        pdf.set_y(y_map + map_h + 4)
    except Exception:
        pdf.set_x(MARGIN)
        pdf.small_text("[Global map could not be embedded]")

    # Global Capital Exclusions table — placed after the body text / graphic area and before the interpretive world description
    pdf.set_x(MARGIN)
    pdf.section_label("Global capital exclusions by lever")
    pdf.ln(0.5)

    # Clean table header
    tcol = [7, 88, 30, 16]  # #, name, lost, pct
    headers = ["#", "Lever", "Annual Capital Exclusions", "% total"]
    pdf.set_font(FONT_NAME, "", 7.5)
    pdf.set_fill_color(*HEADER_COLOR)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(tcol[i], 4.2, h, border=1, fill=True, align="C" if i != 1 else "L")
    pdf.ln()
    pdf.set_text_color(*BLACK)

    ind_tuples = list(enumerate(global_indicator_losts))
    ind_tuples.sort(key=lambda x: x[1], reverse=True)

    for rank, (i, lost) in enumerate(ind_tuples):
        name = lever_short(i + 1, indicator_names[i] if i < len(indicator_names) else f"Lever {i+1}")
        pct = (lost / global_total_lost * 100) if global_total_lost > 0 else 0
        desc = lever_description(i + 1, indicator_descs[i] if i < len(indicator_descs) else "")

        zebra = (rank % 2 == 0)
        pdf.set_fill_color(*PANEL_BG) if zebra else (255, 255, 255)

        pdf.set_font(FONT_NAME, "", 7.5)
        pdf.set_text_color(*BLACK)
        pdf.cell(tcol[0], 4, str(i + 1), border=1, align="C", fill=zebra)
        pdf.cell(tcol[1], 4, name, border=1, fill=zebra)
        lost_str = format_money(lost)
        pdf.cell(tcol[2], 4, lost_str, border=1, align="R", fill=zebra)
        pdf.cell(tcol[3], 4, f"{pct:.1f}%", border=1, align="C", fill=zebra, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Description under the row (still inside the table visual block for scannability)
        if desc:
            pdf.set_font(FONT_NAME, "", 6.5)
            pdf.set_text_color(70, 70, 70)
            pdf.set_x(MARGIN + tcol[0] + 1)
            pdf.multi_cell(CONTENT_WIDTH - tcol[0] - 2, 2.9, desc)
            pdf.set_x(MARGIN)

    pdf.ln(1.5)

    # Interpretive world description (the "RTLP breakdown" narrative) — now after the table, enlarged for readability
    pdf.set_x(MARGIN)
    pdf.set_font(FONT_NAME, "", 9)
    pdf.set_text_color(30, 30, 30)
    desc_text = (
        f"These figures paint a picture of a world where the greatest measured disparities are associated with access to justice, preventing torture and inhumane treatment, independent judiciaries, and basic legal protections—together accounting for a large share of the bounded global total. "
        f"The associated exclusions are comparatively lower for civilian protection in conflict, freedom of expression and whistleblowing, and protection against arbitrary detention. "
        f"Socioeconomic shortfalls remain a persistent burden. After applying the contextual cap derived from case studies of archetypal nations, the data show how weaknesses in the nine core protections are linked to substantial differences in prosperity once other determinants (resources, industry, history, location) are credited."
    )
    pdf.multi_cell(0, 3.6, desc_text)
    pdf.ln(0.8)

    # Prominent planet total
    pdf.set_x(MARGIN)
    pdf.set_fill_color(*PANEL_ALT)
    pdf.set_draw_color(*RULE)
    y_total = pdf.get_y()
    pdf.rect(MARGIN, y_total, CONTENT_WIDTH, 17, style="DF")
    pdf.set_xy(MARGIN + 3, y_total + 2.2)
    pdf.set_font(FONT_NAME, "", 9)
    pdf.set_text_color(*HEADER_COLOR)
    total_t = global_total_lost / 1e12
    pdf.multi_cell(CONTENT_WIDTH - 6, 4, f"Total modeled global capital exclusions: ${total_t:,.2f} trillion. This bounded cross-sectional estimate is associated with missing protections; it is not directly observed capital or a guaranteed causal effect.")
    pdf.set_y(y_total + 19)

    pdf.ln(0.5)
    pdf.set_x(MARGIN)
    pdf.set_font(FONT_NAME, "", 6.5)
    pdf.set_text_color(85, 85, 85)
    pdf.multi_cell(0, 2.8,
        "Data in outputs/atlas/ supports re-projection in external tools for AuthaGraph/Dymaxion if desired. See source Ch. 2 and Epilogue on maps and nested causality (DOI 10.5281/zenodo.19468550)."
    )

    # ========== SUMMARY TABLE OF ALL NATIONS ==========
    pdf.add_page()
    pdf.chapter_title("Summary Table of All 193 UN Member Nations")
    pdf.small_text(
        "Sorted by estimated total annual GDP loss (highest first). "
        "R = RTLP score (0–1); values shown as fraction of 9 indicators where possible. "
        "Losses in current USD using 2026 baseline GDP per capita paired with latest available RTLP components (2024)."
    )
    pdf.ln(2)

    col_widths = [8, 38, 22, 18, 22, 28, 28]
    headers = ["#", "Country", "Region", "R", "Per Capita Capital Exclusions", "Capital Exclusions (USD)", "Population"]
    pdf.set_font(FONT_NAME, "", 7)
    pdf.set_fill_color(*HEADER_COLOR)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 5, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*BLACK)
    pdf.set_font(FONT_NAME, "", 6.5)

    rows_per_page = 38
    for idx, d in enumerate(detailed_by_loss):
        if idx > 0 and idx % rows_per_page == 0:
            pdf.add_page()
            pdf.set_font(FONT_NAME, "", 7)
            pdf.set_fill_color(*HEADER_COLOR)
            pdf.set_text_color(255, 255, 255)
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 5, h, border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_text_color(*BLACK)
            pdf.set_font(FONT_NAME, "", 6.5)

        rank = int(d.get("rank_by_total_deficit", idx + 1)) if d.get("rank_by_total_deficit") else idx + 1
        country = d["country"][:28]
        region = d["un_region"][:18] if d.get("un_region") else ""
        r_val = d["r"]
        r_str = f"{r_val:.2f}" if r_val is not None else "N/A"
        per_cap = d["delta_g_per_capita"]
        per_cap_str = f"${per_cap:,.0f}" if per_cap is not None else "N/A"
        total = d["total_deficit_usd"]
        if total is not None:
            if total >= 1e9:
                total_str = f"${total/1e9:.1f} bn"
            else:
                total_str = f"${total/1e6:.0f} m"
        else:
            total_str = "N/A"
        pop = d["population"]
        if pop is None:
            pop_str = "N/A"
        elif pop < 100000:
            pop_str = f"{pop/1000:.0f} k"
        else:
            pop_str = f"{pop/1e6:.1f} m"

        zebra_fill = (idx % 2 == 0)
        pdf.set_fill_color(248, 248, 250) if zebra_fill else (255, 255, 255)

        if r_val is not None:
            if r_val >= 0.6:
                pdf.set_text_color(0, 128, 0)
            elif r_val <= 0.2:
                pdf.set_text_color(180, 0, 0)
            else:
                pdf.set_text_color(*BLACK)
        else:
            pdf.set_text_color(*BLACK)

        pdf.cell(col_widths[0], 4.2, str(rank), border=1, align="C", fill=zebra_fill)
        pdf.cell(col_widths[1], 4.2, country, border=1, fill=zebra_fill)
        pdf.cell(col_widths[2], 4.2, region, border=1, fill=zebra_fill)
        pdf.cell(col_widths[3], 4.2, r_str, border=1, align="C", fill=zebra_fill)
        pdf.set_text_color(*BLACK)
        pdf.cell(col_widths[4], 4.2, per_cap_str, border=1, align="R", fill=zebra_fill)
        pdf.cell(col_widths[5], 4.2, total_str, border=1, align="R", fill=zebra_fill)
        pdf.cell(col_widths[6], 4.2, pop_str, border=1, align="R", fill=zebra_fill, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Keep the QR title page on a recto in the assembled duplex volume.
    if pdf.page_no() % 2 == 1:
        pdf.add_chromeless_page()
    draw_qr_gateway(
        pdf,
        title="UN Regional Summaries",
        subtitle="Twenty-two comparable geographic views, with direct access to the interactive Web Atlas.",
        url=WEB_ATLAS_URL,
        slug="web-atlas-regions",
        kicker="Part II / Print and web",
        note="The summaries that follow use the same 193 canonical country records. Scan to compare regions, open countries, and inspect every lever online.",
    )

    # End of front matter (global 193-nation summary table). Regions are now in their own independent PDF
    # for fast iteration without re-generating front or the heavy nations section.
    out_path = Path(FRONT_PDF)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(out_path)
    print(f"Front matter PDF written to: {out_path}  ({pdf.page_no()} pages)")
    return out_path


def build_regions(data: dict) -> Path:
    """Build the UN Regional Summaries PDF as its own independent part (22 regions).
    One page per region with choropleth, stats, cumulative description,
    member table + REGIONAL TOTAL, 9-indicator breakdown, and universal-fail callout where applicable.
    This is now separate so front matter changes and nation page changes do not force re-generation
    of the region pages (and vice-versa). Included in the final concat after front, before nations.
    """
    pdf = RTLDIAtlasPDF()
    detailed_all = data["detailed_all"]
    sorted_regions = data["sorted_regions"]

    for reg_name, reg_sum in sorted_regions:
        pdf.add_page()
        pdf.section_label("UN regional summary", HEADER_COLOR)
        pdf.set_font(FONT_NAME, "", 16)
        pdf.set_text_color(*INK)
        pdf.cell(0, 7, f"{reg_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

        metric_y = pdf.get_y()
        metric_w = (CONTENT_WIDTH - 9) / 4
        pdf.metric_card(MARGIN, metric_y, metric_w, 22, "Countries", str(reg_sum["n_countries"]))
        pdf.metric_card(MARGIN + metric_w + 3, metric_y, metric_w, 22, "Population", f"{reg_sum['total_pop']/1e6:,.1f}m")
        pdf.metric_card(MARGIN + (metric_w + 3) * 2, metric_y, metric_w, 22, "Weighted R", f"{reg_sum['weighted_r']:.2f}", fill=PANEL_ALT)
        pdf.metric_card(MARGIN + (metric_w + 3) * 3, metric_y, metric_w, 22, "Capital exclusions", f"${reg_sum['total_lost_gdp']/1e9:,.1f}B")
        pdf.set_y(metric_y + 25)

        members = reg_sum.get("members", [])
        n = reg_sum['n_countries']
        inds = reg_sum.get("indicators", [])
        para1 = ""
        para2 = ""
        if inds:
            sorted_inds = sorted(inds, key=lambda x: x.get("frac_yes", 0), reverse=True)
            strong_names = [lever_name(i["num"], i["name"]) for i in sorted_inds[:2] if i.get("frac_yes", 0) > 0.4]
            weak_names = [lever_name(i["num"], i["name"]) for i in sorted_inds[-2:]]
            potential_b = sum(i.get("attributable_lost_gdp", 0) for i in sorted_inds[-3:]) / 1e9
            para1 = (
                f"The {reg_name} region has a population-weighted average RTLP score of {reg_sum['weighted_r']:.2f}. "
                f"This cumulative measure indicates that, across its {n} member countries, "
                f"roughly {reg_sum['weighted_r']*100:.0f}% of the nine core protections are in place on average, "
                f"corresponding to an estimated ${reg_sum['total_lost_gdp']/1e9:,.2f} billion in capital exclusions (lost potential GDP) annually. "
                f"The region demonstrates particular strength in {', '.join(strong_names) if strong_names else 'several key areas'}, "
                f"where a substantial share of countries satisfy the binarization thresholds for those indicators. "
                f"These protections represent opportunities to support greater economic scale for life and capital."
            )
            para2 = (
                f"Strengthening the areas with lower implementation—especially {', '.join(weak_names) if weak_names else 'priority areas'}—"
                f"is associated with the largest opportunities for realizing additional scale in the region (after the 25% contextual bound). "
                f"The cross-sectional association links stronger protections to greater economic scale of roughly ${potential_b:,.2f} billion annually for the region as a whole (within the bound). "
                f"Whether and how much of that association is realized depends on the other determinants of output (industry structure, resources, human capital, history) that the model explicitly accounts for by bounding the contribution of these nine factors."
            )

        # Place map on the right; flow descriptive text (larger) on the left beside it.
        # Then put the member table full-width beneath the text+map area, before the RTLP breakdown.
        map_p = get_regional_choropleth(reg_name, detailed_all)
        map_h = 0
        if map_p and map_p.exists():
            map_w = 92  # mm, right side for side-by-side
            map_h = map_w / 2.0  # preserve 2:1 aspect ratio from generated 400x200 (fixes squashed/distorted appearance)
            map_x = PAGE_WIDTH - MARGIN - map_w
            y_map = pdf.get_y()

            pdf.image(str(map_p), x=map_x, w=map_w, h=map_h)

            # Flow the two descriptive paragraphs on the left of the map (enlarged for readability)
            left_w = CONTENT_WIDTH - map_w - 5
            pdf.set_xy(MARGIN, y_map)
            pdf.set_font(FONT_NAME, "", 7.7)
            pdf.set_text_color(40, 40, 40)
            if para1:
                pdf.multi_cell(left_w, 3.3, para1)
            if para2:
                pdf.set_xy(MARGIN, pdf.get_y() + 0.6)
                pdf.multi_cell(left_w, 3.3, para2)

            # Advance past the map for content below
            pdf.set_y(max(pdf.get_y(), y_map + map_h + 2))

            # Compact map caption under the flowed area
            pdf.set_font(FONT_NAME, "", 5.5)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(0, 2.2,
                "Mollweide projection (equal-area, same RTLDI atlas R scale as global choropleth).")
            pdf.ln(0.3)
        else:
            # Fallback: full-width larger text if no map
            pdf.set_font(FONT_NAME, "", 8)
            pdf.set_text_color(40, 40, 40)
            if para1:
                pdf.multi_cell(0, 3.3, para1)
            if para2:
                pdf.ln(0.4)
                pdf.multi_cell(0, 3.3, para2)
            pdf.ln(0.5)

        # Member nations table — now beneath the (flowed) text and map, above the RTLP breakdown
        members_sorted = sorted(reg_sum.get("members", []), key=lambda x: x.get("total_deficit_usd", 0) or 0, reverse=True)
        if members_sorted:
            pdf.section_label("Member nations sorted by capital exclusions", HEADER_COLOR)
            pdf.ln(0.2)
            tcols = [36, 9, 15, 16, 20]
            thdrs = ["Country", "R", "G0 ($)", "Pop", "Capital Exclusions ($)"]
            pdf.set_font(FONT_NAME, "", 5.5)
            pdf.set_fill_color(*HEADER_COLOR)
            pdf.set_text_color(255, 255, 255)
            for ii, hh in enumerate(thdrs):
                pdf.cell(tcols[ii], 2.8, hh, border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_text_color(*BLACK)
            for m in members_sorted:
                cname = str(m.get("country") or m.get("iso3", ""))[:20]
                rr = m.get("r")
                rstr = f"{rr:.2f}" if rr is not None else "N/A"
                gg = m.get("g0")
                gstr = f"{gg:,.0f}" if gg is not None else "N/A"
                pp = m.get("population")
                if pp is None:
                    pstr = "N/A"
                elif pp < 100000:
                    pstr = f"{pp/1000:.0f}k"
                else:
                    pstr = f"{pp/1e6:.1f}m" if pp else "N/A"
                ll = m.get("total_deficit_usd")
                if ll is not None:
                    lstr = f"${ll/1e9:.2f}b" if ll >= 1e9 else f"${ll/1e6:.0f}m"
                else:
                    lstr = "N/A"

                font = ""
                pdf.set_font(FONT_NAME, font, 5)

                if rr is not None:
                    if rr >= 0.6:
                        pdf.set_text_color(0, 128, 0)
                    elif rr <= 0.2:
                        pdf.set_text_color(180, 0, 0)
                    else:
                        pdf.set_text_color(*BLACK)
                else:
                    pdf.set_text_color(*BLACK)

                pdf.cell(tcols[0], 2.5, cname, border=1)
                pdf.cell(tcols[1], 2.5, rstr, border=1, align="C")
                pdf.set_text_color(*BLACK)
                pdf.cell(tcols[2], 2.5, gstr, border=1, align="R")
                pdf.cell(tcols[3], 2.5, pstr, border=1, align="R")
                pdf.cell(tcols[4], 2.5, lstr, border=1, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_font(FONT_NAME, "", 5.5)
            pdf.set_fill_color(*PANEL_ALT)
            pdf.set_text_color(*BLACK)
            totp = reg_sum["total_pop"]
            totl = reg_sum["total_lost_gdp"]
            totpstr = f"{totp/1e6:.1f}m"
            totlstr = f"${totl/1e9:.2f}b"
            wrstr = f"{reg_sum['weighted_r']:.2f}"
            pdf.cell(tcols[0], 2.7, "REGIONAL TOTAL", border=1, fill=True)
            pdf.cell(tcols[1], 2.7, wrstr, border=1, align="C", fill=True)
            pdf.cell(tcols[2], 2.7, "", border=1, fill=True)
            pdf.cell(tcols[3], 2.7, totpstr, border=1, align="R", fill=True)
            pdf.cell(tcols[4], 2.7, totlstr, border=1, align="R", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_fill_color(240, 240, 240)
            pdf.ln(0.6)

        pdf.section_label("RTLP indicator breakdown for the region", HEADER_COLOR)
        pdf.ln(0.2)

        for ind in reg_sum.get("indicators", []):
            pct = ind["frac_yes"] * 100
            lost_b = ind.get("attributable_lost_gdp", 0) / 1e9
            pdf.set_font(FONT_NAME, "", 6)
            pdf.set_text_color(*BLACK)
            name = lever_name(ind["num"], ind["name"])
            desc = lever_description(ind["num"], ind["desc"])
            line = f"Lever {ind['num']}: {name} | {pct:.0f}% Yes ({ind['n_yes']}/{ind['n_countries']})"
            pdf.cell(0, 2.8, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            bar_x = MARGIN + 2
            bar_y = pdf.get_y() - 0.2
            bar_w = 34
            pdf.set_fill_color(228, 234, 240)
            pdf.rect(bar_x, bar_y, bar_w, 1.4, style="F")
            pdf.set_fill_color(*ACCENT_COLOR)
            pdf.rect(bar_x, bar_y, bar_w * max(0, min(100, pct)) / 100.0, 1.4, style="F")
            pdf.set_font(FONT_NAME, "", 5.5)
            pdf.set_text_color(70, 70, 70)
            pdf.set_x(MARGIN + 39)
            pdf.multi_cell(0, 2.4,
                f"Annual exclusion: {format_money(ind.get('attributable_lost_gdp', 0))} ({(lost_b * 1e9 / reg_sum['total_lost_gdp'] * 100) if reg_sum['total_lost_gdp'] > 0 else 0:.0f}% of region total). Avg raw {ind['avg_raw']:.2f}. {desc}"
            )
            pdf.set_x(MARGIN)

        if n > 3:
            common_fails = [ind for ind in inds if ind.get("frac_yes", 0) == 0]
            if common_fails:
                chosen = max(common_fails, key=lambda x: x.get("attributable_lost_gdp", 0))
                gain_b = chosen.get("attributable_lost_gdp", 0) / 1e9
                pdf.set_font(FONT_NAME, "", 6)
                pdf.set_text_color(20, 20, 20)
                pdf.multi_cell(0, 2.8,
                    f"Critically, every single nation in the {reg_name} region is currently failing lever {chosen['num']}: {lever_name(chosen['num'], chosen['name'])}. "
                    f"The portion of the region's capital exclusions (after the 25% cap) associated with this lever is ${gain_b:,.2f} billion."
                )
                pdf.ln(0.3)

        pdf.ln(0.4)
        pdf.set_font(FONT_NAME, "", 5.5)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 2.3,
            f"Note: Weighted R is population-weighted mean of member countries' R. Attributable lost for an indicator = sum over countries with 'No' on that indicator of (η/9 × G₀ × pop) with current η={ETA:.2f}. "
            "See individual nation profiles for country-level detail and 3-year trends."
        )

    out_path = Path(REGIONS_PDF)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(out_path)
    print(f"Regions PDF written to: {out_path}  ({pdf.page_no()} pages)")
    return out_path


def build_nations(data: dict) -> Path:
    """Build the nations (individual country profiles) PDF — the 193-page section.
    Regenerating this is the expensive step; changes to front/back should not require it.
    """
    pdf = RTLDIAtlasPDF()
    detailed_alpha = data["detailed_alpha"]
    g0_series = data["g0_series"]
    iso2_lookup = load_iso2_lookup()

    # In the assembled volume, this blank verso places the Part III QR title on a recto.
    pdf.add_chromeless_page()
    draw_qr_gateway(
        pdf,
        title="Detailed Nation Profiles",
        subtitle="One archival profile for every United Nations Member State, with direct access to interactive country exploration.",
        url=WEB_ATLAS_URL,
        slug="web-atlas-nations",
        kicker="Part III / Print and web",
        note="The 193 profiles that follow are ordered alphabetically. Scan to search Full Data, compare every field, and open a country in the interactive map.",
    )

    for d in detailed_alpha:
        pdf.add_page()

        iso2 = iso2_lookup.get(d["iso3"], "")
        yes_count = sum(c['bin'] for c in d['components'])

        g0 = d.get('g0') or 0
        dpc = d.get('delta_g_per_capita') or 0
        tot = d.get('total_deficit_usd') or 0
        pop = d.get('population') or 0
        if pop >= 100000:
            pop_str = f"{pop/1e6:,.1f} million"
        elif pop > 0:
            pop_str = f"{pop:,.0f}"
        else:
            pop_str = "N/A"
        trend_text = format_trend_text(
            d["iso3"], d.get("r"), d.get("population"),
            g0_series.get(d["iso3"], {})
        )

        hero_y = pdf.get_y()
        hero_h = 34
        r_score = float(d.get("r") or 0)
        pdf.set_fill_color(247, 250, 252)
        pdf.set_draw_color(*RULE)
        pdf.rect(MARGIN, hero_y, CONTENT_WIDTH, hero_h, style="DF")
        pdf.set_fill_color(*ACCENT_COLOR)
        pdf.rect(MARGIN, hero_y, 3.0, hero_h, style="F")

        pdf.set_xy(MARGIN + 6, hero_y + 4.0)
        pdf.set_font(FONT_NAME, "", 6.8)
        pdf.set_text_color(*ACCENT_COLOR)
        pdf.cell(0, 3.2, "NATION PROFILE", new_x=XPos.LMARGIN, new_y=YPos.TOP)
        pdf.set_xy(MARGIN + 6, hero_y + 8.0)
        pdf.set_font(FONT_NAME, "", 18)
        pdf.set_text_color(*INK)
        pdf.cell(120, 7.0, f"{d['country']} ({d['iso3']})")

        pdf.set_xy(PAGE_WIDTH - MARGIN - 32, hero_y + 4.5)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(*RULE)
        pdf.rect(PAGE_WIDTH - MARGIN - 32, hero_y + 4.0, 26, 20, style="DF")
        pdf.set_xy(PAGE_WIDTH - MARGIN - 29, hero_y + 6.0)
        pdf.set_font(FONT_NAME, "", 5.8)
        pdf.set_text_color(*MUTED)
        pdf.cell(20, 3.0, "RTLP SCORE", align="C")
        pdf.set_xy(PAGE_WIDTH - MARGIN - 29, hero_y + 10.2)
        pdf.set_font(FONT_NAME, "", 13)
        pdf.set_text_color(*ACCENT_COLOR)
        pdf.cell(20, 5.5, f"{r_score:.2f}", align="C")
        pdf.set_xy(PAGE_WIDTH - MARGIN - 29, hero_y + 16.0)
        pdf.set_font(FONT_NAME, "", 5.6)
        pdf.set_text_color(*MUTED)
        pdf.cell(20, 3.0, f"{yes_count}/9 levers", align="C")

        pdf.set_xy(MARGIN + 6, hero_y + 18.3)
        pdf.set_font(FONT_NAME, "", 7.7)
        pdf.set_text_color(*MUTED)
        flag_text = f" | Flag code: {iso2}" if iso2 else ""
        pdf.cell(0, 4, f"{d.get('un_region', 'N/A')} | V-Dem {d['vdem_year']} | GDP baseline {d['g0_year']}{flag_text}")

        strip_x = MARGIN + 6
        strip_y = hero_y + 25.4
        box_w = 9.2
        for comp_idx, comp in enumerate(d["components"]):
            x = strip_x + comp_idx * (box_w + 1.6)
            is_yes = comp.get("bin", 0) == 1
            pdf.set_fill_color(*(YES_COLOR if is_yes else NO_COLOR))
            pdf.set_draw_color(255, 255, 255)
            pdf.rect(x, strip_y, box_w, 5.0, style="DF")
            pdf.set_xy(x, strip_y + 1.0)
            pdf.set_font(FONT_NAME, "", 5.4)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(box_w, 2.5, str(comp_idx + 1), align="C")
        pdf.set_xy(strip_x + 9 * (box_w + 1.6) + 2.5, strip_y + .3)
        pdf.set_font(FONT_NAME, "", 6.0)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 3.4, "Nine RTLP levers: green present, red absent")

        pdf.set_y(hero_y + hero_h + 4)

        metric_y = pdf.get_y()
        metric_w = (CONTENT_WIDTH - 9) / 4
        pdf.metric_card(MARGIN, metric_y, metric_w, 22, "GDP per capita G0", f"${g0:,.0f}")
        pdf.metric_card(MARGIN + metric_w + 3, metric_y, metric_w, 22, "Capital exclusions / cap", f"${dpc:,.0f}", fill=PANEL_ALT)
        pdf.metric_card(MARGIN + (metric_w + 3) * 2, metric_y, metric_w, 22, "Capital exclusions", format_money(tot))
        pdf.metric_card(MARGIN + (metric_w + 3) * 3, metric_y, metric_w, 22, "Population", pop_str)
        pdf.set_y(metric_y + 25)
        trend_y = pdf.get_y()
        pdf.set_fill_color(*PANEL_BG)
        pdf.set_draw_color(*RULE)
        pdf.rect(MARGIN, trend_y, CONTENT_WIDTH, 16, style="DF")
        pdf.set_xy(MARGIN + 2.5, trend_y + 2)
        pdf.set_font(FONT_NAME, "", 6.8)
        pdf.set_text_color(*INK)
        pdf.multi_cell(CONTENT_WIDTH - 5, 3.1, trend_text)
        pdf.set_y(trend_y + 18)

        country_map = get_nation_country_map(d["iso3"], d["country"], d.get("r"))
        if country_map and country_map.exists():
            pdf.set_font(FONT_NAME, "", 6.8)
            pdf.set_text_color(*HEADER_COLOR)
            pdf.cell(0, 3.2, "Country View — Enclosure Strength (R)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            y_map = pdf.get_y()
            map_w = CONTENT_WIDTH - 60
            map_h = map_w * (180 / 380)
            pdf.image(str(country_map), x=MARGIN + 30, y=y_map, w=map_w, h=map_h)
            pdf.set_y(y_map + map_h + 1)
            pdf.set_font(FONT_NAME, "", 5)
            pdf.set_text_color(95, 95, 95)
            pdf.multi_cell(0, 2.1, "Country-only local view fitted to the national boundary; no regional comparison map is used on nation pages.")
            pdf.ln(0.3)

        pdf.ln(0.5)
        pdf.section_label("Nine-lever RTLDI display", HEADER_COLOR)
        pdf.ln(1.0)

        card_gap = 3
        row_gap = 2.0
        card_cols = 2
        card_w = (CONTENT_WIDTH - card_gap) / card_cols
        card_h = 18.8
        grid_y = pdf.get_y()

        for idx, c in enumerate(d["components"]):
            col = idx % card_cols
            row = idx // card_cols
            x = MARGIN + col * (card_w + card_gap)
            y = grid_y + row * (card_h + row_gap)
            yes = c["yes"]
            is_yes = yes == "Yes"
            name = lever_name(c["num"], c["name"])
            desc = lever_description(c["num"], c["desc"])
            raw_str = str(c["raw"])[:42] if c["raw"] is not None else "N/A"

            fill = (244, 251, 247) if is_yes else (255, 247, 247)
            accent = YES_COLOR if is_yes else NO_COLOR
            pdf.set_fill_color(*fill)
            pdf.set_draw_color(*RULE)
            pdf.rect(x, y, card_w, card_h, style="DF")
            pdf.set_fill_color(*accent)
            pdf.rect(x, y, 1.7, card_h, style="F")

            pdf.set_xy(x + 3, y + 2)
            pdf.set_font(FONT_NAME, "", 6.2)
            pdf.set_text_color(*ACCENT_COLOR)
            pdf.cell(card_w - 6, 2.8, f"Lever {c['num']}", new_x=XPos.RIGHT, new_y=YPos.TOP)

            badge_w = 11
            pdf.set_xy(x + card_w - badge_w - 2.2, y + 1.8)
            pdf.set_font(FONT_NAME, "", 5.9)
            pdf.set_text_color(*accent)
            pdf.cell(badge_w, 3.2, yes.upper(), border=1, align="C")

            pdf.set_xy(x + 3, y + 5.2)
            pdf.set_font(FONT_NAME, "", 7.0)
            pdf.set_text_color(*INK)
            pdf.multi_cell(card_w - badge_w - 7, 3.0, name, align="L")

            pdf.set_xy(x + 3, y + 10.7)
            pdf.set_font(FONT_NAME, "", 6.2)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(card_w - 6, 2.7, desc, align="L")

            pdf.set_xy(x + 3, y + card_h - 4.0)
            pdf.set_font(FONT_NAME, "", 5.8)
            pdf.set_text_color(90, 100, 108)
            pdf.cell(card_w - 6, 2.4, f"raw: {raw_str}")

        rows_used = math.ceil(len(d["components"]) / card_cols)
        pdf.set_y(grid_y + rows_used * (card_h + row_gap) - row_gap + 2.0)
        pdf.set_font(FONT_NAME, "", 6.0)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 2.8,
            "Note: [Yes] = contributes +1 to R. Raw = V-Dem/WB value (higher=stronger protection). Thresholds in Methodology. Partial coverage possible for some nations. "
            "See the Economic Intelligence section for how to use your R and component scores as a tool to identify opportunities for greater scale."
        )

    out_path = Path(NATIONS_PDF)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(out_path)
    print(f"Nations PDF written to: {out_path}  ({pdf.page_no()} pages)")
    return out_path


def build_back_matter(data: dict) -> Path:
    """Build the back matter PDF (attribution, alphabetical index of terms, credits).
    Safe to iterate on without touching the 193 nation pages.
    """
    pdf = RTLDIAtlasPDF()
    detailed_all = data["detailed_all"]

    # The preceding Eurozone module ends on a recto; preserve the Part V recto opening.
    pdf.add_chromeless_page()
    draw_section_opener(
        pdf,
        part="Part V",
        title="Evidence, Data, and Project Record",
        subtitle="The methods, sources, rights, and production record required to inspect and reproduce the Atlas.",
        facts=[
            ("Crosswalk", "Nine fields, thresholds, proxies, caveats, and allocations"),
            ("Regression", "Specification, robust uncertainty, comparators, and growth check"),
            ("Provenance", "Exact V-Dem artifact, checksum, and World Bank indicators"),
            ("Publication record", "Ownership, citation, license, source access, glossary, and colophon"),
        ],
    )

    # ========== DATA ATTRIBUTION ==========
    pdf.add_page()
    pdf.chapter_title("Data Attribution and Source Ownership")
    pdf.body_text(
        "Primary Data\n"
        "• V-Dem (Varieties of Democracy) Country-Year Core, version 15, using 2024 country-year observations. "
        "Released component fields: v2cltrnslw, v2juhcind, v2juncind, v2clkill, v2xcl_acjst, v2cltort, v2x_clphy, v2clrspct, and v2x_freexp. Each of the eight V-Dem levers has a distinct operational field or field composite; World Bank indicators supply lever 9.\n"
        "• World Bank World Development Indicators (WDI) via API — GDP per capita (current US$), "
        "population, prevalence of undernourishment, and poverty headcount at $2.15 (2017 PPP). "
        "Values are the most recent published as of atlas production (labeled 2026 baseline).\n"
        "• United Nations Member States list for the 193-country publication scope; repository ISO tables provide operational codes and regional grouping.\n\n"
        "Field-level ownership\n"
        "V-Dem is credited for its institutional measurements. The World Bank is credited for GDP, population, undernourishment, and poverty observations. RTLP scores, RTLDI values, lever classifications, potential-GDP and capital-exclusion estimates, rankings, maps, narratives, and generated data products are attributable to the RTLDI Atlas Project.\n\n"
        "Source Framework\n"
        "The RTLDI equation and the nine RTLP indicators are taken from:\n"
        "Sid J.A. Hubbard, Causality and Attraction: A Continuum of Steady States (Version 3, May 2026), "
        "DOI: 10.5281/zenodo.19468550. The operational crosswalk and binarization thresholds used here "
        "are documented in docs/indicator_crosswalk.md of this project."
    )
    pdf.small_text(
        "This PDF was generated programmatically from the open RTLDI ATLAS toolkit. "
        "No proprietary or restricted source data were used. V-Dem and World Bank remain the authoritative sources for their observations."
    )

    # ========== REPOSITORY / ATLAS SUITE ==========
    pdf.add_page()
    pdf.chapter_title("RTLDI Atlas Suite and Public Repository")
    pdf.body_text(
        "This PDF atlas was produced by the RTLDI Atlas Suite, the open repository that contains the "
        "canonical data crosswalks, Python build pipeline, choropleth map generation, PDF ebook generator, "
        "and self-contained HTML atlas generator used for the public release.\n\n"
        "Users of this atlas are invited to download the RTLDI Atlas Suite and reproduce the published "
        "RTLP scores and RTLDI capital-exclusion projections directly from the public-release V-Dem and "
        "World Bank datasets. The suite is designed so NGOs, researchers, policymakers, analysts, and "
        "investors can rerun the atlas as new public data releases become available."
    )
    draw_mini_link(pdf, label="RTLDI Atlas public repository", url=REPOSITORY_URL, slug="suite-repository")
    pdf.body_text(
        "The same tools can also be used to generate an RTLDI Atlas from proprietary, internal, or field "
        "data. The implementation separates the conceptual nine-lever RTLDI model from the data crosswalk: "
        "if an organization has its own trusted country, regional, sectoral, or subnational indicators, it "
        "can map those fields into the required nine binary RTLP components and then use the existing suite "
        "to compute R, per-capita ΔG, total capital exclusions, lever-level attribution, regional summaries, "
        "maps, spreadsheets, PDF reports, and HTML outputs."
    )
    pdf.body_text(
        "For public-data runs, use the documented V-Dem and World Bank workflow. For proprietary-data runs, "
        "implement a clear data crosswalk, preserve the nine RTLP component meanings, document all thresholds, "
        "and keep the output labels tied to the same canonical RTLDI equation. This keeps forks comparable "
        "while allowing local datasets to improve coverage, timeliness, or granularity."
    )
    pdf.small_text(
        "The official public atlas has one canonical pipeline: src.build_atlas produces the master atlas table; "
        "src.generate_atlas_ebook.prepare_atlas_data() prepares the shared print/web data; and the PDF/HTML "
        "generators consume that same prepared data. Forks should preserve this single-pipeline discipline or "
        "clearly identify themselves as experimental derivatives."
    )

    # ========== EVIDENCE ROADMAP ==========
    pdf.add_page()
    pdf.chapter_title("Evidence and Transparency Roadmap")

    pdf.body_text(
        "The pages that follow mirror the web atlas's methods and source views. Each lever page states the RTLP question, source field, threshold, operational proxy, caveat, and global bounded allocation. Regression pages report specification, robust uncertainty, statistical significance, comparators, and a non-significant one-year growth check. Dataset pages identify the exact V-Dem artifact and World Bank indicators used for reproduction.\n\n"
        "This evidence should be read with the interpretation limits in Part I. Lever-level allocations partition a bounded national total; they are not independent causal estimates. Cross-sectional significance does not establish a reform counterfactual."
    )

    evidence = evidence_bundle(data)

    # ========== LEVER TRANSPARENCY ==========
    pdf.add_page()
    pdf.chapter_title("The Nine Levers: Executable Crosswalk")
    pdf.body_text(
        "This section mirrors the web atlas lever pages. It reports the global annual capital exclusions "
        "attributed to each lever and the exact fields and thresholds used by the executable 2026 pipeline. "
        "The lever amounts allocate each country's bounded total across its missing components; they are not "
        "nine independent causal estimates and should not be summed without the shared cap."
    )
    for num in range(1, 10):
        meta = LEVER_DISPLAY[num]
        cross = LEVER_CROSSWALK[num]
        pdf.add_page()
        pdf.section_label(f"Lever {num} of 9", HEADER_COLOR)
        pdf.chapter_title(meta["name"])
        pdf.set_font(FONT_NAME, "", 17)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.cell(0, 9, f"{format_compact_usd(evidence['lever_totals'].get(num, 0))} global annual exclusions", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        pdf.body_text(meta["long_description"])
        pdf.section_label("RTLP question", HEADER_COLOR)
        pdf.body_text(cross["question"])
        pdf.section_label("Fields and scoring rule", HEADER_COLOR)
        pdf.body_text(
            f"Source: {cross['source']}\n"
            f"Field(s): {', '.join(cross['fields'])}\n"
            f"Binary rule: {cross['transform']}\n"
            f"Operational proxy: {cross['proxy']}"
        )
        pdf.set_fill_color(255, 249, 239)
        pdf.set_draw_color(224, 193, 142)
        note_y = pdf.get_y() + 2
        pdf.rect(MARGIN, note_y, CONTENT_WIDTH, 30, style="DF")
        pdf.set_xy(MARGIN + 4, note_y + 4)
        pdf.set_font(FONT_NAME, "", 8.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(CONTENT_WIDTH - 8, 4.3, "Transparency note: " + cross["caveat"])

    # ========== REGRESSION EVIDENCE ==========
    reg = evidence["regression"]
    main_reg = reg["main"]
    pdf.add_page()
    pdf.chapter_title("GDP Regression, Significance, and Eta")
    pdf.body_text(
        "The canonical atlas model is a population-weighted cross-sectional regression of log GDP per "
        "capita on activated-lever count. It estimates association with the level of GDP per capita, not a "
        "causal time-series growth effect."
    )
    y = pdf.get_y() + 2
    w = (CONTENT_WIDTH - 6) / 3
    pdf.metric_card(MARGIN, y, w, 26, "Eta", f"{main_reg['eta']:.3f}", "exp(beta) - 1", PANEL_ALT)
    pdf.metric_card(MARGIN + w + 3, y, w, 26, "95% robust interval", f"{main_reg['ci_low']:.1%} to {main_reg['ci_high']:.1%}", f"n = {main_reg['n']}")
    pdf.metric_card(MARGIN + (w + 3) * 2, y, w, 26, "Model fit", f"R2 {main_reg['r2']:.3f}", f"p = {main_reg['p']:.3g}")
    pdf.set_y(y + 31)
    pdf.body_text(
        f"Specification: log(GDP per capita) = intercept + beta x activated-lever count + error. "
        f"The fitted log slope is {main_reg['slope']:.3f} with robust standard error {main_reg['se']:.3f}. "
        f"Eta is exp(beta)-1 = {main_reg['eta']:.3f}; the operational atlas rounds this to 0.36 and applies "
        "Delta G = min(eta x (1-R) x G0, 0.25 x G0)."
    )
    pdf.section_label("Interpretation limit", HEADER_COLOR)
    pdf.body_text(
        "Statistical significance is not causal identification. Omitted variables, reverse causation, proxy "
        "validity, binary thresholds, and source-year mismatch remain. The 25% cap limits attribution but does "
        "not resolve those identification problems."
    )

    pdf.add_page()
    pdf.chapter_title("Regression Comparators and Growth Check")
    cols = [53, 15, 25, 20, 20]
    headers = ["Single predictor", "n", "Slope", "R2", "p"]
    pdf.set_font(FONT_NAME, "", 7.5)
    pdf.set_fill_color(*HEADER_COLOR)
    pdf.set_text_color(255, 255, 255)
    for width, header in zip(cols, headers):
        pdf.cell(width, 5, header, border=1, fill=True, align="C")
    pdf.ln()
    for item in reg["comparators"]:
        values = [item["label"], str(item["n"]), f"{item['slope']:.3f}", f"{item['r2']:.3f}", f"{item['p']:.3g}"]
        pdf.set_text_color(*INK)
        for i, (width, value) in enumerate(zip(cols, values)):
            pdf.cell(width, 5, value, border=1, align="L" if i == 0 else "R")
        pdf.ln()
    pdf.ln(4)
    growth = reg["growth"]
    if growth:
        pdf.body_text(
            f"Available growth falsification check: 2023-2024 current-US$ GDP-per-capita change on lever "
            f"count, unweighted OLS. n={growth['n']}; slope={growth['slope']:.3f} percentage points per lever; "
            f"R2={growth['r2']:.3f}; p={growth['p']:.3g}. This one-year check is not statistically significant. "
            "The atlas therefore describes a cross-sectional GDP-level association and does not claim that "
            "the nine levers predict one-year GDP growth."
        )
    pdf.small_text(
        "Comparator models are descriptive single-predictor checks. Undernourishment and poverty are development "
        "outcomes and inputs to lever 9, not independent causal controls; missing data change their sample sizes."
    )

    # ========== DATASET PAGES ==========
    pdf.add_page()
    pdf.chapter_title("V-Dem Dataset and Reproduction")
    pdf.body_text(
        "The corrected 2026 score table uses V-Dem Country-Year Core v15 and 2024 country-year observations. "
        "The current update workflow targets Country-Year Core v16. The repository does not redistribute the "
        "large raw source artifact.\n\n"
        "SHA-256 for the exact v15 artifact: 4b715190a1e351a81daf11cbe6f9f77e67d8914f0ed612b93e2d8fba5523e540\n\n"
        "For exact replication, download the v15 artifact identified above and export the required columns as "
        "data/raw/V-Dem-CY-Core-v15.csv. For a current-data update, download Core v16, then run "
        "python3 -m src.build_atlas --year 2026 --eta 0.36."
    )
    draw_mini_link(pdf, label="Official V-Dem v15 archive", url=VDEM_ARCHIVE_URL, slug="vdem-v15-archive")
    draw_mini_link(pdf, label="Exact V-Dem v15 artifact", url=VDEM_V15_SOURCE_URL, slug="vdem-v15-artifact")
    draw_mini_link(pdf, label="Current V-Dem dataset", url=VDEM_DATASET_URL, slug="vdem-current")
    draw_mini_link(pdf, label="V-Dem v16 codebook", url=VDEM_CODEBOOK_URL, slug="vdem-v16-codebook")
    pdf.body_text(
        "V-Dem's unsuffixed expert-coded fields are measurement-model point estimates on a standardized interval "
        "scale, not the original ordinal coder categories. The atlas cutoffs are project operationalizations. "
        "A v16 rebuild may revise historical scores and is therefore an update rather than guaranteed bit-for-bit "
        "replication. The URL and checksum above identify the exact official v15 artifact used by this build."
    )

    pdf.add_page()
    pdf.chapter_title("World Bank Dataset and Reproduction")
    pdf.body_text(
        "World Development Indicators supply NY.GDP.PCAP.CD (GDP per capita, current US$), SP.POP.TOTL "
        "(population), SN.ITK.DEFC.ZS (undernourishment), and SI.POV.DDAY (international-poverty headcount). "
        "GDP is G0 and the regression outcome; population is the regression weight and aggregation factor; the "
        "last two fields populate lever 9.\n\n"
        "The pipeline fetches the public API through wbgapi and stores processed snapshots under data/processed/."
    )
    draw_mini_link(pdf, label="World Bank Data portal", url=WORLD_BANK_DATA_URL, slug="world-bank-data")
    draw_mini_link(pdf, label="World Bank public API", url=WORLD_BANK_API_URL, slug="world-bank-api")
    pdf.body_text(
        "The 2026 baseline is the freshest published value available at build time, not a claim that every value "
        "was observed in 2026. Missing undernourishment or poverty is conservatively scored as lever 9 absent. "
        "Current-US$ GDP supports current-dollar totals but also reflects price-level and exchange-rate movement."
    )

    pdf.add_page()
    pdf.chapter_title("Citation, Licensing, and Reuse")
    pdf.section_label("Cite Atlas outputs")
    pdf.body_text(
        "RTLDI Atlas Project. (2026). RTLDI Atlas of UN Member States [Data set, software, and atlas]. "
        "Sid J.A. Hubbard, Principal Investigator."
    )
    draw_mini_link(pdf, label="Atlas repository", url=REPOSITORY_URL, slug="citation-repository")
    pdf.section_label("Cite the source theory")
    pdf.body_text(
        "Hubbard, Sid J.A. (2026). Causality and Attraction: A Continuum of Steady States, Volume I, "
        "Version 3."
    )
    draw_mini_link(pdf, label="Source theory DOI", url="https://doi.org/10.5281/zenodo.19468550", slug="citation-doi")
    pdf.section_label("Cite source observations")
    pdf.body_text(
        "For institutional observations, cite the V-Dem Institute and the v15 dataset/codebook appropriate to "
        "the observation. For GDP, population, undernourishment, and poverty observations, cite the relevant "
        "World Development Indicators series and access date. Do not attribute RTLDI Project transformations "
        "or projections to V-Dem or the World Bank."
    )
    pdf.section_label("License boundary")
    pdf.body_text(
        "Atlas repository materials are available under the MIT License. Preserve the copyright and license notice when "
        "redistributing licensed materials. The source books and theoretical framework retain their separately "
        "stated rights."
    )
    draw_mini_link(pdf, label="MIT License", url="https://github.com/SJAH9/rtldi-atlas/blob/main/LICENSE", slug="citation-license")

    # Preserve a recto opening for the glossary/source-access title in the full volume.
    pdf.add_chromeless_page()
    draw_qr_gateway(
        pdf,
        title="Glossary and Source Access",
        subtitle="Definitions for the Atlas, with direct access to the executable crosswalk, source code, canonical records, and reproduction commands.",
        url=REPOSITORY_URL,
        slug="source-code-and-data",
        kicker="Part V / Reference",
        note="The glossary follows this title page. Scan to inspect the code and project-generated data; V-Dem and World Bank remain authoritative for their observations.",
    )

    # ========== NEW: FALSIFICATION OF MALTHUS (streamlined from source) ==========
    # pdf.add_page()
    # pdf.chapter_title("Falsification of Malthusian Scarcity")

    # pdf.body_text(
    #    "Thomas Malthus argued that population grows exponentially while resources grow linearly, leading to famine and checks on population unless growth is deliberately limited."
    # )

    # pdf.body_text(
    #    "The conditions Malthus projected are true when nations do not equally protect the lives of all people within their borders: more people then equate to less available resource per person. But when the right to life is equally protected, GDP rises for multiple reasons and rises exponentially because societal stresses are distributed evenly among a more productive and more capable society."
  #  )

   # pdf.body_text(
   #     "The levers make this possible at low annual cost. Freedom from torture, freedom from arbitrary detention, and an independent judiciary together make a nation investible — businesses and startups form when the risk of death or arbitrary imprisonment does not stop capital from flowing in. Whistleblower protections allow corruption and theft to be exposed at scales previously unknown. Most of the nine levers have minimal annual cost; they are force multipliers of economic velocity."
  #  )

   # pdf.body_text(
   #     "The important distinction is that this analysis does not negate the efficacy of Malthusian regimes. A nation can choose the Malthusian relationship to its population and receive the expected constraints on per-capita resources, or it can activate more of the nine levers and enjoy the scaling benefits of an optimized institutional environment. The opportunity to realize greater economic scale through these levers is now visible in the data."
  #  )

    # ========== GLOSSARY ==========
    pdf.add_page()
    pdf.chapter_title("Glossary of Terms")

    terms = [
        ("ΔG (delta G)", "Annual per-capita capital exclusions (lost potential GDP) associated with the current level of the nine levers. Core output of the RTLDI equation."),
        ("G₀ (G-zero)", "Baseline GDP per capita (World Bank, current US$). The 'current' economic size against which capital exclusions are measured."),
        ("R (RTLP score)", "The arithmetic mean (0–1) of the nine binary Right-to-Life Protection lever values. R=1 means all nine operational thresholds are met."),
        ("RTLP", "Right-to-Life Protection. In the Atlas, RTLP refers to the nine-component protection score R and its component classifications."),
        ("RTLDI", "Right to Life Deficit Index — the source framework operationalized here to report RTLP scores and bounded capital-exclusion estimates."),
        ("The Nine Levers", "The nine conceptual protections averaged to produce R. Each is populated by a distinct operational field or field composite in the corrected pipeline."),
        ("V-Dem", "Varieties of Democracy project. Supplies the expert-coded governance and civil liberties indicators for eight of the nine RTLP components."),
        ("Crosswalk", "The explicit mapping from the nine verbatim RTLP questions to observable V-Dem variables and World Bank statistics, with defined binarization thresholds."),
        ("2026-fresh G0", "The most recent published GDP per capita values used as the dynamic baseline for the 2026 edition (even when RTLP components are from 2024)."),
        ("Mollweide", "Equal-area pseudocylindrical map projection used for global and regional choropleths. Nation profiles use fitted country views for legibility."),
        ("Choropleth", "Thematic map in which countries or regions are shaded by enclosure strength R (0–1) using the RTLDI atlas scale; primary visual for the global, regional, and focus views."),
        ("Economic Intelligence (tool)", "The use of R scores, component breakdowns, and attributable capital exclusions figures as practical information for governments, businesses, and analysts to identify high-leverage institutional opportunities."),
        ("Trend (up to 3 years)", "A text summary of available GDP-driven projection points with R held fixed at its latest V-Dem value. It is not a measured RTLP time series."),
        ("Attributable capital exclusions", f"The allocation of a country or region's bounded total across missing levers, using η/9 × G₀ × population and each country's cap ratio. Current operational η={ETA:.2f}. These allocations are not independent causal estimates."),
        ("Enclosure (nested causal / human)", "The source document's central metaphor: the interdependent, layered structures of protection whose strength or weakness shapes higher-order economic and social steady states."),
        ("Causality and Attraction", "The source monograph (Hubbard 2026V3, Zenodo 19468550) that supplies the RTLDI equation, the nine RTLP indicators, the nested-enclosures paradigm, and the cartographic critique of distortion. This atlas extends the source RTLDI to quantify capital exclusions."),
        ("Binarization / threshold", "The documented conversion of continuous V-Dem and World Bank values into the binary 0/1 scores for the nine indicators (e.g., ≥2.0 on 0-4 scales, ≤5 % undernourishment + ≤10 % poverty for #9)."),
        ("η (eta)", "The sensitivity coefficient (current data-driven default 0.36 from the corrected population-weighted 2026 UN cross-section). In the bounded model ΔG = min(η(1 − R) × G₀, 0.25 × G₀); the cross-sectional premium per indicator, then capped so the nine RTLP indicators are never credited with more than 25% of observed G₀ after other determinants are given due weight. (Source document used a more conservative 0.05 structural value.)"),
        ("Steady state", "A balanced biological, economic, or social condition that the framework argues is supported or undermined by the strength of the nine life protections and the resulting causal enclosures."),
   #     ("Malthusian theory","The proposition (Thomas Malthus) that population grows exponentially while resources grow linearly, inevitably producing scarcity and misery unless population is checked. The source and this atlas present geometric and empirical counter-evidence under conditions of equal right-to-life protection. There is no evidence of high population leading to lower GDP per capita. Strong corollary across many data sets links population and GDP suggesting resource development may be a direct consequence of population growth and greater economic capacity."),

        ("UN region / regional summary", "One of the 22 geographic groupings used for aggregates, focused choropleths, member-nations tables (with R / G0 / population / capital exclusions + REGIONAL TOTAL row), and 9-lever breakdowns."),
        ("Member-nations table", "The compact table on each regional summary page that lists every country in the region together with its R, G0, population, and capital exclusions, plus a bottom row of regional totals."),
        ("RTLDI atlas R scale", "The shared perceptual color scale used for every enclosure-strength choropleth in the atlas: deep low-R tones through teal midrange values to warm high-R values."),
        ("Country view", "The country-only choropleth on each nation page, fitted to the national boundary and shaded by enclosure strength R without using the regional context map."),
        ("Capital exclusion", "The Atlas term for bounded lost potential GDP associated with missing RTLP protections under the stated cross-sectional model. It is an estimate, not observed money or a guaranteed reform dividend."),
        ("Contextual cap", "The rule limiting projected capital exclusions to 25% of G₀ so the nine protections are not assigned more than one quarter of observed GDP. The cap limits attribution but does not establish causality."),
        ("Cross-sectional association", "A relationship measured across countries at one analytical period. It can be statistically significant without showing that changing one variable will cause the other to change."),
        ("Causal projection", "A projection of how changing an enclosure alters the set of reachable outcomes. It identifies an enabled or disabled pathway without guaranteeing the timing, magnitude, or realization of a particular response."),
        ("Feasible set", "The outcomes and actions that remain institutionally possible under the current enclosures. Activating a lever can add pathways to this set without forcing actors to use them immediately."),
        ("Institutional option value", "The value created when an effective protection makes a beneficial action or remedy available. Availability can be established by the protection even when the eventual uptake and financial return remain uncertain."),
        ("Outer enclosure", "A legal, institutional, or social boundary that protects and constrains actions inside a modeled system. In the whistleblower example, credible protection surrounds the reporting pathway and changes what insiders can safely do."),
        ("Full Data View", "The web table exposing one record per UN Member State with RTLP, lever, GDP, population, potential-GDP, and capital-exclusion fields."),
        ("Linked open data", "Atlas data published in RDF/XML with stable concepts and relationships so machines can consume and connect the observations semantically."),
        ("Operational proxy", "An available measured field used to represent a conceptual lever when no source variable directly measures the full RTLP question."),
        ("Provenance", "The documented origin, version, transformation path, and checksum needed to understand or reproduce a data product."),
        ("Robust standard error", "An uncertainty estimate designed to remain valid under heteroskedastic regression residuals; used in the Atlas regression interval and significance test."),
        ("Source ownership", "The attribution boundary separating V-Dem and World Bank observations from RTLDI Atlas Project classifications, transformations, projections, maps, and narratives."),
        ("Weighted seven-signal equivalence", "The algebraic rewriting of the former duplicated-proxy nine-row score as seven unique signals while retaining two-ninths weights for the two repeated pairs. It is not an unweighted seven-variable model."),
        ("AI-assisted production", "The disclosed use of AI and data-science tools in research, software development, analysis, validation, and publication under the direction and responsibility of the Principal Investigator."),
        ("DOI", "Digital Object Identifier: a persistent identifier for a publication. The Atlas source framework is identified by doi:10.5281/zenodo.19468550."),
        ("MIT License", "The permissive open-source license governing Atlas repository code, pipeline, documentation, and generated outputs. It does not relicense the source books or theoretical framework."),
        ("p-value", "The probability, under the fitted null model, of observing a test statistic at least as extreme as the one reported. It is not the probability that the model is true or causal."),
        ("Population weighting", "Regression or aggregation weights proportional to national population, so the fitted relationship or mean reflects people rather than treating every country as equally sized."),
        ("QR gateway", "A full-page print-to-digital bridge containing a high-redundancy QR symbol and its visible destination URL. The URL remains usable without QR scanning."),
        ("R-squared (R2)", "The share of outcome variation described by a fitted regression in its sample. It is a model-fit statistic, not evidence of causality."),
    ]

    if detailed_all and "components" in detailed_all[0]:
        for comp in detailed_all[0]["components"]:
            name = comp.get("name", "")
            desc = comp.get("desc", "One of the nine binary RTLP indicators averaged to produce the RTLP score R.")
            if name:
                terms.append((name, desc))

    indicator_subterms = [
        ("Arbitrary Detention", "Core protection against state overreach (RTLP indicator #4); current implementation level contributes to associated capital exclusions in regions."),
        ("Torture and Inhumane Treatment", "RTLP indicator #5; one of the larger contributors to global capital exclusions, highlighting physical integrity protections."),
        ("Independent Judiciary", "RTLP indicator #2; essential for enforcing all other protections and a frequent point of regional failure."),
        ("Socioeconomic Conditions", "RTLP indicator #9; combines World Bank undernourishment and poverty data; measures structural ability to sustain life."),
        ("Freedom of Expression and Whistleblower Protections", "RTLP indicator #8; critical for exposing violations and one of the lower-loss (stronger) areas globally."),
        ("Civilian Protection in Conflict Zones", "RTLP indicator #6; focuses on mechanisms during armed conflict or high-violence periods."),
        ("Law Enforcement Accountability", "RTLP indicator #3; addresses whether agencies and leaders are held responsible for unlawful killings."),
        ("Access to Justice", "RTLP indicator #7; ensures individuals can seek remedies for rights violations."),
        ("Existence of Legal Protections", "RTLP indicator #1; the foundational de-jure and de-facto right to life."),
        ("Right to Life", "The overarching protected interest; the nine indicators operationalize equal and effective protection against arbitrary interruption."),
    ]
    terms.extend(indicator_subterms)

    seen = set()
    unique = []
    for t in terms:
        key = t[0].lower()
        if key not in seen:
            seen.add(key)
            unique.append(t)
    terms = unique

    terms = sorted(terms, key=lambda x: x[0].lower()
                   .replace("δ", "d")
                   .replace("η", "eta")
                   .replace("₀", "0")
                   .replace("g₀", "g0"))

    pdf.set_font(FONT_NAME, "", 8)
    for term, definition in terms:
        pdf.set_font(FONT_NAME, "", 8)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.multi_cell(0, 4, term + ":")
        pdf.set_font(FONT_NAME, "", 8)
        pdf.set_text_color(*BLACK)
        pdf.set_x(MARGIN + 5)
        pdf.multi_cell(0, 4, definition)
        pdf.ln(1)
        pdf.set_x(MARGIN)

    # ========== CREDITS ==========
    pdf.add_page()
    pdf.chapter_title("Credits and Acknowledgments")
    pdf.body_text(
        "Principal Investigator and Production\n"
        "Sid J.A. Hubbard conceived, wrote, directed, and engineered the RTLDI Atlas Project and is responsible "
        "for its methods, crosswalk decisions, interpretation, software direction, and publication. The project "
        "was produced with assistance from multiple AI and data-science tools under the production disclosure stated in Part I.\n\n"
        "Conceptual Framework\n"
        "Causality and Attraction: A Continuum of Steady States, Volume I, Version 3 — Sid J.A. Hubbard.\n\n"
        "Institutional Data\n"
        f"V-Dem Institute — Country-Year Core v15, 2024 observations. SHA-256 {VDEM_V15_SHA256}.\n\n"
        "Economic and Population Data\n"
        "World Bank World Development Indicators through the public API.\n\n"
        "Country Scope\n"
        "United Nations Member States."
    )
    draw_mini_link(pdf, label="Conceptual framework DOI", url="https://doi.org/10.5281/zenodo.19468550", slug="credits-framework")
    draw_mini_link(pdf, label="Exact V-Dem v15 artifact", url=VDEM_V15_SOURCE_URL, slug="credits-vdem-artifact")
    draw_mini_link(pdf, label="V-Dem Institute", url="https://www.v-dem.net/", slug="credits-vdem")
    draw_mini_link(pdf, label="World Bank Data", url=WORLD_BANK_DATA_URL, slug="credits-world-bank")
    draw_mini_link(pdf, label="World Bank API", url=WORLD_BANK_API_URL, slug="credits-world-bank-api")
    draw_mini_link(pdf, label="United Nations Member States", url="https://www.un.org/en/about-us/member-states", slug="credits-un")
    pdf.section_label("Open-source production stack")
    pdf.body_text(
        "Python, pandas, NumPy, SciPy, Plotly, Kaleido, fpdf2, PyPDF2, Pillow, qrcode, openpyxl, and wbgapi. "
        "Plotly's geographic rendering uses public map geometry derived from established open cartographic sources, "
        "including Natural Earth. Each project retains its own license and attribution requirements."
    )

    pdf.add_page()
    pdf.chapter_title("Colophon and Print Specification")
    pdf.body_text(
        "Format\n"
        "A4 portrait (210 × 297 mm), designed without required bleed. All essential text, QR quiet zones, maps, "
        "folios, and rules remain inside the trim safety area. Section gateways and covers use white trim edges so "
        "the file can be printed without edge-to-edge finishing.\n\n"
        "Typography and graphics\n"
        "Unicode-capable TrueType fonts are embedded by the PDF generator. Global and regional maps are rendered "
        "from the canonical atlas data; QR symbols are generated at high resolution with error-correction level H. "
        "Rules and text remain vector content.\n\n"
        "Assembly\n"
        "The publication is generated as modular front, regional, nation, Eurozone, and evidence PDFs, then "
        "assembled in canonical order. Final processing adds continuous physical folios, document metadata, a "
        "two-page reading layout preference, and PDF outline navigation.\n\n"
        "Production note\n"
        "This general-purpose print file uses a device-independent digital workflow suitable for office, digital, "
        "and print-on-demand production. A commercial offset printer may apply its required CMYK output intent, "
        "paper profile, imposition, and trapping during prepress."
    )
    draw_mini_link(pdf, label="Repository", url=REPOSITORY_URL, slug="colophon-repository")
    draw_mini_link(pdf, label="Web Atlas", url=WEB_ATLAS_URL, slug="colophon-web")
    draw_mini_link(pdf, label="Interactive map", url=INTERACTIVE_MAP_URL, slug="colophon-map")
    draw_mini_link(pdf, label="Full Data View", url=FULL_DATA_URL, slug="colophon-data")

    out_path = Path(BACK_PDF)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(out_path)
    print(f"Back matter PDF written to: {out_path}  ({pdf.page_no()} pages)")
    return out_path


def _finalize_print_pdf(assembled: Path, out: Path) -> Path:
    """Apply continuous folios, metadata, duplex layout, and outline navigation."""
    reader = PdfReader(str(assembled))
    page_text = [(page.extract_text() or "") for page in reader.pages]
    total_pages = len(reader.pages)

    overlay_path = out.with_name(out.stem + "_folios.pdf")
    overlay = FPDF(format="A4", unit="mm")
    overlay.add_font(FONT_NAME, "", FONT_PATH)
    overlay.set_auto_page_break(False)
    for index, text in enumerate(page_text):
        overlay.add_page()
        suppress = (
            index == 0
            or not text.strip()
            or "Scan with a phone camera" in text
            or "RTLDI 2026 Eurozone Capital Exclusion Map" in text
        )
        if suppress:
            continue
        overlay.set_draw_color(*RULE)
        overlay.line(MARGIN, 286, PAGE_WIDTH - MARGIN, 286)
        overlay.set_y(287)
        overlay.set_font(FONT_NAME, size=7)
        overlay.set_text_color(*MUTED)
        overlay.cell(90, 5, "RTLDI ATLAS 2026 | PRINT EDITION")
        overlay.cell(90, 5, f"PAGE {index + 1} OF {total_pages}", align="R")
    overlay.output(overlay_path)

    overlay_reader = PdfReader(str(overlay_path))
    writer = PdfWriter()
    for page, folio in zip(reader.pages, overlay_reader.pages):
        page.merge_page(folio)
        writer.add_page(page)

    def locate(phrase: str) -> Optional[int]:
        return next((i for i, text in enumerate(page_text) if phrase in text), None)

    sections = [
        ("Part I — Project Record and Global Overview", "Publication Record, Rights, and Citation", [
            ("About the RTLDI Atlas", "About the RTLDI Atlas"),
            ("Executive Description", "Executive Description"),
            ("Methodology and Data Sources", "Methodology and Data Sources"),
            ("Causal Projection from Outer Enclosures", "Causal Projection from Outer Enclosures"),
            ("Global Map and Lever Overview", "Cartographic Approach and the Nested Map"),
            ("Summary of 193 UN Member States", "Summary Table of All 193 UN Member Nations"),
        ]),
        ("Part II — UN Regional Summaries", "UN Regional Summaries", []),
        ("Part III — Nation Profiles", "Detailed Nation Profiles", []),
        ("Part IV — Eurozone Focus", "EUROZONE EXCLUSIONS", []),
        ("Part V — Evidence, Data, and Project Record", "The methods, sources, rights, and production record", [
            ("Nine-Lever Executable Crosswalk", "The Nine Levers: Executable Crosswalk"),
            ("GDP Regression and Eta", "GDP Regression, Significance, and Eta"),
            ("V-Dem Reproduction", "V-Dem Dataset and Reproduction"),
            ("World Bank Reproduction", "World Bank Dataset and Reproduction"),
            ("Citation and Licensing", "Citation, Licensing, and Reuse"),
            ("Glossary", "Glossary of Terms"),
            ("Credits", "Credits and Acknowledgments"),
            ("Colophon", "Colophon and Print Specification"),
        ]),
    ]
    for title, phrase, children in sections:
        page_number = locate(phrase)
        if page_number is None:
            continue
        parent = writer.add_outline_item(title, page_number)
        for child_title, child_phrase in children:
            child_page = locate(child_phrase)
            if child_page is not None:
                writer.add_outline_item(child_title, child_page, parent=parent)

    writer.add_metadata({
        "/Title": "RTLDI Atlas 2026: UN Member States",
        "/Author": "RTLDI Atlas Project; Sid J.A. Hubbard, Principal Investigator",
        "/Subject": "Right to Life Deficit Index, RTLP scores, capital exclusions, and nine-lever country profiles",
        "/Keywords": "RTLDI, RTLP, V-Dem, World Bank, capital exclusions, atlas",
        "/Creator": "RTLDI Atlas open-source publication pipeline",
        "/Producer": "fpdf2, PyPDF2, Plotly, Kaleido, Pillow, and qrcode",
    })
    writer.page_layout = "/TwoPageRight"
    writer.page_mode = "/UseOutlines"
    with out.open("wb") as file_obj:
        writer.write(file_obj)

    overlay_path.unlink(missing_ok=True)
    assembled.unlink(missing_ok=True)
    return out


def concat_pdfs(front: Optional[Path], regions: Optional[Path], nations: Optional[Path], back: Optional[Path], out: Path, eurozone: Optional[Path] = None) -> Path:
    """Concatenate front, regions, nations, Eurozone report, and back matter.
    This is the final step before creating a GitHub release asset.
    Requires PyPDF2 (already present in the environment).
    """
    if not HAS_PYPDF:
        print("WARNING: PyPDF2 not available; cannot concatenate. Returning None.")
        return None

    writer = PdfWriter()
    total_pages = 0
    for label, p in [("front", front), ("regions", regions), ("nations", nations), ("Eurozone", eurozone), ("back", back)]:
        if p is None:
            continue
        p = Path(p)
        if not p.exists():
            print(f"  Skipping {label} (not found: {p})")
            continue
        reader = PdfReader(str(p))
        for page in reader.pages:
            writer.add_page(page)
        total_pages += len(reader.pages)
        print(f"  Added {label}: {len(reader.pages)} pages")

    if total_pages % 2:
        writer.add_blank_page(width=595.28, height=841.89)
        total_pages += 1
        print("  Added final blank verso for duplex print alignment")

    out.parent.mkdir(parents=True, exist_ok=True)
    assembled = out.with_name(out.stem + "_assembled.pdf")
    with assembled.open("wb") as f:
        writer.write(f)
    _finalize_print_pdf(assembled, out)
    print(f"Concatenated print-ready PDF written to: {out}  (total {total_pages} pages)")
    return out


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(
        description="Generate RTLDI ATLAS 2026 PDF parts (front / regions / nations / back) and concatenate for release."
    )
    parser.add_argument("--front", action="store_true", help="Build only front matter PDF (title through 193 summary table)")
    parser.add_argument("--regions", action="store_true", help="Build only the 22 UN Regional Summaries pages")
    parser.add_argument("--nations", action="store_true", help="Build only the 193 nation profile pages")
    parser.add_argument("--back", action="store_true", help="Build only back matter (attribution + index + credits)")
    parser.add_argument("--concat-only", action="store_true", help="Concatenate existing part PDFs into release (no rebuild)")
    parser.add_argument("--release", "--all", dest="release", action="store_true",
                        help="Build all four parts then concatenate (default behavior when no flags)")

    args = parser.parse_args(argv)

    do_all = not (args.front or args.regions or args.nations or args.back or args.concat_only)

    front_p = Path(FRONT_PDF)
    regions_p = Path(REGIONS_PDF)
    nations_p = Path(NATIONS_PDF)
    back_p = Path(BACK_PDF)
    eurozone_p = Path(EUROZONE_PDF)
    release_p = Path(RELEASE_PDF)

    if args.concat_only:
        if not (front_p.exists() and regions_p.exists() and nations_p.exists() and eurozone_p.exists() and back_p.exists()):
            print("concat-only requested but one or more part PDFs are missing. Run without --concat-only first.")
            return 1
        concat_pdfs(front_p, regions_p, nations_p, back_p, release_p, eurozone_p)
        return 0

    data = None
    if args.front or args.regions or args.nations or args.back or do_all:
        data = prepare_atlas_data()

    f = r = n = b = None
    if args.front or do_all:
        f = build_front_matter(data)
    if args.regions or do_all:
        r = build_regions(data)
    if args.nations or do_all:
        n = build_nations(data)
    if do_all or args.release:
        subprocess.run([sys.executable, "-m", "src.generate_eurozone_atlas"], check=True)
    if args.back or do_all:
        b = build_back_matter(data)

    if do_all or args.release:
        concat_pdfs(f or front_p, r or regions_p, n or nations_p, b or back_p, release_p, eurozone_p)

    print("\nOutputs (most current versions):")
    for p in [front_p, regions_p, nations_p, eurozone_p, back_p, release_p]:
        if p.exists():
            print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

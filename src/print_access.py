"""Shared print-access pages linking the physical atlas to its public digital sources."""

from __future__ import annotations

from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_H


REPOSITORY_URL = "https://github.com/SJAH9/rtldi-atlas"
WEB_ATLAS_URL = "https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/"
FULL_DATA_URL = "https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/full_data.html"
INTERACTIVE_MAP_URL = "https://sjah9.github.io/rtldi-atlas/outputs/html-atlas/global_interactive.html"


def qr_image(url: str, slug: str) -> Path:
    """Create a high-resolution, high-redundancy QR image suitable for offset or digital print."""
    out_dir = Path("outputs/figures/qr")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.png"
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=20,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(path)
    return path


def draw_qr_gateway(
    pdf,
    *,
    title: str,
    subtitle: str,
    url: str,
    slug: str,
    kicker: str,
    note: str,
) -> int:
    """Add a restrained full-page QR gateway and return its local page number."""
    pdf.add_chromeless_page()
    page_width = 210
    page_height = 297
    margin = 18

    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, page_width, page_height, style="F")
    pdf.set_fill_color(16, 126, 101)
    pdf.rect(margin, 28, 2.5, 41, style="F")

    pdf.set_xy(margin + 8, 30)
    pdf.set_font("ArialUnicode", "", 7.5)
    pdf.set_text_color(16, 126, 101)
    pdf.cell(0, 4, kicker.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(margin + 8)
    pdf.set_font("ArialUnicode", "", 25)
    pdf.set_text_color(24, 32, 43)
    pdf.multi_cell(160, 10.5, title)
    pdf.set_x(margin + 8)
    pdf.set_font("ArialUnicode", "", 10.5)
    pdf.set_text_color(91, 103, 112)
    pdf.multi_cell(158, 5.4, subtitle)

    qr_path = qr_image(url, slug)
    qr_size = 92
    qr_x = (page_width - qr_size) / 2
    qr_y = 91
    pdf.image(str(qr_path), x=qr_x, y=qr_y, w=qr_size, h=qr_size, link=url)

    panel_y = 195
    pdf.set_fill_color(247, 250, 252)
    pdf.set_draw_color(198, 209, 218)
    pdf.rect(margin, panel_y, page_width - 2 * margin, 37, style="DF")
    pdf.set_xy(margin + 6, panel_y + 5)
    pdf.set_font("ArialUnicode", "", 8)
    pdf.set_text_color(31, 78, 121)
    pdf.multi_cell(page_width - 2 * margin - 12, 4.2, url, align="C", link=url)
    pdf.set_xy(margin + 8, panel_y + 18)
    pdf.set_font("ArialUnicode", "", 8.2)
    pdf.set_text_color(24, 32, 43)
    pdf.multi_cell(page_width - 2 * margin - 16, 4.4, note, align="C")

    pdf.set_xy(margin, 258)
    pdf.set_font("ArialUnicode", "", 7)
    pdf.set_text_color(91, 103, 112)
    pdf.multi_cell(page_width - 2 * margin, 4, "Scan with a phone camera or use the printed URL. QR destination verified at production time.", align="C")
    return pdf.page_no()


def draw_mini_link(pdf, *, label: str, url: str, slug: str) -> None:
    """Draw a compact, clickable QR-and-URL row for a printed external link."""
    page_width = 210
    margin = getattr(pdf, "l_margin", 18)
    qr_size = 13
    row_height = 17
    if pdf.get_y() + row_height > 280:
        pdf.add_page()

    y = pdf.get_y()
    qr_path = qr_image(url, f"mini-{slug}")
    pdf.image(str(qr_path), x=margin, y=y, w=qr_size, h=qr_size, link=url)
    pdf.set_xy(margin + qr_size + 4, y + 1)
    pdf.set_font("ArialUnicode", "", 6.8)
    pdf.set_text_color(16, 126, 101)
    pdf.cell(page_width - margin * 2 - qr_size - 4, 3.5, label.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(margin + qr_size + 4, y + 5)
    pdf.set_font("ArialUnicode", "", 6.3)
    pdf.set_text_color(31, 78, 121)
    pdf.multi_cell(page_width - margin * 2 - qr_size - 4, 3.2, url, link=url)
    pdf.set_y(y + row_height)


def draw_section_opener(
    pdf,
    *,
    part: str,
    title: str,
    subtitle: str,
    facts: list[tuple[str, str]],
) -> int:
    """Add a recto-style section opener with stable publication hierarchy."""
    pdf.add_chromeless_page()
    page_width = 210
    margin = 20
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, page_width, 297, style="F")
    pdf.set_fill_color(31, 78, 121)
    pdf.rect(margin, 30, 3, 68, style="F")
    pdf.set_fill_color(16, 126, 101)
    pdf.rect(margin + 4.5, 30, 1.5, 68, style="F")

    pdf.set_xy(margin + 13, 35)
    pdf.set_font("ArialUnicode", "", 8)
    pdf.set_text_color(16, 126, 101)
    pdf.cell(0, 4, part.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(margin + 13)
    pdf.set_font("ArialUnicode", "", 28)
    pdf.set_text_color(24, 32, 43)
    pdf.multi_cell(150, 11.5, title, align="L")
    pdf.set_x(margin + 13)
    pdf.set_font("ArialUnicode", "", 11)
    pdf.set_text_color(91, 103, 112)
    pdf.multi_cell(148, 5.5, subtitle, align="L")

    y = 132
    width = (page_width - 2 * margin - 10) / 2
    for index, (label, value) in enumerate(facts):
        col = index % 2
        row = index // 2
        x = margin + col * (width + 10)
        box_y = y + row * 42
        pdf.set_fill_color(247, 250, 252)
        pdf.set_draw_color(198, 209, 218)
        pdf.rect(x, box_y, width, 32, style="DF")
        pdf.set_xy(x + 5, box_y + 5)
        pdf.set_font("ArialUnicode", "", 7)
        pdf.set_text_color(16, 126, 101)
        pdf.cell(width - 10, 4, label.upper(), new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(x + 5, box_y + 12)
        pdf.set_font("ArialUnicode", "", 11)
        pdf.set_text_color(24, 32, 43)
        pdf.multi_cell(width - 10, 5.2, value, align="L")
    return pdf.page_no()

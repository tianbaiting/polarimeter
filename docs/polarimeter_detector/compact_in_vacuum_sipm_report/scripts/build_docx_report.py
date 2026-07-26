from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


REPORT_DIR = Path(__file__).resolve().parents[1]
BUILD_DIR = REPORT_DIR / "build"
OUTPUT_PATH = REPORT_DIR / "CompactInVacuum_SiPM_Engineering_Procurement_Report.docx"
CHART_PATH = BUILD_DIR / "sipm_saturation.png"
DERIVED_RESULTS_PATH = REPORT_DIR / "generated" / "derived_results.json"
THICKNESS_SUMMARY_PATH = REPORT_DIR / "generated" / "thickness_summary.csv"

BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
TEXT = "202124"
MUTED = "5F6368"
LIGHT = "F2F4F7"
PALE_BLUE = "EAF2F8"
PALE_GREEN = "E8F3EC"
PALE_AMBER = "FFF4D6"
PALE_RED = "FCE8E6"
WHITE = "FFFFFF"
GRID = "C9CED6"


SIPMS = [
    {
        "name": "NDL EQR15 11-6060D-S",
        "cells": 167_537,
        "pde": 0.45,
        "gain": 4.0e5,
        "area": "6.14 × 6.14",
        "pitch": "15",
        "role": "Recommended baseline",
    },
    {
        "name": "NDL EQR20 11-6060D-S",
        "cells": 97_344,
        "pde": 0.478,
        "gain": 8.0e5,
        "area": "6.24 × 6.24",
        "pitch": "20",
        "role": "Higher-gain backup",
    },
    {
        "name": "Hamamatsu S13360-6025CS",
        "cells": 57_600,
        "pde": 0.25,
        "gain": 7.0e5,
        "area": "6.0 × 6.0",
        "pitch": "25",
        "role": "Imported reference",
    },
    {
        "name": "Ray-Quant JSP-TP6050",
        "cells": 13_852,
        "pde": 0.35,
        "gain": 2.1e6,
        "area": "6.0 × 6.0",
        "pitch": "50",
        "role": "Comparison only",
    },
]


def fired_cells(energy_mev: float, efficiency: float, sipm: dict) -> tuple[float, float, float]:
    seed = energy_mev * 10_000.0 * efficiency * sipm["pde"]
    fired = sipm["cells"] * (1.0 - math.exp(-seed / sipm["cells"]))
    nonlinearity = 100.0 * (1.0 - fired / seed) if seed > 0 else 0.0
    charge_nc = fired * sipm["gain"] * 1.602176634e-19 * 1.0e9
    return fired, nonlinearity, charge_nc


def ten_percent_energy(efficiency: float, sipm: dict) -> float:
    lo, hi = 0.0, 10.0
    for _ in range(100):
        x = 0.5 * (lo + hi)
        linearity = (1.0 - math.exp(-x)) / x if x > 0 else 1.0
        if linearity > 0.9:
            lo = x
        else:
            hi = x
    x = 0.5 * (lo + hi)
    return x * sipm["cells"] / (10_000.0 * efficiency * sipm["pde"])


def load_report_data() -> tuple[dict, list[dict[str, str]]]:
    with DERIVED_RESULTS_PATH.open(encoding="utf-8") as stream:
        derived_results = json.load(stream)
    with THICKNESS_SUMMARY_PATH.open(encoding="utf-8", newline="") as stream:
        thickness_rows = list(csv.DictReader(stream))
    return derived_results, thickness_rows


def build_chart(candidate_max_mev: float, legacy_max_mev: float, carbon_max_mev: float) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 8.5,
        }
    )
    energy = np.linspace(0.05, 210.0, 900)
    fig, ax = plt.subplots(figsize=(7.25, 4.05))
    colors = ["#1F77B4", "#2CA02C", "#9467BD", "#D62728"]
    for sipm, color in zip(SIPMS, colors):
        seed = energy * 10_000.0 * 0.05 * sipm["pde"]
        fired = sipm["cells"] * (1.0 - np.exp(-seed / sipm["cells"]))
        nonlinear = 100.0 * (1.0 - fired / seed)
        ax.plot(energy, nonlinear, lw=2.0, color=color, label=sipm["name"])
    ax.axhspan(0, 5, color="#E8F3EC", alpha=0.95, zorder=0)
    ax.axhline(10, color="#B26A00", ls="--", lw=1.2)
    ax.axvline(candidate_max_mev, color="#1F4D78", ls="-.", lw=1.3)
    ax.axvline(legacy_max_mev, color="#555555", ls=":", lw=1.2)
    ax.axvline(carbon_max_mev, color="#555555", ls=":", lw=1.2)
    ax.text(
        candidate_max_mev + 2.0,
        27.0,
        f"5 mm candidate\n{candidate_max_mev:.2f} MeV",
        color="#1F4D78",
        va="top",
    )
    ax.text(
        legacy_max_mev + 2.0,
        18.0,
        f"10 mm legacy\n{legacy_max_mev:.2f} MeV",
        color="#444444",
        va="top",
    )
    ax.text(
        carbon_max_mev - 2.0,
        54.0,
        f"upper d–C carbon deposit\n{carbon_max_mev:.2f} MeV",
        color="#444444",
        ha="right",
        va="top",
    )
    ax.text(2.0, 3.4, "preferred ≤5% region", color="#276738")
    ax.set_xlim(0, 210)
    ax.set_ylim(0, 56)
    ax.set_xlabel("Deposited energy used in the unquenched light upper-bound model (MeV)")
    ax.set_ylabel("SiPM microcell nonlinearity (%)")
    ax.set_title("Short-pulse SiPM saturation estimate at 5% total optical collection")
    ax.grid(True, color="#D8DDE5", lw=0.65, alpha=0.8)
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#C9CED6")
    fig.tight_layout()
    fig.savefig(CHART_PATH, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")


def set_cell_margins(cell, top: int = 80, start: int = 120, bottom: int = 80, end: int = 120) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_width(cell, width: int) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(width))
    tc_w.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def set_table_layout(table, widths: list[int]) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), "9360")
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")
    tbl_layout = tbl_pr.find(qn("w:tblLayout"))
    if tbl_layout is None:
        tbl_layout = OxmlElement("w:tblLayout")
        tbl_pr.append(tbl_layout)
    tbl_layout.set(qn("w:type"), "fixed")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        grid_col = OxmlElement("w:gridCol")
        grid_col.set(qn("w:w"), str(width))
        grid.append(grid_col)
    for row in table.rows:
        prevent_row_split(row)
        for idx, cell in enumerate(row.cells):
            set_cell_width(cell, widths[idx])
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_table_borders(table, color: str = GRID, size: int = 4) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), str(size))
        node.set(qn("w:space"), "0")
        node.set(qn("w:color"), color)


def set_run_font(run, size: float | None = None, bold: bool | None = None, color: str | None = None) -> None:
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def add_hyperlink(paragraph, text: str, url: str, size: float = 9.5) -> None:
    part = paragraph.part
    rel_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), BLUE)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_fonts = OxmlElement("w:rFonts")
    r_fonts.set(qn("w:ascii"), "Calibri")
    r_fonts.set(qn("w:hAnsi"), "Calibri")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(size * 2)))
    r_pr.extend([r_fonts, color, underline, sz])
    run.append(r_pr)
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.append(text_node)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_page_field(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    set_run_font(run, 8.5, color=MUTED)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    value = OxmlElement("w:t")
    value.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, separate, value, end])


def keep_with_next(paragraph, value: bool = True) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    node = p_pr.find(qn("w:keepNext"))
    if node is None:
        node = OxmlElement("w:keepNext")
        p_pr.append(node)
    node.set(qn("w:val"), "1" if value else "0")


def keep_lines(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    node = p_pr.find(qn("w:keepLines"))
    if node is None:
        node = OxmlElement("w:keepLines")
        p_pr.append(node)


def add_custom_numbering(document: Document) -> tuple[int, int]:
    numbering = document.part.numbering_part.element
    abstract_ids = [int(node.get(qn("w:abstractNumId"))) for node in numbering.findall(qn("w:abstractNum"))]
    num_ids = [int(node.get(qn("w:numId"))) for node in numbering.findall(qn("w:num"))]
    next_abstract = max(abstract_ids, default=0) + 1
    next_num = max(num_ids, default=0) + 1

    def create_num(abstract_id: int, num_id: int, fmt: str, text: str) -> None:
        abstract = OxmlElement("w:abstractNum")
        abstract.set(qn("w:abstractNumId"), str(abstract_id))
        multi = OxmlElement("w:multiLevelType")
        multi.set(qn("w:val"), "singleLevel")
        abstract.append(multi)
        level = OxmlElement("w:lvl")
        level.set(qn("w:ilvl"), "0")
        start = OxmlElement("w:start")
        start.set(qn("w:val"), "1")
        num_fmt = OxmlElement("w:numFmt")
        num_fmt.set(qn("w:val"), fmt)
        level_text = OxmlElement("w:lvlText")
        level_text.set(qn("w:val"), text)
        justification = OxmlElement("w:lvlJc")
        justification.set(qn("w:val"), "left")
        p_pr = OxmlElement("w:pPr")
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "num")
        tab.set(qn("w:pos"), "720")
        tabs.append(tab)
        indentation = OxmlElement("w:ind")
        indentation.set(qn("w:left"), "720")
        indentation.set(qn("w:hanging"), "360")
        p_pr.extend([tabs, indentation])
        level.extend([start, num_fmt, level_text, justification, p_pr])
        abstract.append(level)
        numbering.append(abstract)
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(num_id))
        abstract_ref = OxmlElement("w:abstractNumId")
        abstract_ref.set(qn("w:val"), str(abstract_id))
        num.append(abstract_ref)
        numbering.append(num)

    create_num(next_abstract, next_num, "bullet", "•")
    create_num(next_abstract + 1, next_num + 1, "decimal", "%1.")
    return next_num, next_num + 1


def set_list_number(paragraph, num_id: int) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn("w:numPr"))
    if num_pr is None:
        num_pr = OxmlElement("w:numPr")
        p_pr.append(num_pr)
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    num = OxmlElement("w:numId")
    num.set(qn("w:val"), str(num_id))
    num_pr.extend([ilvl, num])


def configure_document(document: Document) -> tuple[int, int]:
    section = document.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    section.different_first_page_header_footer = True

    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(TEXT)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.10
    normal.paragraph_format.widow_control = True

    for name, size, color, before, after in (
        ("Title", 24, TEXT, 0, 12),
        ("Subtitle", 14, MUTED, 0, 8),
        ("Heading 1", 16, BLUE, 16, 8),
        ("Heading 2", 13, BLUE, 12, 6),
        ("Heading 3", 12, DARK_BLUE, 8, 4),
    ):
        style = document.styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = name not in ("Subtitle",)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.widow_control = True

    title_p_pr = document.styles["Title"].element.get_or_add_pPr()
    title_border = title_p_pr.find(qn("w:pBdr"))
    if title_border is not None:
        title_p_pr.remove(title_border)

    caption = document.styles["Caption"]
    caption.font.name = "Calibri"
    caption._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    caption.font.size = Pt(9)
    caption.font.italic = True
    caption.font.color.rgb = RGBColor.from_string(MUTED)
    caption.paragraph_format.space_before = Pt(3)
    caption.paragraph_format.space_after = Pt(8)
    caption.paragraph_format.keep_with_next = False

    if "Table Text" not in document.styles:
        style = document.styles.add_style("Table Text", WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        style.font.size = Pt(9)
        style.font.color.rgb = RGBColor.from_string(TEXT)
        style.paragraph_format.space_after = Pt(2)
        style.paragraph_format.line_spacing = 1.0
        style.paragraph_format.widow_control = True

    if "Small Note" not in document.styles:
        style = document.styles.add_style("Small Note", WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        style.font.size = Pt(9.5)
        style.font.color.rgb = RGBColor.from_string(MUTED)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.line_spacing = 1.05

    header = section.header
    paragraph = header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run("COMPACTINVACUUM POLARIMETER  |  PRELIMINARY ENGINEERING REPORT")
    set_run_font(run, 8.5, bold=True, color=MUTED)
    footer = section.footer
    add_page_field(footer.paragraphs[0])
    return add_custom_numbering(document)


def add_body(document: Document, text: str, bold_lead: str | None = None, style: str | None = None):
    paragraph = document.add_paragraph(style=style)
    if bold_lead and text.startswith(bold_lead):
        lead = paragraph.add_run(bold_lead)
        set_run_font(lead, bold=True)
        rest = paragraph.add_run(text[len(bold_lead) :])
        set_run_font(rest)
    else:
        run = paragraph.add_run(text)
        set_run_font(run)
    keep_lines(paragraph)
    return paragraph


def add_bullet(document: Document, text: str, bullet_num_id: int):
    paragraph = document.add_paragraph()
    set_list_number(paragraph, bullet_num_id)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.line_spacing = 1.167
    run = paragraph.add_run(text)
    set_run_font(run)
    keep_lines(paragraph)
    return paragraph


def add_numbered(document: Document, text: str, decimal_num_id: int):
    paragraph = document.add_paragraph()
    set_list_number(paragraph, decimal_num_id)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.line_spacing = 1.167
    run = paragraph.add_run(text)
    set_run_font(run)
    keep_lines(paragraph)
    return paragraph


def add_table(document: Document, headers: list[str], rows: list[list[str]], widths: list[int], font_size: float = 8.8):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    set_table_layout(table, widths)
    set_table_borders(table)
    header_row = table.rows[0]
    set_repeat_table_header(header_row)
    for idx, header in enumerate(headers):
        set_cell_shading(header_row.cells[idx], LIGHT)
        paragraph = header_row.cells[idx].paragraphs[0]
        paragraph.style = document.styles["Table Text"]
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(header)
        set_run_font(run, font_size, bold=True, color=TEXT)
    for row_values in rows:
        row = table.add_row()
        for idx, value in enumerate(row_values):
            cell = row.cells[idx]
            paragraph = cell.paragraphs[0]
            paragraph.style = document.styles["Table Text"]
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(str(value))
            set_run_font(run, font_size, color=TEXT)
    set_table_layout(table, widths)
    return table


def add_callout(document: Document, title: str, paragraphs: list[str], fill: str) -> None:
    table = document.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    set_table_layout(table, [9360])
    set_table_borders(table, color=fill, size=6)
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    first = cell.paragraphs[0]
    first.style = document.styles["Table Text"]
    first.paragraph_format.space_after = Pt(4)
    run = first.add_run(title)
    set_run_font(run, 10.5, bold=True, color=DARK_BLUE)
    for text in paragraphs:
        paragraph = cell.add_paragraph(style=document.styles["Table Text"])
        paragraph.paragraph_format.space_after = Pt(3)
        run = paragraph.add_run(text)
        set_run_font(run, 9.5)
    document.add_paragraph().paragraph_format.space_after = Pt(0)


def add_source(document: Document, number: int, title: str, organization: str, url: str, note: str) -> None:
    paragraph = document.add_paragraph(style="Small Note")
    run = paragraph.add_run(f"[{number}] {organization}, “{title}.” ")
    set_run_font(run, 9.0, color=TEXT)
    add_hyperlink(paragraph, url, url, size=8.7)
    tail = paragraph.add_run(f" {note} Accessed 26 July 2026.")
    set_run_font(tail, 9.0, color=MUTED)


def build_document() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    derived, thickness_rows = load_report_data()
    thickness_study = derived["thickness_study"]
    candidate_thickness_mm = thickness_study["candidate_thickness_mm"]
    legacy_thickness_mm = thickness_study["legacy_reference_thickness_mm"]
    candidate_min_mev = thickness_study["candidate_minimum_deposit_mev"]
    candidate_max_mev = thickness_study["candidate_maximum_deposit_mev"]
    legacy_max_mev = thickness_study["legacy_maximum_deposit_mev"]
    maximum_reduction_percent = thickness_study["maximum_deposit_reduction_percent"]
    energy_by_key = {row["key"]: row for row in derived["energy_deposition"]}
    carbon_max_mev = energy_by_key["dc_carbon_small"]["deposit_range_mev"][1]
    eqr15 = next(row for row in derived["sipm"] if row["key"] == "eqr15")
    build_chart(candidate_max_mev, legacy_max_mev, carbon_max_mev)
    document = Document()
    bullet_num_id, decimal_num_id = configure_document(document)

    title = document.add_paragraph(style="Title")
    title.paragraph_format.space_before = Pt(84)
    title.paragraph_format.space_after = Pt(16)
    run = title.add_run("CompactInVacuum Polarimeter")
    set_run_font(run, 24, bold=True, color=TEXT)
    subtitle = document.add_paragraph(style="Subtitle")
    run = subtitle.add_run("SiPM Detector, Vacuum Chamber, and China Procurement Engineering Report")
    set_run_font(run, 14, color=MUTED)
    document.add_paragraph()
    metadata = [
        ("Status", "Preliminary Design Review / Procurement Planning"),
        ("Issue date", "26 July 2026"),
        ("CAD reference", "polarimeter commit d1fc28f96a2018a212be7de07d94d80ad435ba9f"),
        ("Configuration", "compactInVacuum/config/default_compactInVacuum.yaml"),
        ("Procurement region", "People’s Republic of China preferred"),
        ("Primary integration candidate", "Shanghai PrMat Precision Instrument Technology Co., Ltd. (conditional qualification)"),
    ]
    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for label, value in metadata:
        row = table.add_row()
        set_cell_shading(row.cells[0], LIGHT)
        p0 = row.cells[0].paragraphs[0]
        p0.style = document.styles["Table Text"]
        r0 = p0.add_run(label)
        set_run_font(r0, 9.5, bold=True)
        p1 = row.cells[1].paragraphs[0]
        p1.style = document.styles["Table Text"]
        r1 = p1.add_run(value)
        set_run_font(r1, 9.5)
    set_table_layout(table, [2300, 7060])
    set_table_borders(table)
    document.add_paragraph()
    warning = document.add_paragraph()
    warning.paragraph_format.space_before = Pt(18)
    warning.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = warning.add_run("PRELIMINARY — NOT FOR FABRICATION OR PURCHASE ORDER RELEASE")
    set_run_font(run, 10, bold=True, color="A33A2B")
    note = document.add_paragraph(style="Small Note")
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = note.add_run(
        "The report converts the present physics and CAD model into an engineering baseline. "
        "Open dimensions, vacuum requirements, and supplier capabilities must be closed at the stated gates."
    )
    set_run_font(run, 9.5, color=MUTED)
    document.add_page_break()

    document.add_heading("1. Executive decision", level=1)
    add_callout(
        document,
        "Recommended prototype baseline",
        [
            "Use a fast blue plastic scintillator, not a high-light-yield inorganic crystal, for the first compact detector.",
            f"Active element: study a 5–6 mm active-thickness band; use {candidate_thickness_mm:.0f} mm as the first calculation candidate, not as a frozen optimum.",
            "Photosensor: NDL EQR15 11-6060D-S, 6.14 × 6.14 mm², 15 µm pitch, 167,537 microcells.",
            "Design the optical interface for a measured total collection efficiency of 2–5%, with channel-by-channel calibration and saturation correction.",
            "Keep the active front-end outside the vacuum. Use one shielded 50 Ω coaxial feedthrough per detector channel, with the SiPM bias carried through an external bias tee.",
        ],
        PALE_GREEN,
    )
    add_body(
        document,
        "The SiPM choice is technically viable for the expected elastic d–p signals if a high-microcell-count device is used and the optical collection is deliberately controlled. "
        f"At the {candidate_thickness_mm:.0f} mm candidate’s maximum estimated normal d–p energy deposit of {candidate_max_mev:.2f} MeV, "
        f"the EQR15 microcell nonlinearity is approximately {eqr15['normal']['2pct']['nonlinearity_percent']:.2f}% at 2% collection "
        f"and {eqr15['normal']['5pct']['nonlinearity_percent']:.2f}% at 5% collection. "
        "The estimate is an upper bound because it starts from the electron-equivalent light yield and does not credit Birks quenching for protons, deuterons, or carbon ions."
    )
    add_body(
        document,
        f"The principal remaining saturation risk is not only the SiPM. At 5% collection the same event can produce approximately {eqr15['normal']['5pct']['charge_nc']:.3f} nC from an EQR15. "
        "A direct 50 Ω connection, preamplifier, or digitizer may clip even while the microcells remain acceptably linear. "
        "The prototype therefore requires a low-gain charge path, a timing path, input protection, and a calibrated LED/laser linearity scan."
    )
    add_body(
        document,
        "Shanghai PrMat is a reasonable candidate for chamber integration because its public material states that it develops vacuum precision components and provides custom part design and machining. "
        "No public specification for the intended rotary feedthrough or a completed vacuum chamber matching this polarimeter was located. "
        "PrMat must therefore be treated as a candidate to be qualified through an RFQ, drawings, process records, inspection, and helium leak acceptance—not as a prequalified source."
    )
    add_callout(
        document,
        "Fabrication blocker: present ICF114 beam-port model",
        [
            "The current CAD configuration specifies a 63.6 mm pipe outside diameter and 63.0 mm inside diameter, leaving only 0.3 mm radial wall thickness.",
            "A standard ICF114 half nipple commonly provides approximately 60.2 mm clear diameter with a 63.5 mm tube outside diameter.",
            "ICF114 is a fixed external interface for both polarimeters. Resolve the 63 mm CAD stay-clear conflict by replacing placeholder pipe geometry with certified ICF114 flange, nipple, adapter, and bellows dimensions—not by changing the flange contract.",
        ],
        PALE_RED,
    )
    document.add_heading("Decision summary", level=2)
    add_table(
        document,
        ["Item", "Recommended decision", "Release condition"],
        [
            ["Scintillator", "Fast blue plastic; 5–6 mm prototype band", "LISE++/Geant4 comparison plus domestic batch timing, light output, machining, and vacuum-screening data"],
            ["SiPM", "NDL EQR15 baseline; EQR20 backup; Hamamatsu reference", "Bench linearity, gain, dark rate, temperature coefficient, and lot screening"],
            ["Chamber architecture", "Short cylindrical shell plus removable flat service plate / faceted detector cartridge", "Port map, external-pressure FEA, handling mass, and detector access"],
            ["ICF interfaces", "afterSRC: ICF114 front/rear + top ICF70; CompactInVacuum: ICF114 front/rear", "Certified component drawings, beam stay-clear, and ICF-class leak acceptance"],
            ["PrMat workshare", "Chamber, rotary feedthrough integration, metallic detector cassettes, final leak/dimensional acceptance", "Supplier capability questionnaire and accepted quality plan"],
            ["Detector optical/electronic workshare", "Scintillator supplier plus project electronics team", "Golden cassette demonstrated before production"],
        ],
        [2000, 4200, 3160],
        8.5,
    )
    document.add_heading("2. Scope, reference configuration, and open assumptions", level=1)
    add_body(
        document,
        "The project contains two polarimeters. The afterSRC instrument keeps the present external H+V+V detector arrangement and has fixed ICF114 front and rear beam interfaces, a top ICF70 rotary-feedthrough interface, and no additional side vacuum ports. "
        "CompactInVacuum is the future primary development version; its front and rear beam interfaces are also fixed as ICF114. Adapters and bellows may be inserted, but every vacuum-boundary joint must preserve ICF/CF all-metal knife-edge practice and the assembly leak requirement. "
        "The reference physics case is 380 MeV deuterons on a CH₂ target, with coincident detection of elastically scattered deuterons and protons in four azimuthal sectors. "
        "The current model has three detector stations per sector: D at 20.9° and 140 mm radius, P-small at 11.2° and 190 mm radius, and P-large at 53.4° and 205 mm radius. "
        "The detector envelope is presently Ø25 mm × 50 mm, but material and photosensor remain placeholders."
    )
    document.add_heading("Frozen instrument-interface contract", level=2)
    add_table(
        document,
        ["Instrument", "Beam interfaces", "Rotary / auxiliary ports", "Vacuum acceptance"],
        [
            ["afterSRC", "Front ICF114; rear ICF114", "Top rotary interface ICF70; no extra side vacuum ports", "All-metal ICF seals; integrated helium leak ≤1 × 10⁻¹⁰ Pa·m³/s"],
            ["CompactInVacuum", "Front ICF114; rear ICF114", "Final service-port map remains under development", "Same ICF-class boundary; adapters/bellows may not downgrade it"],
        ],
        [1900, 2160, 2900, 2400],
        8.3,
    )
    document.add_heading("Current chamber envelope", level=2)
    add_table(
        document,
        ["Parameter", "Current model", "Engineering interpretation"],
        [
            ["Inner cross-section", "440 × 440 mm", "Larger than required by a compact detector cartridge; drives mass and transport volume"],
            ["Wall thickness", "10 mm nominal", "Must not be frozen without external-pressure buckling analysis and weld details"],
            ["Body length", "360 mm", "Includes a central spine concept that should be replaced by a local cartridge where possible"],
            ["Outer body envelope", "460 × 460 × 360 mm", "Approximate square-shell material volume 10.29 L; roughly 80 kg if stainless steel"],
            ["End-interface extent", "approximately 555 mm total z envelope", "Transport length includes front and rear beamline interfaces"],
            ["Detector count", "12 operating channels", "Three energy stations in each of four sectors; production plan should include spares"],
        ],
        [2600, 2200, 4560],
        8.7,
    )
    document.add_heading("Compact v2 design direction", level=2)
    add_bullet(
        document,
        "Use an approximately 0.8 geometric scale as the first CAD candidate: D/P-small/P-large radii near 112/152/164 mm and a Ø20 mm active diameter. This preserves the present angular acceptance approximately while reducing the detector envelope.",
        bullet_num_id,
    )
    add_bullet(
        document,
        "Evaluate a short cylindrical pressure shell around a removable flat or faceted detector/service cartridge. A cylinder is structurally efficient under external pressure; the flat service element simplifies ICF bosses, coaxial feedthroughs, alignment datums, and maintenance.",
        bullet_num_id,
    )
    add_bullet(
        document,
        "Group electrical services on one removable plate or top/rear manifold. Do not distribute twelve fast-signal feedthroughs around the curved wall unless routing, access, weld distortion, and maintenance clearly justify it.",
        bullet_num_id,
    )
    add_bullet(
        document,
        "Use short, removable beamline spools and protective ICF knife-edge covers for transport. Add lifting points and specify a maximum manually handled subassembly mass.",
        bullet_num_id,
    )
    document.add_heading("Assumptions that remain provisional", level=2)
    add_table(
        document,
        ["Assumption", "Value used here", "Required closure evidence"],
        [
            ["Beam energy and reaction", "380 MeV d + CH₂; elastic d–p coincidence", "Approved physics configuration and Geant4 run card"],
            ["Active scintillator thickness", "5 mm calculation candidate; 5–6 mm prototype band", "LISE++ five-model envelope, Geant4, source tests, then beam measurement"],
            ["Optical collection to SiPM active area", "2–5% design target", "Collimated scan of the actual wrapped detector"],
            ["Plastic light yield", "10,000 photons/MeV electron-equivalent", "Domestic supplier batch certificate and electron/gamma test"],
            ["Vacuum boundary", "ICF all-metal primary seals; integrated helium leak ≤1 × 10⁻¹⁰ Pa·m³/s", "Signed purchased-part drawings, cleaning/bake plan, and witnessed leak report"],
            ["Beam stay-clear", "Current CAD says 63 mm", "Beam-envelope drawing including alignment and tolerance margin"],
            ["Rotary feedthrough", "Top ICF70 concept, Ø18 mm shaft, 0°/90° positions", "PrMat model datasheet, load case, torque, backlash, life, and interface drawing"],
        ],
        [2650, 2300, 4410],
        8.5,
    )
    document.add_heading("3. Detector physics and active thickness", level=1)
    add_body(
        document,
        "The existing energy-loss analysis was developed for the earlier external-detector layout. For this report the elastic d–p coincidence acceptance was recalculated using the present compact detector diameters and radii. "
        "The coincidence overlap corresponds approximately to 61.91–75.51° and 147.58–163.55° in the center-of-mass system. "
        f"The table below gives the LISE++ ATIMA 1.2 LS estimate for the {candidate_thickness_mm:.0f} mm calculation candidate. "
        "Each kinetic-energy value is converted to a range, the active thickness is subtracted, and the residual range is converted back to residual energy."
    )
    candidate_rows = []
    branch_labels = {
        "forward_dp_deuteron": "Forward d, D station",
        "forward_dp_proton": "Forward p, P-large",
        "backward_dp_deuteron": "Backward d, D station",
        "backward_dp_proton": "Backward p, P-small",
        "dc_deuteron": "d–C deuteron, D station",
        "dc_carbon_small": "d–C carbon, P-small",
        "dc_carbon_large": "d–C carbon, P-large",
    }
    for key in branch_labels:
        row = energy_by_key[key]
        candidate_rows.append(
            [
                branch_labels[key],
                f"{row['lab_range_deg'][0]:.2f}–{row['lab_range_deg'][1]:.2f}°",
                f"{row['incident_range_mev'][0]:.2f}–{row['incident_range_mev'][1]:.2f} MeV",
                f"{row['deposit_range_mev'][0]:.2f}–{row['deposit_range_mev'][1]:.2f} MeV",
                row["significance"],
            ]
        )
    add_table(
        document,
        ["Branch / station", "Lab angle", "Incident energy", f"Deposit in {candidate_thickness_mm:.0f} mm", "Design significance"],
        candidate_rows,
        [1800, 1400, 1700, 1700, 2760],
        7.8,
    )
    active_thickness_heading = document.add_heading("Active-thickness recommendation", level=2)
    active_thickness_heading.paragraph_format.page_break_before = True
    add_body(
        document,
        f"The detector should be treated as a ΔE counter, not a stopping calorimeter: the largest accepted-particle range in the LISE++ model envelope is approximately {thickness_study['rows'][0]['maximum_model_range_mm']:.1f} mm. "
        f"A {candidate_thickness_mm:.0f} mm candidate deposits {candidate_min_mev:.2f}–{candidate_max_mev:.2f} MeV across the normal d–p coincidence branches. "
        f"The legacy {legacy_thickness_mm:.0f} mm case reaches {legacy_max_mev:.2f} MeV, so the candidate reduces the maximum normal light-load case by {maximum_reduction_percent:.1f}% while retaining more than 1.5 MeV in the lowest branch. "
        "Use 5–6 mm as the first prototype band, but retain 4, 8, and 10 mm coupons because timing threshold, proton/deuteron quenching, optical uniformity, and real electronics noise can still move the optimum."
    )
    thickness_table_rows = []
    for row in thickness_rows:
        thickness_table_rows.append(
            [
                f"{float(row['thickness_mm']):.0f}",
                f"{float(row['forward_d_deposit_min_mev']):.2f}–{float(row['forward_d_deposit_max_mev']):.2f}",
                f"{float(row['forward_p_deposit_min_mev']):.2f}–{float(row['forward_p_deposit_max_mev']):.2f}",
                f"{float(row['backward_d_deposit_min_mev']):.2f}–{float(row['backward_d_deposit_max_mev']):.2f}",
                f"{float(row['backward_p_deposit_min_mev']):.2f}–{float(row['backward_p_deposit_max_mev']):.2f}",
            ]
        )
    add_table(
        document,
        ["Thickness (mm)", "Forward d ΔE", "Forward p ΔE", "Backward d ΔE", "Backward p ΔE"],
        thickness_table_rows,
        [1500, 1965, 1965, 1965, 1965],
        8.1,
    )
    add_body(
        document,
        "Table values are MeV and come directly from generated/thickness_summary.csv. "
        "The primary column model is LISE++ ATIMA 1.2 LS; generated/thickness_scan.csv retains the five-model envelope for independent inspection."
    )
    add_callout(
        document,
        "Interpretation of “crystal” for the first prototype",
        [
            "The recommended active material is a plastic scintillator, although it may be colloquially called a crystal in procurement discussions.",
            "High-light-yield CsI(Tl), GAGG, or LYSO would produce more SiPM saturation, add high-Z material and secondary-interaction background, and generally provide slower timing or higher cost.",
            "An inorganic crystal should be reconsidered only if a later requirement proves that stopping calorimetry or substantially better energy resolution is more important than fast coincidence timing and compactness.",
        ],
        PALE_BLUE,
    )
    document.add_heading("Light-yield quenching", level=2)
    add_body(
        document,
        "The saturation calculation uses the electron-equivalent light yield as a conservative upper bound. Heavy charged particles have a reduced light yield described to first order by Birks’ law:"
    )
    formula = document.add_paragraph()
    formula.alignment = WD_ALIGN_PARAGRAPH.CENTER
    formula.paragraph_format.space_before = Pt(4)
    formula.paragraph_format.space_after = Pt(8)
    run = formula.add_run("dL/dx = S(dE/dx) / [1 + kB(dE/dx)]")
    set_run_font(run, 11.5, color=DARK_BLUE)
    add_body(
        document,
        "The Birks constant and the response to deuterons, protons, and carbon ions must be measured or validated for the selected domestic plastic batch. "
        "A value taken from a nominally similar scintillator is insufficient for precision carbon rejection."
    )
    document.add_heading("4. Scintillator trade study and detector cassette", level=1)
    add_table(
        document,
        ["Material option", "Timing / light", "Advantages", "Concerns", "Disposition"],
        [
            ["Fast blue plastic (EJ-200 class / domestic equivalent)", "≈2.1–2.4 ns; ≈10,000 photons/MeV e⁻ reference", "Fast coincidence; low density and Z; machinable; domestic customization", "Birks quenching; optical uniformity; organic-material vacuum qualification", "Baseline"],
            ["CsI(Tl)", "High light; ≈1 µs class decay", "High stopping power; inexpensive domestic supply", "Severe SiPM load; slow pile-up; hygroscopic handling; high-Z background", "Not baseline"],
            ["GAGG(Ce)", "High light; ≈90 ns class", "Non-hygroscopic; good energy resolution", "Dense/high-Z; higher cost; more saturation; slower timing", "Future comparison only"],
            ["LYSO(Ce)", "Moderate-high light; ≈40 ns class", "Fast for an inorganic crystal; robust", "Dense/high-Z; intrinsic activity; cost; saturation", "Not preferred"],
        ],
        [2000, 1900, 2200, 2220, 1040],
        8.1,
    )
    document.add_heading("Recommended detector cassette", level=2)
    add_bullet(document, "Active plastic: Ø20 mm × 5–6 mm for the first 0.8-scale prototypes, or Ø25 mm × 5–6 mm if current radii are retained. Also procure 4, 8, and 10 mm coupons for the thickness gate.", bullet_num_id)
    add_bullet(document, "Polish the SiPM-coupling face and define the side/rear finish. Use a controlled reflective wrap or coating plus a separate light-tight outer cassette; record every optical material and batch.", bullet_num_id)
    add_bullet(document, "Couple one centered 6 × 6 mm SiPM to the flat rear face. Avoid adding an acrylic light guide in vacuum unless position-uniformity tests prove it is necessary. A shallow integral taper in the same plastic may be evaluated as a second prototype.", bullet_num_id)
    add_bullet(document, "Use a removable sensor carrier with repeatable spring preload. Avoid permanent optical epoxy in the first prototype so sensors and coupling layers can be exchanged. Any grease, pad, adhesive, black coating, tape, or reflector must pass the vacuum material screen.", bullet_num_id)
    add_bullet(document, "Provide a copper thermal path from the sensor carrier to a controlled chamber datum. Put a temperature sensor close to each SiPM or each thermally common group.", bullet_num_id)
    add_bullet(document, "Use an interchangeable mechanical datum scheme so all twelve cassettes can be swapped without re-surveying the chamber. Include anti-rotation, insertion stop, cable strain relief, and light-leak verification features.", bullet_num_id)
    document.add_heading("Optical uniformity is a first-order design variable", level=2)
    add_body(
        document,
        "A 6 × 6 mm SiPM covers only about 9–11% of the rear face area of a Ø20–25 mm disc. Direct coupling naturally limits collection, which helps saturation, but can create radial response variation. "
        "A highly reflective wrap improves uniformity while increasing collection and saturation. The design target is therefore not “maximum light”; it is a measured 2–5% collection with acceptable trigger margin and spatial uniformity."
    )
    add_table(
        document,
        ["Prototype optical variant", "Purpose", "Measurement"],
        [
            ["A: direct coupling, diffuse reflector", "Baseline balance of collection and uniformity", "2D collimated scan; pulse charge and timing"],
            ["B: direct coupling, specular reflector", "Test lower optical path dispersion", "Same scan plus incidence-angle dependence"],
            ["C: shallow integral taper", "Test improved coupling without a separate light guide", "Collection, uniformity, machining repeatability"],
            ["D: deliberately attenuated interface", "Reserve option if the real beam produces excess light", "Linearity versus LED/laser intensity and particle energy"],
        ],
        [2400, 3300, 3660],
        8.5,
    )
    sipm_heading = document.add_heading("5. SiPM selection and saturation calculation", level=1)
    add_table(
        document,
        ["Candidate", "Active area (mm²)", "Pitch (µm)", "Microcells", "PDE used", "Gain used", "Role"],
        [
            [s["name"], s["area"], s["pitch"], f'{s["cells"]:,}', f'{100*s["pde"]:.1f}%', f'{s["gain"]:.1e}', s["role"]]
            for s in SIPMS
        ],
        [2150, 1250, 800, 1200, 850, 1000, 2110],
        7.8,
    )
    selection_heading = document.add_heading("Selection rationale", level=2)
    add_body(
        document,
        "The EQR15 is preferred because its 15 µm pitch gives the largest microcell population among the evaluated 6 × 6 mm devices. "
        "The EQR20 offers higher gain and similar PDE but fewer cells. The Hamamatsu device is valuable as a well-documented reference. "
        "The domestic 50 µm Ray-Quant device has too few cells for the expected direct energy signal unless the optical coupling is strongly attenuated."
    )
    document.add_heading("Model", level=2)
    add_body(
        document,
        "For a scintillation pulse shorter than the SiPM recovery time, uniformly distributed over the active area, the first-order occupancy model is:"
    )
    formula = document.add_paragraph()
    formula.alignment = WD_ALIGN_PARAGRAPH.CENTER
    formula.paragraph_format.space_after = Pt(2)
    run = formula.add_run("Nseed = Edep · Yγ · ηopt · PDE")
    set_run_font(run, 11.5, color=DARK_BLUE)
    formula2 = document.add_paragraph()
    formula2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    formula2.paragraph_format.space_after = Pt(8)
    run = formula2.add_run("Nfired = Ncell · [1 − exp(−Nseed / Ncell)]")
    set_run_font(run, 11.5, color=DARK_BLUE)
    add_body(
        document,
        "Yγ is set to 10,000 photons/MeV electron-equivalent; ηopt includes every collection and coupling loss before the PDE. "
        "Nonlinearity is 1 − Nfired/Nseed. Correlated noise, recovery during the pulse, pixel-to-pixel variation, nonuniform illumination, temperature, and electronics are not included."
    )
    document.add_picture(str(CHART_PATH), width=Inches(5.10))
    caption = document.add_paragraph(style="Caption")
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.keep_with_next = False
    run = caption.add_run(
        "Figure 1. Calculated microcell nonlinearity at 5% total optical collection. "
        "The carbon point is an intentionally conservative, unquenched upper bound."
    )
    set_run_font(run, 9, color=MUTED)
    saturation_heading = document.add_heading("Saturation and charge results", level=2)
    saturation_heading.paragraph_format.page_break_before = True
    saturation_rows = []
    for sipm in SIPMS:
        _, nl2, _ = fired_cells(candidate_max_mev, 0.02, sipm)
        _, nl5, q5 = fired_cells(candidate_max_mev, 0.05, sipm)
        _, nlc, _ = fired_cells(carbon_max_mev, 0.05, sipm)
        limit = ten_percent_energy(0.05, sipm)
        saturation_rows.append(
            [
                sipm["name"],
                f"{nl2:.1f}%",
                f"{nl5:.1f}%",
                f"{q5:.3f} nC",
                f"{nlc:.1f}%",
                f"{limit:.1f} MeV",
            ]
        )
    add_table(
        document,
        ["Device", f"{candidate_max_mev:.2f} MeV, η=2%", f"{candidate_max_mev:.2f} MeV, η=5%", "Charge at η=5%", f"{carbon_max_mev:.2f} MeV, η=5%", "10% limit at η=5%"],
        saturation_rows,
        [2200, 1280, 1280, 1350, 1570, 1680],
        8.0,
    )
    add_callout(
        document,
        "Result",
        [
            "EQR15 meets the preferred ≤5% microcell-nonlinearity target for all normal d–p events at 2–5% optical collection.",
            "At 5% collection the conservative unquenched carbon upper point is about 11.9% nonlinear; Birks quenching will reduce the real occupancy, but carbon calibration is still required.",
            "The 5 mm candidate provides substantially more SiPM and electronics headroom than the legacy 10 mm case. The 50 µm Ray-Quant device remains a comparison device because of its smaller microcell population.",
        ],
        PALE_GREEN,
    )
    document.add_heading("Front-end dynamic range and channel architecture", level=2)
    add_body(
        document,
        f"At {candidate_max_mev:.2f} MeV and 5% collection, the EQR15 calculation gives about {eqr15['normal']['5pct']['fired_cells']:.0f} fired cells and {eqr15['normal']['5pct']['charge_nc']:.3f} nC. "
        f"A 20 ns effective charge window corresponds to an average current near {eqr15['normal']['5pct']['charge_nc'] / 20.0 * 1000.0:.1f} mA "
        f"and a 50 Ω voltage scale near {eqr15['normal']['5pct']['charge_nc'] / 20.0 * 50.0:.3f} V; the real peak depends strongly on SiPM capacitance, cable, bias tee, termination, and shaping. "
        "This estimate is sufficient to show that the front-end must be designed from measured waveforms, not from single-photoelectron gain alone."
    )
    add_bullet(document, "Provide a fast timing discriminator path and a lower-gain charge path, or digitize one protected broadband path with two calibrated gain ranges.", bullet_num_id)
    add_bullet(document, "Set the low-gain integrated-charge range to at least 1.5 nC for the prototype, then revise it after carbon/quenching measurements. Include headroom for correlated avalanches and channel variation.", bullet_num_id)
    add_bullet(document, "Use a programmable, low-noise bias supply with temperature compensation. Record sensor temperature and bias voltage in event or run metadata.", bullet_num_id)
    add_bullet(document, "Characterize gain, breakdown voltage, PDE proxy, dark count, optical crosstalk, afterpulsing, and recovery time on a statistically useful sample from every production lot.", bullet_num_id)
    add_bullet(document, "Measure linearity with a pulsed blue LED or laser over at least 0.5–200% of the expected normal d–p charge, including a two-pulse recovery scan.", bullet_num_id)
    add_bullet(document, "Keep preamplifiers and digitizers outside vacuum. Inside vacuum retain only the SiPM, minimal passive bias components, temperature sensing, vacuum-rated cable, and a cleanable carrier.", bullet_num_id)
    vacuum_services_heading = document.add_heading("6. Vacuum electrical services, grounding, and thermal design", level=1)
    vacuum_services_heading.paragraph_format.page_break_before = True
    add_body(
        document,
        "The recommended service architecture uses one shielded 50 Ω coaxial path per detector. The signal and SiPM bias can share the coax through an external bias tee, avoiding a separate high-voltage pin for every channel. "
        "Temperature sensors and any housekeeping lines use a separate low-frequency multipin feedthrough."
    )
    add_table(
        document,
        ["Service", "Recommended implementation", "Reason / acceptance item"],
        [
            ["12 fast SiPM channels", "Three CF40 flanges, each with four 50 Ω double-ended SMA feedthroughs; or equivalent qualified custom service plate", "Shielding, impedance control, replaceability, and commercially specified leak performance"],
            ["Bias", "External low-noise supply and bias tee on each coax channel", "Minimizes vacuum conductors and lets electronics remain accessible"],
            ["Temperature", "One sensor per cassette or thermally common group through a multipin CF feedthrough", "Required for gain correction and thermal qualification"],
            ["Vacuum-side cable", "Short qualified Kapton or PTFE 50 Ω cable with strain relief", "Cable type, bake temperature, capacitance, connector retention, and outgassing to be documented"],
            ["Ground", "Single defined chamber/reference ground; avoid parallel shield-return paths", "Verify noise and common-mode behavior with pumps and motors operating"],
            ["Rotary motor/encoder", "Separate filtered service path and physical cable separation", "Prevent switching noise from coupling into SiPM channels"],
        ],
        [1900, 4350, 3110],
        8.3,
    )
    add_body(
        document,
        "Beijing Feedivac publicly lists 50 Ω SMA50/SMAD50 feedthroughs up to 6.5 GHz, one channel on CF16 or up to four channels on CF40, with stated helium leak rate below 1 × 10⁻¹² Pa·m³/s and ultimate vacuum below 1 × 10⁻¹⁰ mbar. "
        "These published values make the product family a strong domestic RFQ candidate, but the exact flange, connector gender, cable assembly, bake history, and acceptance certificate must be specified in the purchase order."
    )
    document.add_heading("Thermal limits", level=2)
    add_bullet(document, "Do not treat the vacuum as a heat sink. Provide a conductive path from each SiPM/board to the chamber and calculate the steady-state temperature at operating bias and worst dark current.", bullet_num_id)
    add_bullet(document, "Keep the scintillator below its softening and optical-aging limits. The EJ-200 reference has a 75°C softening point and a recommended range up to 60°C; the domestic material must provide its own limit.", bullet_num_id)
    add_bullet(document, "Set bake temperature from the least tolerant qualified internal component. A high-temperature stainless chamber does not make the installed detector cassette bakeable at the same temperature.", bullet_num_id)
    add_bullet(document, "Run a vacuum thermal cycle with SiPM gain and dark count monitored before authorizing production.", bullet_num_id)
    document.add_heading("7. Chamber, ICF interfaces, and rotary feedthrough", level=1)
    document.add_heading("Cylinder versus square chamber", level=2)
    add_body(
        document,
        "A cylindrical shell is not incompatible with ICF ports or electrical feedthroughs. Radial ports are normally integrated through welded nozzles or formed bosses. "
        "The drawback is manufacturing and metrology: each saddle/nozzle weld needs a controlled angular datum, access can be poor, and many ports around the circumference increase distortion and routing complexity. "
        "A square box provides flat mounting faces but is heavier and less efficient under external pressure."
    )
    add_callout(
        document,
        "Preferred mechanical architecture",
        [
            "Use a short cylindrical pressure shell for vacuum efficiency and lower mass.",
            "Use one removable flat service plate, or an internal faceted detector cartridge with a flat external service manifold, for detector mounting, coax feedthrough grouping, survey datums, and maintenance.",
            "Use welded short nozzles only for frozen ICF interfaces and approved services. The afterSRC variant has no extra side vacuum ports; keep the four CompactInVacuum detector sectors internal.",
        ],
        PALE_BLUE,
    )
    add_body(
        document,
        "An initial 0.8-scale comparison suggests a body near 372 × 372 × 288 mm if a square shell were retained, with approximately 6.59 L of stainless material (roughly 52 kg). "
        "A comparable cylindrical concept was estimated near 5.16 L (roughly 41 kg) before ports, flanges, stiffeners, and covers. "
        "These are screening estimates only; pressure-vessel mass must come from final geometry and external-pressure FEA."
    )
    document.add_heading("ICF beam-port decision", level=2)
    add_table(
        document,
        ["Instrument / item", "Fixed interface", "Implementation requirement", "Acceptance evidence"],
        [
            ["afterSRC beamline", "Front ICF114; rear ICF114", "Adapters and bellows permitted; external mating faces remain ICF114", "Certified component drawings, incoming inspection, dimensional report, integrated leak test"],
            ["afterSRC target motion", "Top ICF70 rotary interface", "Purchase the rotary feedthrough through Shanghai PrMat; freeze the exact part and load case", "OEM drawing, torque/backlash/life/bake/leak data, installed acceptance test"],
            ["CompactInVacuum beamline", "Front ICF114; rear ICF114", "Correct the placeholder 63 mm stay-clear against actual ICF114 purchased parts", "Interface control drawing, beam-envelope margin, integrated leak test"],
            ["Vacuum boundary", "ICF knife edge + OFHC copper gasket", "No elastomer substitution in the primary boundary; adapters/bellows meet the same class", "Integrated helium leak ≤1 × 10⁻¹⁰ Pa·m³/s"],
        ],
        [1900, 1900, 3000, 2560],
        8.0,
    )
    add_bullet(document, "Purchase certified ICF flanges or half nipples from a qualified vacuum-component source. PrMat may weld and integrate them, but should not casually recreate the knife-edge geometry.", bullet_num_id)
    add_bullet(document, "Freeze an interface control drawing that states ICF114/ICF70 designation, OD, thickness, bolt-hole pattern, rotatable/fixed configuration, tube OD/ID, knife-edge material, gasket, bolt/nut system, and the exact mating component.", bullet_num_id)
    add_bullet(document, "Avoid calling all 4.5-inch CF-style products “ICF114” without a dimensioned drawing. Japanese ICF and other CF naming conventions can hide small but consequential differences.", bullet_num_id)
    add_bullet(document, "A bellows or reducing adapter is an installation component, not permission to weaken the vacuum standard. Specify metal seals, compatible materials/cleaning/bake limits, component leak certificate, and a final integrated helium leak test.", bullet_num_id)
    rotary_heading = document.add_heading("Rotary feedthrough RFQ data", level=2)
    add_body(
        document,
        "The afterSRC target contract uses a top-mounted ICF70 rotary-feedthrough interface, with an approximately Ø18 mm shaft and 0° beam / 90° parked positions in the present concept. "
        "The purchase specification to PrMat must request the following data before model selection:"
    )
    add_bullet(document, "Flange standard and complete dimensions; shaft diameter, material, usable internal length, external envelope, and coupling details.", bullet_num_id)
    add_bullet(document, "Allowable radial, axial, and overturning loads; output torque; breakaway torque; backlash; angular repeatability; hard stops; and position indication or encoder provision.", bullet_num_id)
    add_bullet(document, "Seal and bearing technology; continuous versus intermittent rotation; rated cycle life; lubrication; particle generation; magnetic materials; and service/rebuild procedure.", bullet_num_id)
    add_bullet(document, "Rated operating and bake temperature, ultimate pressure, certified helium leak rate, motor/manual options, and the test certificate supplied with the unit.", bullet_num_id)
    document.add_heading("8. Chamber manufacturing and acceptance specification", level=1)
    add_table(
        document,
        ["Topic", "Proposed RFQ requirement", "Required evidence"],
        [
            ["Material", "304L or 316L stainless selected with the vacuum owner; low-carbon weldable grades", "Mill certificates and material traceability"],
            ["Standard interfaces", "Purchased certified ICF flanges/half nipples; no unapproved substitutions", "Supplier drawings, certificates, incoming inspection"],
            ["Welding", "Full-penetration GTAW/TIG where applicable; inert purge; documented sequence and fixtures", "Weld map, WPS/PQR or equivalent procedure evidence, welder qualification"],
            ["Vacuum design", "No trapped volumes; vented blind holes; cleanable internal geometry; compatible fasteners", "Design review checklist and sectioned drawings"],
            ["Surface / cleaning", "Defined roughness where needed; degrease, rinse, dry, bag, and cap knife edges; passivation/electropolish only where justified", "Process travelers and cleaning record"],
            ["Structural", "External-pressure buckling FEA including ports, covers, welds, and transport loads", "Calculation report and approved proof/test plan"],
            ["Dimensional", "Beam-axis datums, flange-face position/orientation, detector datums, port clocking, and cover flatness under GD&T", "CMM or equivalent dimensional inspection report"],
            ["Leak", "Proposed assembly acceptance ≤1 × 10⁻¹⁰ Pa·m³/s helium; tighter component requirements where purchased", "Calibrated helium mass-spectrometer report and test setup"],
            ["Vacuum performance", "Base pressure, pump-down, bake, and residual-gas criteria to be frozen by beamline owner", "Witnessed vacuum acceptance test and RGA if required"],
            ["Handling", "Defined lifting points, center of gravity, maximum removable-subassembly mass, shipping fixture, and knife-edge protection", "Handling drawing and packing inspection"],
        ],
        [1600, 4870, 2890],
        7.9,
    )
    add_callout(
        document,
        "Do not release fabrication from a STEP model alone",
        [
            "The fabrication package must contain controlled 2D drawings, GD&T, weld symbols, material and cleaning notes, bought-out component part numbers, acceptance criteria, and revision history.",
            "Require PrMat to return a manufacturability review, marked-up drawings, weld sequence, and inspection plan before approval to cut material.",
        ],
        PALE_AMBER,
    )
    document.add_heading("PrMat qualification", level=2)
    add_body(
        document,
        "PrMat’s public website states that it develops vacuum precision components, MBE-related equipment, manipulators, and custom parts. A published K-cell product specifies a DN40CF flange, 200°C maximum bake, and UHV-class operating pressure, which is relevant evidence of vacuum-domain experience. "
        "It does not replace project-specific evidence for a large welded chamber or rotary feedthrough."
    )
    add_bullet(document, "Request two comparable chamber references, maximum completed chamber size/mass, in-house versus subcontracted welding, CMM capability, helium leak equipment, cleaning facility, and external-pressure analysis capability.", bullet_num_id)
    add_bullet(document, "Ask whether the rotary feedthrough is PrMat-designed, OEM, or integrated from another manufacturer. Require the original manufacturer and unaltered certificate if it is an OEM item.", bullet_num_id)
    add_bullet(document, "Separate NRE/design, purchased vacuum parts, chamber fabrication, detector cassette machining, assembly, inspection, and shipping into distinct quote lines.", bullet_num_id)
    add_bullet(document, "Define ownership and delivery of native CAD, manufacturing drawings, inspection data, and spare/replacement compatibility.", bullet_num_id)
    procurement_heading = document.add_heading("9. China-based procurement and workshare", level=1)
    procurement_heading.paragraph_format.page_break_before = True
    add_table(
        document,
        ["Package", "Preferred China source / route", "Recommended responsibility", "Qualification action"],
        [
            ["Vacuum chamber and target integration", "Shanghai PrMat", "Chamber design-for-manufacture, welding, machining, assembly, dimensional and leak acceptance", "Formal capability questionnaire; reference projects; process and inspection plan"],
            ["Rotary feedthrough", "Shanghai PrMat purchase/integration route", "Supply selected model and complete OEM data; integrate to top ICF interface", "Torque/load/life/leak/bake certificate and incoming inspection"],
            ["Plastic scintillator", "Shanghai EPIC Crystal / Shanghai Shuojie or another qualified domestic producer", "Material batch, rough machining, precision finish, polish, reflector/packaging options", "Witness samples; light yield/timing/uniformity; vacuum-material screen"],
            ["Primary SiPM", "NDL through Shanghai Centao or an authorized domestic channel", "EQR15 11-6060D-S supply with current datasheet and lot traceability", "Screen breakdown, gain, DCR, crosstalk, afterpulse, linearity, and temperature coefficient"],
            ["Backup SiPM", "NDL EQR20 through Shanghai Centao", "Small prototype quantity", "Same screening; compare timing and electronics headroom"],
            ["Reference SiPM", "Hamamatsu Photonics China", "Small control quantity of S13360-6025CS", "Use as documented cross-check; not China-origin preference"],
            ["Coax feedthroughs", "Beijing Feedivac", "CF40 four-channel 50 Ω feedthrough assemblies and vacuum cables", "Confirm exact part number, connector gender, bake, leak certificate, and spares"],
            ["Detector metal cassette", "PrMat after golden-unit drawing freeze", "Precision metal carrier, thermal path, repeatable datum, light-tight shell", "First article inspection and interchangeability test"],
            ["SiPM PCB and front-end", "Project electronics team plus qualified domestic PCB assembly", "Circuit ownership, component selection, screening, calibration, firmware/data format", "Bench qualification before chamber integration"],
        ],
        [1600, 2250, 3410, 2100],
        7.55,
    )
    document.add_heading("Recommended responsibility split", level=2)
    add_body(
        document,
        "PrMat should own the vacuum boundary, purchased ICF integration, rotary feedthrough installation, metallic cartridge/cassette parts, final chamber dimensional report, and helium leak acceptance. "
        "The scintillator supplier should own the optical material and polished part. The project electronics team should own SiPM selection, PCB, dynamic range, bias control, calibration, and data interpretation."
    )
    add_body(
        document,
        "PrMat may perform final mechanical assembly after the project supplies an accepted golden detector cassette and a controlled assembly traveler. "
        "PrMat should not be assigned responsibility for SiPM saturation, optical coupling, or particle-response calibration unless it demonstrates the required detector-physics capability and accepts quantitative performance criteria."
    )
    document.add_heading("Preliminary purchase phasing", level=2)
    add_table(
        document,
        ["Gate", "Suggested items", "Quantity guidance", "Purpose"],
        [
            ["P1 sensor/material study", "EQR15, EQR20, Hamamatsu reference; domestic plastic samples", "EQR15: 10; EQR20: 4; Hamamatsu: 2; plastic variants: 6–10 pieces", "Lot screening, optical variants, electronics and saturation tests"],
            ["P2 one-sector prototype", "One D + P-small + P-large cassettes and cables", "3 operating + at least 2 spare detector assemblies", "Real three-channel coincidence and integration trial"],
            ["P3 chamber prototype", "One engineering chamber, rotary feedthrough, service feedthrough set", "One set; buy critical seals/gaskets and cable spares", "Vacuum, thermal, alignment, handling, and maintenance qualification"],
            ["P4 production", "Twelve operating channels plus spares", "15 scintillators and 15 accepted EQR15 minimum; adjust after screening yield", "Four-sector installation with replaceable spares"],
        ],
        [1550, 2900, 2850, 2060],
        8.2,
    )
    add_body(
        document,
        "Quantities are planning values, not an authorization to purchase. The EQR15 production quantity must include the measured screening yield, and all production sensors should be from a controlled lot where practical."
    )
    document.add_heading("10. Development and verification plan", level=1)
    add_numbered(document, "Gate 0 — freeze physics and interfaces. Keep the ICF114 front/rear and afterSRC ICF70 top contracts fixed; approve beam stay-clear, detector radii/diameters, the thickness-test matrix, target motion envelope, vacuum/bake class, port map, survey datums, and transport limits.", decimal_num_id)
    add_numbered(document, "Gate 1 — single-detector optical/electronic prototype. Compare EQR15, EQR20, and the Hamamatsu reference on direct-coupled plastic variants. Complete LED/laser saturation, charge-range, timing, temperature, and 2D uniformity scans.", decimal_num_id)
    add_numbered(document, "Gate 2 — one-sector coincidence prototype. Build D, P-small, and P-large channels with final-style cabling and front-end. Validate thresholds, coincidence timing, energy separation, common-mode noise, and calibration metadata.", decimal_num_id)
    add_numbered(document, "Gate 3 — vacuum detector cartridge. Run vacuum soak, thermal cycling, dark-rate monitoring, outgassing screening, cable/feedthrough noise testing, and post-vacuum optical remeasurement.", decimal_num_id)
    add_numbered(document, "Gate 4 — engineering chamber. Complete PrMat first article, external-pressure review, dimensional inspection, helium leak test, target motion test, detector insertion/removal trial, and transport handling demonstration.", decimal_num_id)
    add_numbered(document, "Gate 5 — production release. Freeze drawings and travelers only after the golden sector and engineering chamber pass. Procure twelve operating channels plus approved spares and repeat acceptance tests.", decimal_num_id)
    acceptance_heading = document.add_heading("Minimum detector acceptance matrix", level=2)
    acceptance_heading.paragraph_format.page_break_before = True
    add_table(
        document,
        ["Test", "Method", "Prototype pass criterion", "Production record"],
        [
            ["SiPM electrical screen", "Automated I–V, gain, dark count, correlated noise, temperature scan", "Acceptance windows derived from the prototype sample; no unstable devices", "Per-device serial-number data"],
            ["Optical linearity", "Pulsed 415–425 nm source with calibrated intensity steps", "EQR15 corrected residual within project target through normal d–p range; no electronics clipping", "Per-channel correction curve"],
            ["Timing", "Fast pulsed source and coincidence reference", "Threshold and time walk support experiment coincidence requirement", "Per-channel timing calibration"],
            ["Uniformity", "Collimated 2D scan over active face", "Spatial variation within a frozen limit; no edge dead region that changes angular acceptance", "Map for golden design; sampling plan for production"],
            ["Vacuum/thermal", "Soak and cycles at frozen pressure/temperature", "No leak, discharge, gain instability, light-output loss, delamination, or cable failure", "Assembly traveler and before/after data"],
            ["Mechanical interchangeability", "Gauge and repeated cassette swaps", "Datum repeatability within alignment budget; no light leak or connector damage", "First article plus production inspection"],
            ["Coincidence physics", "Source/cosmic commissioning, then beam or validated simulation", "Normal d–p locus retained and d–C background separable at required efficiency", "Configuration, calibration, and analysis version"],
        ],
        [1650, 2800, 3340, 1570],
        7.9,
    )
    document.add_heading("Software and reproducibility", level=2)
    add_body(
        document,
        "Every reported detector result should record the CAD Git commit, resolved YAML configuration, geometry metrics, Geant4/stopping-power version, SiPM serial number, scintillator batch, bias, temperature, waveform-chain configuration, calibration version, and analysis commit. "
        "The desk mini PC remains the reference CAD environment; laptop and labenpg reproduction should compare stable geometry metrics rather than byte-identical STEP or FCStd files."
    )
    document.add_heading("11. Risk register", level=1)
    risk_table = add_table(
        document,
        ["Risk", "Likelihood", "Impact", "Control / exit condition"],
        [
            ["Current 63 mm CAD stay-clear conflicts with reference ICF114 purchased-part bore", "High", "High", "Keep ICF114 fixed; replace placeholder pipe geometry using certified flange, nipple, adapter, and bellows drawings"],
            ["SiPM microcell saturation or uncorrected carbon response", "Medium", "High", "EQR15, 2–5% collection, 5–6 mm prototype band, LED/particle calibration, saturation correction"],
            ["Front-end or ADC clips before SiPM saturation", "High", "High", "Low-gain ≥1.5 nC range, protected timing path, measured waveform and pulser scan"],
            ["Domestic plastic differs from EJ-200 reference", "Medium", "High", "Batch measurements of light, timing, Birks response, machining quality, and vacuum behavior"],
            ["Optical response varies across Ø20–25 mm face", "Medium", "Medium", "2D scan of reflector/taper variants; freeze measured optical assembly"],
            ["SiPM gain drifts with temperature", "High", "Medium", "Conductive thermal path, local temperature sensing, bias compensation, run metadata"],
            ["Organic materials outgas or degrade in vacuum", "Medium", "High", "Material declaration, vacuum soak/RGA as required, post-soak optical/electrical comparison"],
            ["Curved-shell port welds distort datums", "Medium", "High", "Group services on a flat plate; weld sequence/fixtures; intermediate and final metrology"],
            ["Rotary feedthrough capability is assumed from a catalog description", "High", "High", "OEM identification, full load/torque/life/leak data, incoming and integrated acceptance test"],
            ["Supplier scope leaves detector performance unowned", "High", "High", "Explicit workshare; project owns electronics/calibration; golden cassette before PrMat assembly"],
            ["Production released before one-sector coincidence proof", "Medium", "High", "Gate reviews and no full-channel PO before Gate 2 pass"],
        ],
        [3030, 1050, 950, 4330],
        8.0,
    )
    for row in risk_table.rows[1:]:
        likelihood = row.cells[1].text
        impact = row.cells[2].text
        if "High" in (likelihood, impact):
            set_cell_shading(row.cells[1], PALE_RED if likelihood == "High" else PALE_AMBER)
            set_cell_shading(row.cells[2], PALE_RED if impact == "High" else PALE_AMBER)
    document.add_heading("Decisions required before any chamber purchase order", level=2)
    decisions = [
        "Approve the beam stay-clear diameter and tolerance budget against actual certified ICF114 flange, nipple, adapter, and bellows drawings; the ICF114 interface is already fixed.",
        "Approve the 0.8-scale detector radii and Ø20 mm acceptance, or retain present radii and Ø25 mm acceptance.",
        "Approve the 4/5/6/8/10 mm prototype matrix, with 5–6 mm as the first study band, and confirm that the detector is a ΔE counter rather than a stopping calorimeter.",
        "Confirm the integrated helium-leak criterion of ≤1 × 10⁻¹⁰ Pa·m³/s and define operating pressure, allowable gas load, populated/bare bake limits, pump-down time, cleaning class, and RGA requirement.",
        "Provide the rotary target load, center of gravity, required torque, allowed backlash, angular repeatability, cycle life, and manual/motor/encoder preference.",
        "Approve the 12-coax service concept, digitizer input range, timing requirement, grounding architecture, and temperature/bias metadata.",
        "Select the cylinder-plus-flat-service architecture after a port-layout and maintenance review.",
        "Approve PrMat’s capability, quality plan, quotation scope, and acceptance test plan after the formal RFQ response.",
    ]
    for decision in decisions:
        add_bullet(document, decision, bullet_num_id)
    document.add_heading("12. RFQ checklist for Shanghai PrMat", level=1)
    add_body(
        document,
        "The following package should be sent as a controlled RFQ after Gate 0. It is intentionally separable so chamber manufacture, rotary feedthrough supply, and detector cassette machining can be evaluated independently."
    )
    rfq_matrix_heading = document.add_heading("RFQ response matrix", level=2)
    rfq_matrix_heading.paragraph_format.page_break_before = True
    add_table(
        document,
        ["RFQ section", "Information to provide to PrMat", "Information PrMat must return"],
        [
            ["System envelope", "Approved 3D envelope, beam axis, service zones, handling limits, installed orientation", "Manufacturability comments, final mass/CoG estimate, access and lifting proposal"],
            ["Vacuum boundary", "Material, pressure/bake, leak target, cleaning, prohibited materials, standard ICF list", "Material route, bought-out parts, weld map/procedure, FEA plan, cleaning and leak procedure"],
            ["Interfaces / GD&T", "Controlled 2D interface drawings and datum hierarchy", "Production drawings, tolerance feasibility, inspection equipment, sample report format"],
            ["Rotary target", "Load case, travel, shaft/interface, angular performance, environment, cable/motor needs", "Exact model/OEM, complete datasheet, life/load/torque/backlash, leak/bake certificate, service plan"],
            ["Detector cartridge", "Golden-cassette interface, optical keep-out, thermal path, cable routing, interchangeability", "Material and finish, machining tolerances, first article plan, assembly traveler"],
            ["Electrical feedthroughs", "12 × 50 Ω coax concept plus housekeeping requirements", "Selected Feedivac/equivalent part numbers, connector/cable drawings, certificates and spares"],
            ["Acceptance", "Witness points, leak/dimensional/test criteria, documentation language and format", "Inspection and test plan, nonconformance process, certificate package"],
            ["Commercial", "Prototype and production quantities, requested line-item structure, drawing/data ownership", "NRE, parts, fabrication, inspection, packing, lead time, warranty, replacement/spare terms"],
        ],
        [1700, 3750, 3910],
        8.15,
    )
    add_callout(
        document,
        "Recommended order sequence",
        [
            "First order: rotary feedthrough data review plus one detector-cassette machining trial and, if useful, a chamber design-for-manufacture study.",
            "Second order: one engineering chamber only after beam aperture, ports, vacuum class, and detector cartridge are frozen.",
            "Production order: only after the chamber first article and one-sector detector prototype pass their acceptance gates.",
        ],
        PALE_AMBER,
    )
    document.add_heading("13. References and supplier evidence", level=1)
    add_body(
        document,
        "Supplier webpages are evidence for candidate selection only. Current signed datasheets, drawings, quotations, lot traceability, and certificates must govern procurement."
    )
    sources = [
        ("About PrMat", "Shanghai PrMat", "https://www.prmat.com/Home/About/index.html", "Public statement of vacuum precision components and custom design/manufacturing capability."),
        ("K-cell thermal evaporation source", "Shanghai PrMat", "https://www.prmat.com/Home/Product/detail/id/702.html", "Public example of a DN40CF, bakeable UHV-domain product."),
        ("NDL EQR15 series SiPM datasheet", "Shanghai Centao / NDL", "https://www.laser-opto.com/uploadfile/202412/f4cdac169ae58dc.pdf", "EQR15 device family and EQR15 11-6060D-S data."),
        ("NDL EQR20 11-6060D-S product page", "Shanghai Centao / NDL", "https://www.laser-opto.com/Single_Channel_SiPM_detectors/1899/NDL_EQR20_11_6060D_S_%E5%A4%96%E5%BB%B6%E7%94%B5%E9%98%BB%E6%B7%AC%E7%81%AD%E7%A1%85%E5%85%89%E7%94%B5%E5%80%8D%E5%A2%9E%E5%99%A8%EF%BC%88EQR_SiPM%EF%BC%89", "6.24 mm active area, 20 µm pitch, 97,344 cells, gain and PDE listing."),
        ("S13360-6025CS product page", "Hamamatsu Photonics China", "https://www.hamamatsu.com.cn/cn/zh-cn/product/optical-sensors/mppc/mppc_mppc-array/S13360-6025CS.html", "6 × 6 mm, 25 µm pitch, 57,600 pixels, gain, dark count, and capacitance."),
        ("Physics and operation of the MPPC silicon photomultiplier", "Hamamatsu Photonics", "https://hub.hamamatsu.com/us/en/technical-notes/mppc-sipms/physics-and-operation-of-the-MPPC-silicon-photomultiplier.html", "Short-pulse microcell occupancy and dynamic-range model."),
        ("General-purpose plastic scintillator EJ-200 / EJ-204 / EJ-208 / EJ-212", "Eljen Technology", "https://eljentechnology.com/images/products/data_sheets/EJ-200_EJ-204_EJ-208_EJ-212.pdf", "Reference light yield, emission wavelength, timing, density, and vacuum compatibility."),
        ("Plastic scintillator", "Shanghai EPIC Crystal / Shanghai Shuojie", "https://www.epic-crystal.com.cn/scintillation-crystals/plastic-scintillator.html", "Domestic plastic scintillator properties, forms, and customization."),
        ("SMA50/SMAD50 coaxial feedthrough", "Beijing Feedivac", "https://www.feedivac.com/bsma/168.html", "50 Ω, CF16/CF40 channel configurations, frequency, temperature, vacuum, and leak specifications."),
        ("ICF vacuum component family", "Cosmotec", "https://en.cosmotec-co.jp/products/list?category_id=64", "Official ICF component family and representative ultra-high-vacuum leak specifications."),
        ("Motion feedthrough family", "Cosmotec", "https://en.cosmotec-co.jp/products/list?category_id=383", "Official rotary, bellows, and magnetic motion-feedthrough families for vacuum service."),
        ("CF vacuum hardware", "Leybold", "https://www.leybold.com/content/leybold/es/products/vacuum-hardware-and-valves/hardware.html", "Official CF hardware guidance covering OFHC copper gaskets and ultra-high-vacuum construction."),
        ("JSP-TP6050 SiPM", "Hubei Ray-Quant / Joinbon", "https://www.ray-quant.com/en/show-55.html", "Domestic 6 × 6 mm, 50 µm-pitch comparison device."),
        ("CompactInVacuum default configuration", "polarimeter repository", "https://github.com/tianbaiting/polarimeter", "CAD and detector configuration reference at commit d1fc28f96a2018a212be7de07d94d80ad435ba9f."),
    ]
    for idx, source in enumerate(sources, 1):
        add_source(document, idx, *source)
    document.add_heading("Calculation provenance", level=2)
    add_body(
        document,
        "Energy-deposition ranges in this report were generated from the project’s elastic d–p/d–C kinematics and LISE++ range tables at 1, 2, 3, 4, 5, 6, 8, and 10 mm thickness. "
        "ATIMA 1.2 LS is the primary estimate and Hubert 1990, Ziegler low energy, ATIMA 1.2 without LS, and ATIMA 1.4 mean charge form the comparison envelope. "
        "The machine-readable sources are generated/thickness_summary.csv, generated/thickness_scan.csv, generated/derived_results.json, and generated/verification_summary.txt. "
        "These are engineering screening values and must be cross-checked by a version-controlled Geant4 result before production release."
    )
    add_body(
        document,
        "SiPM saturation values were recalculated directly from the equations in Section 5 with the listed cell counts, PDE values, gains, a 10,000 photons/MeV electron-equivalent reference yield, and the stated optical efficiencies. "
        "The report intentionally does not apply an assumed Birks constant."
    )
    document.add_paragraph()
    closing = document.add_paragraph()
    closing.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = closing.add_run("END OF PRELIMINARY REPORT")
    set_run_font(run, 9, bold=True, color=MUTED)

    core = document.core_properties
    core.title = "CompactInVacuum Polarimeter: SiPM Detector, Vacuum Chamber, and China Procurement Engineering Report"
    core.subject = "Preliminary design review and procurement planning"
    core.author = "CompactInVacuum project engineering"
    core.keywords = "polarimeter, SiPM, plastic scintillator, ICF, vacuum chamber, China procurement"
    core.comments = "Preliminary; not for fabrication or purchase order release."
    document.save(OUTPUT_PATH)


if __name__ == "__main__":
    build_document()
    print(OUTPUT_PATH)

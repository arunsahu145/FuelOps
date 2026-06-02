"""
Petrol Pump Finance Manager ERP — PDF Report Generator
Uses ReportLab to generate professional Daily and Monthly closing reports.
"""
import os
from datetime import date
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from utils.helpers import format_currency, format_litres, format_date, get_month_name

# ── Color Palette (matches dark-slate ERP theme) ─────────────────────────────
BRAND_DARK = HexColor("#0f172a")
BRAND_SURFACE = HexColor("#1e293b")
BRAND_BORDER = HexColor("#334155")
BRAND_ACCENT = HexColor("#38bdf8")
BRAND_SUCCESS = HexColor("#10b981")
BRAND_DANGER = HexColor("#ef4444")
BRAND_WARNING = HexColor("#f59e0b")
WHITE = HexColor("#ffffff")
LIGHT_GRAY = HexColor("#e2e8f0")
MID_GRAY = HexColor("#94a3b8")
ROW_ALT = HexColor("#f1f5f9")
ROW_WHITE = HexColor("#ffffff")

# ── Reports output directory ─────────────────────────────────────────────────
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def _get_styles():
    """Create custom paragraph styles for the report."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=BRAND_DARK,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        fontName="Helvetica",
        fontSize=10,
        textColor=MID_GRAY,
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=BRAND_DARK,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        name="MetricLabel",
        fontName="Helvetica",
        fontSize=9,
        textColor=MID_GRAY,
    ))
    styles.add(ParagraphStyle(
        name="MetricValue",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=BRAND_DARK,
    ))
    return styles


def _build_table(headers, rows, col_widths=None):
    """Build a styled ReportLab Table."""
    data = [headers] + rows

    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),

        # Data rows
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),

        # Alternating row backgrounds
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Grid
        ("LINEBELOW", (0, 0), (-1, 0), 1, BRAND_BORDER),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, BRAND_BORDER),
    ])

    # Alternating row colors
    for i in range(1, len(data)):
        bg = ROW_ALT if i % 2 == 0 else ROW_WHITE
        style.add("BACKGROUND", (0, i), (-1, i), bg)

    # Right-align numeric columns (last 2-3 columns typically)
    if len(headers) >= 3:
        for col in range(max(1, len(headers) - 3), len(headers)):
            style.add("ALIGN", (col, 0), (col, -1), "RIGHT")

    table.setStyle(style)
    return table


def _add_summary_row(label: str, value: str, styles, color=BRAND_DARK):
    """Create a summary metric row as paragraphs."""
    elements = []
    row_data = [[
        Paragraph(label, styles["MetricLabel"]),
        Paragraph(value, ParagraphStyle(
            name=f"val_{label}",
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=color,
            alignment=TA_RIGHT,
        ))
    ]]
    t = Table(row_data, colWidths=[120 * mm, 50 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t)
    return elements


# ═══════════════════════════════════════════════════════════════════════════════
# DAILY PDF REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_pdf(summary_data: dict) -> str:
    """
    Generate a Daily Closing PDF Report.
    Returns the file path of the generated PDF.
    """
    report_date = summary_data.get("report_date", str(date.today()))
    filename = f"daily_report_{report_date}.pdf"
    filepath = str(REPORTS_DIR / filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=20 * mm, bottomMargin=15 * mm,
    )
    styles = _get_styles()
    elements = []

    # ── Title ──
    elements.append(Paragraph("⛽ PETROL PUMP ERP", styles["ReportTitle"]))
    elements.append(Paragraph(
        f"Daily Closing Report — {format_date(date.fromisoformat(str(report_date)))}",
        styles["ReportSubtitle"]
    ))
    salary_rows = []
    for sp in summary_data.get("salary_breakdown", []):
        salary_rows.append([
            sp.get("employee_name", ""),
            format_currency(sp.get("amount", 0)),
            str(sp.get("paid_date", "")),
        ])
    if salary_rows:
        elements.append(Paragraph("SALARY PAYMENTS", styles["SectionHeader"]))
        elements.append(_build_table(
            ["Employee", "Amount", "Date"],
            salary_rows,
            col_widths=[70 * mm, 45 * mm, 55 * mm]
        ))
    elements.extend(_add_summary_row(
        "Total Salary Given", format_currency(summary_data.get("total_salaries", 0)),
        styles
    ))
    elements.append(Spacer(1, 4 * mm))

    elements.append(HRFlowable(
        width="100%", thickness=1, color=BRAND_BORDER, spaceAfter=4 * mm
    ))

    # ── Sales Summary ──
    elements.append(Paragraph("SALES SUMMARY", styles["SectionHeader"]))
    elements.extend(_add_summary_row(
        "Total Sales", format_currency(summary_data.get("total_sales", 0)),
        styles, BRAND_DARK
    ))
    elements.extend(_add_summary_row(
        "Total Litres Sold", format_litres(summary_data.get("total_litres_sold", 0)),
        styles
    ))
    elements.append(Spacer(1, 3 * mm))

    # Fuel breakdown table
    fuel_rows = []
    for fb in summary_data.get("fuel_breakdown", []):
        fuel_rows.append([
            fb.get("fuel_type", ""),
            format_litres(fb.get("litres_sold", 0)),
            format_currency(fb.get("sales_amount", 0)),
            format_currency(fb.get("purchase_cost_per_litre", 0)),
            format_currency(fb.get("profit", 0)),
        ])
    if fuel_rows:
        elements.append(_build_table(
            ["Fuel Type", "Litres Sold", "Sales Amount", "Purchase Rate/L", "Profit"],
            fuel_rows,
            col_widths=[35 * mm, 30 * mm, 35 * mm, 35 * mm, 35 * mm]
        ))
        elements.append(Spacer(1, 4 * mm))

    # Nozzle breakdown table
    nozzle_rows = []
    for nb in summary_data.get("nozzle_breakdown", []):
        nozzle_rows.append([
            f"Nozzle {nb.get('nozzle_number', '')}",
            f"Shift {nb.get('shift_number', '')}",
            nb.get("fuel_type", ""),
            format_litres(nb.get("litres_sold", 0)),
            format_currency(nb.get("sales_amount", 0)),
        ])
    if nozzle_rows:
        elements.append(Paragraph("NOZZLE-WISE BREAKDOWN", styles["SectionHeader"]))
        elements.append(_build_table(
            ["Nozzle", "Shift", "Fuel Type", "Litres", "Sales"],
            nozzle_rows,
            col_widths=[30 * mm, 25 * mm, 35 * mm, 35 * mm, 40 * mm]
        ))
        elements.append(Spacer(1, 4 * mm))

    # ── Payments ──
    elements.append(Paragraph("PAYMENT COLLECTIONS", styles["SectionHeader"]))
    pay_rows = []
    for pb in summary_data.get("payment_breakdown", []):
        pay_rows.append([pb.get("method", ""), format_currency(pb.get("amount", 0))])
    if pay_rows:
        elements.append(_build_table(
            ["Payment Method", "Amount Collected"],
            pay_rows,
            col_widths=[80 * mm, 90 * mm]
        ))
    elements.extend(_add_summary_row(
        "Total Collections", format_currency(summary_data.get("total_payments", 0)),
        styles
    ))
    elements.extend(_add_summary_row(
        "Expected Cash Collection",
        format_currency(summary_data.get("expected_cash_collection", 0)),
        styles
    ))
    elements.extend(_add_summary_row(
        "Actual Cash Collection",
        format_currency(summary_data.get("cash_collection", 0)),
        styles
    ))

    shortfall = summary_data.get("payment_shortfall", 0)
    if shortfall < 0:
        elements.extend(_add_summary_row(
            "⚠ SHORTFALL",
            format_currency(abs(shortfall)),
            styles, BRAND_DANGER
        ))
    elements.append(Spacer(1, 4 * mm))

    # ── Expenses ──
    elements.append(Paragraph("EXPENSES", styles["SectionHeader"]))
    exp_rows = []
    for eb in summary_data.get("expense_breakdown", []):
        exp_rows.append([eb.get("category", ""), format_currency(eb.get("amount", 0))])
    if exp_rows:
        elements.append(_build_table(
            ["Category", "Amount"],
            exp_rows,
            col_widths=[80 * mm, 90 * mm]
        ))
    elements.extend(_add_summary_row(
        "Total Expenses", format_currency(summary_data.get("total_expenses", 0)),
        styles
    ))
    elements.append(Spacer(1, 4 * mm))

    # ── Profit ──
    elements.append(HRFlowable(
        width="100%", thickness=1, color=BRAND_BORDER, spaceAfter=3 * mm
    ))
    elements.extend(_add_summary_row(
        "Gross Profit", format_currency(summary_data.get("gross_profit", 0)),
        styles, BRAND_SUCCESS
    ))
    net_profit = summary_data.get("net_profit", 0)
    profit_color = BRAND_SUCCESS if net_profit >= 0 else BRAND_DANGER
    elements.extend(_add_summary_row(
        "NET PROFIT", format_currency(net_profit),
        styles, profit_color
    ))

    # Build the PDF
    doc.build(elements)
    return filepath


# ═══════════════════════════════════════════════════════════════════════════════
# MONTHLY PDF REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_monthly_pdf(summary_data: dict) -> str:
    """
    Generate a Monthly Financial Summary PDF Report.
    Returns the file path of the generated PDF.
    """
    month = summary_data.get("month", 1)
    year = summary_data.get("year", 2026)
    month_name = get_month_name(month)
    filename = f"monthly_report_{year}_{month:02d}.pdf"
    filepath = str(REPORTS_DIR / filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=20 * mm, bottomMargin=15 * mm,
    )
    styles = _get_styles()
    elements = []

    # ── Title ──
    elements.append(Paragraph("⛽ PETROL PUMP ERP", styles["ReportTitle"]))
    elements.append(Paragraph(
        f"Monthly Financial Summary — {month_name} {year}",
        styles["ReportSubtitle"]
    ))
    elements.append(HRFlowable(
        width="100%", thickness=1, color=BRAND_BORDER, spaceAfter=4 * mm
    ))

    # ── Sales ──
    elements.append(Paragraph("SALES OVERVIEW", styles["SectionHeader"]))
    elements.extend(_add_summary_row(
        "Total Sales Revenue",
        format_currency(summary_data.get("total_sales", 0)),
        styles
    ))
    elements.extend(_add_summary_row(
        "Total Litres Sold",
        format_litres(summary_data.get("total_litres_sold", 0)),
        styles
    ))
    elements.append(Spacer(1, 3 * mm))

    # Fuel breakdown
    fuel_rows = []
    for fb in summary_data.get("fuel_breakdown", []):
        fuel_rows.append([
            fb.get("fuel_type", ""),
            format_litres(fb.get("litres_sold", 0)),
            format_currency(fb.get("sales_amount", 0)),
            format_currency(fb.get("purchase_cost", 0)),
            format_currency(fb.get("profit", 0)),
        ])
    if fuel_rows:
        elements.append(_build_table(
            ["Fuel Type", "Litres Sold", "Sales", "Purchase Cost", "Profit"],
            fuel_rows,
            col_widths=[35 * mm, 30 * mm, 35 * mm, 35 * mm, 35 * mm]
        ))
    elements.append(Spacer(1, 4 * mm))

    # ── Cost of Goods ──
    elements.append(Paragraph("COST BREAKDOWN", styles["SectionHeader"]))
    elements.extend(_add_summary_row(
        "Total Purchase Cost",
        format_currency(summary_data.get("total_purchase_cost", 0)),
        styles
    ))
    elements.extend(_add_summary_row(
        "Daily Operational Expenses",
        format_currency(summary_data.get("total_daily_expenses", 0)),
        styles
    ))
    elements.extend(_add_summary_row(
        "Monthly Expenses (Rent etc.)",
        format_currency(summary_data.get("total_monthly_expenses", 0)),
        styles
    ))
    elements.extend(_add_summary_row(
        "Employee Salaries",
        format_currency(summary_data.get("total_salaries", 0)),
        styles
    ))
    elements.append(Paragraph("CASH RECONCILIATION", styles["SectionHeader"]))
    elements.extend(_add_summary_row(
        "Total Collections",
        format_currency(summary_data.get("total_payments", 0)),
        styles
    ))
    elements.extend(_add_summary_row(
        "Expected Cash Collection",
        format_currency(summary_data.get("expected_cash_collection", 0)),
        styles
    ))
    elements.extend(_add_summary_row(
        "Actual Cash Collection",
        format_currency(summary_data.get("cash_collection", 0)),
        styles
    ))
    cash_difference = summary_data.get("payment_shortfall", 0)
    elements.extend(_add_summary_row(
        "Cash Surplus" if cash_difference >= 0 else "Cash Shortfall",
        format_currency(cash_difference if cash_difference >= 0 else abs(cash_difference)),
        styles,
        BRAND_SUCCESS if cash_difference >= 0 else BRAND_DANGER
    ))
    elements.append(Spacer(1, 3 * mm))

    # Monthly expenses table
    monthly_exps = summary_data.get("monthly_expenses", [])
    if monthly_exps:
        exp_rows = []
        for me in monthly_exps:
            exp_rows.append([
                me.get("category", ""),
                format_currency(me.get("amount", 0)),
                me.get("description", "") or "-",
            ])
        elements.append(Paragraph("MONTHLY EXPENSES DETAIL", styles["SectionHeader"]))
        elements.append(_build_table(
            ["Category", "Amount", "Description"],
            exp_rows,
            col_widths=[50 * mm, 50 * mm, 70 * mm]
        ))
        elements.append(Spacer(1, 3 * mm))

    # Salaries table
    salaries = summary_data.get("salaries", [])
    if salaries:
        sal_rows = []
        for s in salaries:
            sal_rows.append([
                s.get("employee_name", ""),
                format_currency(s.get("monthly_salary", 0)),
                str(s.get("paid_date") or "-"),
            ])
        elements.append(Paragraph("SALARY PAYMENTS", styles["SectionHeader"]))
        elements.append(_build_table(
            ["Employee", "Amount", "Date"],
            sal_rows,
            col_widths=[70 * mm, 45 * mm, 55 * mm]
        ))
        elements.append(Spacer(1, 3 * mm))

    # ── Final Profit ──
    elements.append(HRFlowable(
        width="100%", thickness=1, color=BRAND_BORDER, spaceAfter=3 * mm
    ))
    elements.extend(_add_summary_row(
        "Gross Profit (Sales - Purchases)",
        format_currency(summary_data.get("gross_profit", 0)),
        styles, BRAND_SUCCESS
    ))
    net_profit = summary_data.get("net_profit", 0)
    profit_color = BRAND_SUCCESS if net_profit >= 0 else BRAND_DANGER
    elements.extend(_add_summary_row(
        "NET PROFIT / (LOSS)",
        format_currency(net_profit),
        styles, profit_color
    ))

    doc.build(elements)
    return filepath

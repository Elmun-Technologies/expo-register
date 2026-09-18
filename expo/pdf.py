"""
PDF hisobot — stend analitikasi va mehmonlar ro'yxatini
PDF ko'rinishida yuklab olish.

Cyrillic/o'zbekcha matnlar uchun DejaVu fontlaridan foydalanamiz.
"""

import io

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import analytics
from .models import Booth, ExpoVisitor

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"


def _register_fonts():
    """DejaVu fontlarini bir marta ro'yxatga olish."""
    if "DejaVuSans" in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont("DejaVu", FONT_DIR + "DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_DIR + "DejaVuSans-Bold.ttf"))


def build_booth_report_pdf():
    """Stend analitikasi PDF — barcha stendlar statistikasi."""
    _register_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title="Expo stend analitikasi",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleUz", parent=styles["Title"],
        fontName="DejaVu-Bold", fontSize=18,
        leading=22, spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "SubUz", parent=styles["Normal"],
        fontName="DejaVu", fontSize=9,
        textColor=colors.HexColor("#64748b"), spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "H2Uz", parent=styles["Heading2"],
        fontName="DejaVu-Bold", fontSize=12,
        leading=16, spaceBefore=10, spaceAfter=8,
    )
    cell_style = ParagraphStyle(
        "CellUz", parent=styles["Normal"],
        fontName="DejaVu", fontSize=8.5, leading=11,
    )
    head_style = ParagraphStyle(
        "HeadUz", parent=styles["Normal"],
        fontName="DejaVu-Bold", fontSize=9,
        textColor=colors.white, leading=11,
    )

    story = []
    now = timezone.localtime(timezone.now()).strftime("%d.%m.%Y %H:%M")
    story.append(Paragraph("Expo stend analitikasi", title_style))
    story.append(Paragraph(
        f"Hisobot sanasi: {now} · Expo Register tizimi",
        sub_style,
    ))

    overview = analytics.expo_overview()
    story.append(Paragraph("Umumiy ko'rsatkichlar", h2_style))
    summary = [
        [Paragraph("Ichkarida (hozir)", head_style), Paragraph("Jami mehmonlar", head_style),
         Paragraph("Kameralar", head_style)],
        [Paragraph(str(overview["active_visitors"]), cell_style),
         Paragraph(str(analytics_expo_total()), cell_style),
         Paragraph(f"{overview['cameras_online']}/{overview['cameras_total']}", cell_style)],
    ]
    t = Table(summary, colWidths=[60 * mm, 60 * mm, 60 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Stendlar bo'yicha statistika", h2_style))
    rows = [
        [Paragraph("#", head_style), Paragraph("Stend", head_style),
         Paragraph("Hudud", head_style), Paragraph("Mehmonlar", head_style),
         Paragraph("Tashriflar", head_style), Paragraph("O'rtacha vaqt (daq.)", head_style)],
    ]
    stats = analytics.all_booth_stats()
    stats.sort(key=lambda r: -r["unique_visitors"])
    for i, s in enumerate(stats, 1):
        rows.append([
            Paragraph(str(i), cell_style),
            Paragraph(s["booth"].name, cell_style),
            Paragraph(s["booth"].zone or "-", cell_style),
            Paragraph(str(s["unique_visitors"]), cell_style),
            Paragraph(str(s["visits"]), cell_style),
            Paragraph(str(s["avg_dwell_min"]), cell_style),
        ])
    t = Table(rows, colWidths=[10 * mm, 55 * mm, 50 * mm, 25 * mm, 22 * mm, 28 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    doc.build(story)
    return buf.getvalue()


def analytics_expo_total():
    return ExpoVisitor.objects.count()


def build_visitors_report_pdf():
    """Mehmonlar ro'yxati PDF."""
    _register_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title="Expo mehmonlar ro'yxati",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleUz", parent=styles["Title"],
        fontName="DejaVu-Bold", fontSize=18,
        leading=22, spaceAfter=4,
    )
    head_style = ParagraphStyle(
        "HeadUz", parent=styles["Normal"],
        fontName="DejaVu-Bold", fontSize=8.5,
        textColor=colors.white, leading=11,
    )
    cell_style = ParagraphStyle(
        "CellUz", parent=styles["Normal"],
        fontName="DejaVu", fontSize=8, leading=10,
    )

    story = []
    story.append(Paragraph("Expo mehmonlar ro'yxati", title_style))
    story.append(Paragraph(
        f"Jami: {ExpoVisitor.objects.count()} ta mehmon",
        ParagraphStyle("Sub", parent=styles["Normal"], fontName="DejaVu",
                       fontSize=9, textColor=colors.HexColor("#64748b"), spaceAfter=12),
    ))

    rows = [
        [Paragraph("#", head_style), Paragraph("F.I.Sh.", head_style),
         Paragraph("Kompaniya", head_style), Paragraph("Maqsad", head_style),
         Paragraph("Holat", head_style), Paragraph("Kirish", head_style)],
    ]
    for i, v in enumerate(ExpoVisitor.objects.order_by("-check_in_at")[:200], 1):
        rows.append([
            Paragraph(str(i), cell_style),
            Paragraph(v.full_name, cell_style),
            Paragraph(v.company or "-", cell_style),
            Paragraph(v.get_purpose_display(), cell_style),
            Paragraph("Ichkarida" if v.is_active else "Chiqib ketdi", cell_style),
            Paragraph(timezone.localtime(v.check_in_at).strftime("%d.%m.%Y %H:%M"), cell_style),
        ])
    t = Table(rows, colWidths=[10 * mm, 55 * mm, 48 * mm, 30 * mm, 24 * mm, 30 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    doc.build(story)
    return buf.getvalue()

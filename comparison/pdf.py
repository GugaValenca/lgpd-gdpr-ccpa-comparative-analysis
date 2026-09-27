"""
PDF export for the "Generate compliance summary" feature, built with
ReportLab (pure-Python, no system dependencies — chosen over WeasyPrint
specifically so this project runs cleanly on Windows without a GTK
install).

`render_scenario_pdf(context)` takes the same context dict produced by
`services.build_summary_context` and returns PDF bytes, so the HTML
result page and the PDF are always describing the same scenario.
"""

import io

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DISCLAIMER = (
    "This summary is generated from a simplified self-assessment questionnaire for "
    "informational and educational purposes only. It is not legal advice and does not "
    "create an attorney-client relationship. Applicability of any privacy law to a real "
    "business depends on its full facts and should be confirmed with qualified counsel "
    "and against the official statutory text."
)


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="DocTitle",
            fontSize=20,
            leading=24,
            spaceAfter=4,
            textColor=colors.HexColor("#1f2937"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubTitle",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#6b7280"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="LawHeading",
            fontSize=14,
            leading=18,
            spaceBefore=16,
            spaceAfter=6,
            textColor=colors.white,
            backColor=colors.HexColor("#334155"),
            leftIndent=6,
            borderPadding=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CategoryHeading",
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=2,
            textColor=colors.HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#6b7280"),
        )
    )
    return styles


def render_scenario_pdf(context):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title="Privacy Compliance Summary",
    )
    styles = _styles()
    story = []

    company_name = context.get("company_name") or "Your business"
    story.append(Paragraph("Privacy Compliance Summary", styles["DocTitle"]))
    story.append(
        Paragraph(
            f"Prepared for: {company_name}  |  Generated: {timezone.localdate().isoformat()}  |  "
            "LGPD / GDPR / CCPA Comparative Analysis tool",
            styles["SubTitle"],
        )
    )
    story.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb"), thickness=1))
    story.append(Spacer(1, 10))

    # Applicability overview table
    rows = [["Framework", "Applies?"]]
    row_colors = []
    for result in context["results"]:
        rows.append([result.law.code, "Yes" if result.applies else "No"])
        row_colors.append(result.applies)

    table = Table(rows, colWidths=[3 * inch, 2 * inch])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
    ]
    for i, applies in enumerate(row_colors, start=1):
        if applies:
            style.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#15803d")))
            style.append(("FONTNAME", (1, i), (1, i), "Helvetica-Bold"))
        else:
            style.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#6b7280")))
    table.setStyle(TableStyle(style))
    story.append(table)
    story.append(Spacer(1, 14))

    if not context["applicable"]:
        story.append(
            Paragraph(
                "Based on your answers, none of the three frameworks appear to be triggered. "
                "Review the questionnaire again if this seems unexpected — privacy law "
                "applicability is fact-specific.",
                styles["Body"],
            )
        )

    for section in context["sections"]:
        law = section["law"]
        story.append(Paragraph(f"{law.code} — {law.full_name}", styles["LawHeading"]))

        if section["matched_questions"]:
            reasons = "; ".join(section["matched_questions"])
            story.append(Paragraph(f"<b>Why it applies:</b> {reasons}", styles["Body"]))
            story.append(Spacer(1, 4))

        for entry in section["obligations"]:
            story.append(Paragraph(entry.category.name, styles["CategoryHeading"]))
            bullet_text = entry.summary
            if not entry.is_verified:
                bullet_text += " <font color='#b45309'>[unverified — confirm against primary source]</font>"
            story.append(
                ListFlowable(
                    [ListItem(Paragraph(bullet_text, styles["Body"]))],
                    bulletType="bullet",
                    leftIndent=14,
                )
            )
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb"), thickness=1))
    story.append(Spacer(1, 8))
    story.append(Paragraph(DISCLAIMER, styles["Small"]))

    doc.build(story)
    return buffer.getvalue()

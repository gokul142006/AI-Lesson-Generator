"""
pdf_export.py
----------------
Generates a professionally formatted PDF lesson plan using ReportLab.
Returns raw bytes so the Streamlit layer can feed them straight into
st.download_button.
"""

from __future__ import annotations

import io
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils import SECTION_SCHEMA, markdown_to_plain_lines

try:
    from excel_export import ExportError
except ImportError:  # pragma: no cover
    class ExportError(Exception):
        def __init__(self, user_message: str):
            super().__init__(user_message)
            self.user_message = user_message


PRIMARY_COLOR = colors.HexColor("#1F3B57")
ACCENT_COLOR = colors.HexColor("#F5F7FA")


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="LessonTitle",
            fontSize=22,
            leading=26,
            textColor=PRIMARY_COLOR,
            spaceAfter=6,
            alignment=1,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            fontSize=13,
            leading=16,
            textColor=colors.white,
            spaceBefore=14,
            spaceAfter=6,
            backColor=PRIMARY_COLOR,
            leftIndent=4,
            borderPadding=(4, 4, 4, 4),
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTextCustom",
            fontSize=10.5,
            leading=15,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaText",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#333333"),
        )
    )
    return styles


def build_pdf(lesson: Dict[str, Any], meta: Dict[str, Any]) -> bytes:
    """Build the PDF document in memory and return its bytes."""
    try:
        styles = _build_styles()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=1.8 * cm,
            bottomMargin=1.8 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            title=lesson.get("lesson_title") or "Lesson Plan",
        )

        story = []

        title = lesson.get("lesson_title") or "Lesson Plan"
        story.append(Paragraph(title, styles["LessonTitle"]))
        story.append(Spacer(1, 6))

        # --- Metadata table --------------------------------------------------
        meta_data = [
            ["Subject", meta.get("subject", "")],
            ["Grade", meta.get("grade", "")],
            ["Topic", meta.get("topic", "")],
            ["Duration", meta.get("duration", "")],
        ]
        meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), ACCENT_COLOR),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # --- Sections ----------------------------------------------------------
        for key, label in SECTION_SCHEMA:
            if key == "lesson_title":
                continue
            content = lesson.get(key, "")
            if not content:
                continue

            story.append(Paragraph(label, styles["SectionHeading"]))
            for line in markdown_to_plain_lines(content):
                if not line.strip():
                    story.append(Spacer(1, 4))
                    continue
                safe_line = (
                    line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
                story.append(Paragraph(safe_line, styles["BodyTextCustom"]))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as exc:
        raise ExportError(f"Could not generate the PDF file: {exc}")

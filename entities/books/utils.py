import csv
import io
import json
from datetime import timedelta, date
from typing import Sequence

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PATH = "C:\Windows\Fonts\Arial.ttf"

pdfmetrics.registerFont(TTFont("Arial", FONT_PATH))


def calculate_streak(reading_dates: Sequence[date]) -> int:
    if not reading_dates:
        return 0
    today = date.today()
    yesterday = today - timedelta(days=1)

    if reading_dates[0] != today and reading_dates[0] != yesterday:
        return 0

    streak = 0
    current_check = reading_dates[0]

    for d in reading_dates:
        if d == current_check:
            streak += 1
            current_check -= timedelta(days=1)
        elif d < current_check:
            break
    return streak


def generate_csv_export(data: list[dict], include_notes: bool) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)

    headers = ["Назва", "Автори", "Жанри", "Статус"]

    if include_notes:
        headers.append("Замітки")

    writer.writerow(headers)

    for item in data:
        row = [item["title"], item["authors"], item["genres"], item["status"]]

        if include_notes:
            row.append(" | ".join(item.get("notes", [])))
        writer.writerow(row)

    return output.getvalue().encode("utf-8-sig")


def generate_json_export(data: list[dict]) -> bytes:
    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def generate_pdf_export(data: list[dict]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        name="TitleStyle",
        fontName="Arial",
        fontSize=18,
        leading=22,
        bold=True,
    )

    normal_style = ParagraphStyle(
        name="CustomNormal",
        fontName="Arial",
        fontSize=10,
        leading=14,
    )
    story.append(Paragraph("Експорт бібліотеки ReaderLove", title_style))
    story.append(Spacer(1, 12))

    for idx, item in enumerate(data, start=1):
        text = f"<b>{idx}. {item['title']}</b> - {item['authors']} <i>({item['status']})</i>"

        story.append(Paragraph(text, normal_style))

        if item.get("notes"):
            story.append(
                Paragraph(f"<b>Замітки:</b> {'; '.join(item['notes'])}", normal_style)
            )

        story.append(Spacer(1, 8))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

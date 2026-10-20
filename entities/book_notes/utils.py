import csv
import os
import json
import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PATH = os.getenv("FONT_PATH")

try:
    if FONT_PATH and os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont("Arial", FONT_PATH))
    else:
        print(f"Попередження: FONT_PATH не знайдено або файл не існує: {FONT_PATH}")
except Exception as e:
    print(f"Помилка при реєстрації шрифту: {e}")


def generate_notes_csv_export(data: list[dict]) -> bytes:
    output = io.StringIO()
    if not data:
        return output.getvalue().encode("utf-8-sig")

    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    return output.getvalue().encode("utf-8-sig")


def generate_notes_json_export(data: list[dict]) -> bytes:
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    return json_str.encode("utf-8")


def generate_noted_pdf_export(data: list[dict], username: str = "Користувач") -> bytes:
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    registered_fonts = pdfmetrics.getRegisteredFontNames()
    font_name = "Arial" if "Arial" in registered_fonts else "Helvetica"

    margin = 40
    y = height - margin

    def draw_header():
        nonlocal y
        p.setFont(font_name, 10)
        p.setFillColor(colors.HexColor("#ff3b69"))
        p.drawString(margin, y, "ExLove - Експорт нотаток")

        export_date = datetime.now().strftime("%d.%m.%Y")
        p.setFillColor(colors.HexColor("#6b7280"))
        p.drawRightString(width - margin, y, f"Дата: {export_date}")

        y -= 15
        p.setFont(font_name, 18)
        p.setFillColor(colors.HexColor("#111827"))
        p.drawString(margin, y, f"Нотатки та цитати: {username}")

        y -= 10
        p.setStrokeColor(colors.HexColor("#e5e7eb"))
        p.setLineWidth(1)
        p.line(margin, y, width - margin, y)
        y -= 15

    draw_header()

    for item in data:
        if y < 80:
            p.showPage()
            y = height - margin
            draw_header()

        book_title = str(item.get("book_title") or item.get("book_tilte", "Без назви"))
        category = str(item.get("category", ""))
        page = str(item.get("book_page", "-"))
        note_text = str(item.get("note_text", ""))[:90]

        p.setFont(font_name, 10)
        p.setFillColor(colors.HexColor("#4b5563"))
        meta_info = f"📚 {book_title}  |  🏷️ {category}"

        if page != "-":
            meta_info += f"  |  📖 Стор. {page}"
        p.drawString(margin, y, meta_info)
        y -= 15

        p.setFont(font_name, 11)
        p.setFillColor(colors.HexColor("#1f2937"))

        max_length = 100
        if len(note_text) > max_length:
            note_text_display = note_text[:max_length] + "..."
        else:
            note_text_display = note_text

        p.drawString(margin + 10, y, f'"{note_text_display}"')
        y -= 25

        p.setStrokeColor(colors.HexColor("#f3f4f6"))
        p.line(margin, y + 10, width - margin, y + 10)
        y -= 10

    p.save()
    buffer.seek(0)
    return buffer.getvalue()

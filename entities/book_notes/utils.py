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
    content_width = width - (margin * 2)

    def draw_background_and_header():
        p.setFillColor(colors.HexColor("#12111"))
        p.rect(0, height - 90, width, 90, stroke=0, fill=1)

        p.setFont(font_name, 10)
        p.setFillColor(colors.HexColor("#ff3b69"))
        p.drawString(margin, height - 15, "ExLove • АРХІВ НОТАТОК ТА ЦИТАТ")

        p.setFont(font_name, 16)
        p.setFillColor(colors.white)
        p.drawString(margin, height - 60, f"Користувач: {username}")

        export_date = datetime.now().strftime("%d.%m.%Y")
        p.setFont(font_name, 9)
        p.setFillColor(colors.HexColor("#9ca3af"))
        p.drawRightString(width - margin, height - 55, f"Дата: {export_date}")

    draw_background_and_header()
    y = height - 120

    for index, item in enumerate(data, 1):
        if y < 90:
            p.showPage()
            draw_background_and_header()
            y = height - 120

        book_title = str(item.get("book_title") or item.get("book_tilte", "Без назви"))
        category = str(item.get("category", ""))
        page = str(item.get("book_page", "-"))
        note_text = str(item.get("note_text", ""))

        card_height = 55
        card_y = y - card_height

        p.setFillColor(colors.HexColor("#f9fafb"))
        p.setStrokeColor(colors.HexColor("#e5e7eb"))
        p.setLineWidth(0.5)
        p.roundRect(margin, card_y, content_width, card_height, 6, stroke=1, fill=1)

        p.setFillColor(colors.HexColor("#ff3b69"))
        p.rect(margin, card_y, 4, card_height, stroke=0, fill=1)

        p.setFont(font_name, 8)
        p.setFillColor(colors.HexColor("#6b7280"))
        meta_parts = [f"Книга: {book_title}", f"Категорія: {category}"]

        if page != "-":
            meta_parts.append(f"Стор. {page}")
        p.drawString(margin + 15, card_y + card_height - 15, "  •  ".join(meta_parts))

        p.setFont(font_name, 10)
        p.setFillColor(colors.HexColor("#1f2937"))

        max_length = 100
        note_text_display = (
            (note_text[:max_length] + "...")
            if len(note_text) > max_length
            else note_text
        )
        p.drawString(margin + 15, card_y + card_height - 35, f'"{note_text_display}"')

        y = card_y - 12

    p.save()
    buffer.seek(0)
    return buffer.getvalue()

import csv
import os
import json
import io

from reportlab.lib.pagesizes import letter
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


def generate_noted_pdf_export(data: list[dict]) -> bytes:
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    registered_fonts = pdfmetrics.getRegisteredFontNames()
    font_name = "Arial" if "Arial" in registered_fonts else "Helvetica"

    p.setFont(font_name, 14)
    y = height - 40
    p.drawString(40, y, "Експорт нотаток користувача")
    y -= 30

    p.setFont(font_name, 10)

    for item in data:
        if y < 50:
            p.showPage()
            y = height - 40
            p.setFont(font_name, 10)

        book_title = str(item.get("book_title") or item.get("book_tilte", "Без назви"))
        category = str(item.get("category", ""))
        page = str(item.get("book_page", "-"))
        note_text = str(item.get("note_text", ""))[:90]

        line = f"Книга: {book_title} | Категорія: {category} | Стор: {page}"
        p.drawString(40, y, line)
        y -= 15
        p.drawString(40, y, f"Текст: {note_text}...")
        y -= 25

    p.save()
    buffer.seek(0)
    return buffer.getvalue()

import os

import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


async def detect_spoiler_with_ai(review_text: str, book_title: str) -> bool:
    if not review_text or len(review_text.strip()) < 15:
        return False

    prompt = f"""
        Ти — модератор книжкового клубу. Проаналізуй відгук до книги "{book_title}".
        Відгук: "{review_text}"
    
        Визнач, чи містить цей відгук ключові сюжетні спойлери або розв'язку.
        Поверни відповідь СТРЕДЖНО У ФОРМАТІ JSON з ключем "is_spoiler" (boolean: true або false).
    """

    try:
        model_name = os.getenv("GEMINI_MODEL")

        response = await client.aio.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

        if response.text:
            data = json.loads(response.text)
            logger.warning(data)
            return bool(data.get("is_spoiler", False))
        return False

    except Exception as e:
        logger.error(f"Помилка при перевірці спойлерів: {e}")
        return False

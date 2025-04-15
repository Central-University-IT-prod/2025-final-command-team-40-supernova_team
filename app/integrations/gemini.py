import logging
import os

from fastapi import HTTPException
from openai import OpenAI

logger = logging.getLogger(__name__)

API_KEY = os.environ["AI_API_KEY"]
MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"

PROMPT = """
Hi, can you give me 5 themes for discussion about film named {film_name} {year}?
Only give me themes numerated from 1 to 5 and nothing else.
Ответь на русском языке.
После конца каждой темы ставь символ $ и не переходи на следующую строку
"""

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)


def get_discussions(film_name: str, year: int) -> list[str]:
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(film_name=film_name, year=year),
                },
            ],
        )

        text = completion.choices[0].message.content

        logger.info("Response from AI:\n%s", text)

        if text is None:
            text = "Sorry, couldn't find any discussion options for you :("

        # Except last empty string
        themes = [x.strip() for x in text.split("$")][:-1]

    except Exception as e:
        raise HTTPException(status_code=500, detail="OpenAI API error") from e

    else:
        return themes

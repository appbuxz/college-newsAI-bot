import json
import logging
from openai import OpenAI
from config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

try:
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    AI_AVAILABLE = True
    logger.info("OpenRouter клиент успешно создан")
except Exception as e:
    logger.error(f"Не удалось создать OpenRouter клиент: {e}")
    client = None
    AI_AVAILABLE = False

MODEL = "openrouter/auto"

TYPE_ICONS = {
    "экзамен": "📝",
    "дедлайн": "⏰",
    "мероприятие": "🎓",
    "объявление": "📢",
}

PRIORITY_ICONS = {
    "высокая": "🔴",
    "средняя": "🟡",
    "низкая": "🟢",
}


async def format_message(text: str) -> str:
    if not AI_AVAILABLE:
        return text

    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": "Сократи сообщение и сделай его понятным для студентов. Без лишнего текста."
                },
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"format_message ошибка: {e}")
        return text



async def classify_message(text: str) -> dict:
    fallback = {
        "type": "объявление",
        "event_date": None,
        "priority": "средняя",
        "formatted_text": text
    }

    if not AI_AVAILABLE:
        return fallback

    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": """Ты классификатор сообщений.

Верни строго JSON:

{
  "type": "экзамен | дедлайн | мероприятие | объявление",
  "event_date": "дата или null",
  "priority": "высокая | средняя | низкая",
  "formatted_text": "короткий текст"
}

Не добавляй ничего лишнего и не выдумывай."""
                },
                {"role": "user", "content": text}
            ]
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        result = json.loads(raw)

        return {
            "type": result.get("type", "объявление"),
            "event_date": result.get("event_date"),
            "priority": result.get("priority", "средняя"),
            "formatted_text": result.get("formatted_text", text)
        }

    except Exception as e:
        logger.error(f"classify_message ошибка: {e}")
        return fallback


def build_context_text(announcements: list) -> str:
    if not announcements:
        return ""

    lines = []

    for ann in announcements:
        type_, date, priority, text, sent_at = ann
        icon = TYPE_ICONS.get(type_, "📢")

        line = f"{icon} [{type_}]"
        if date:
            line += f" {date}:"
        line += f" {text}"

        lines.append(line)

    return "\n".join(lines)


async def answer_student_question(
    question: str,
    student_name: str,
    group_name: str,
    announcements: list,
    history: list = []
) -> str:

    context = build_context_text(announcements)

    if not AI_AVAILABLE or not client:
        if not announcements:
            return "📭 Нет объявлений."
        return f"📋 Объявления:\n\n{context}"

    try:
        system_prompt = f"""
Ты помощник студента.

ВАЖНЫЕ ПРАВИЛА:
- Отвечай ТОЛЬКО на текущий вопрос
- НЕ объединяй ответы с предыдущими вопросами
- НЕ делай списки, если пользователь не просил
- НЕ повторяй старые ответы
- НЕ добавляй лишнюю информацию
- НЕ выдумывай факты

Если вопрос:
- про экзамены/объявления → используй только данные ниже
- общий (химия, факты, подготовка и т.п) → отвечай своими знаниями

Если информации нет → напиши "информации нет"

Объявления:
{context if context else "нет"}

Ответ:
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]

        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.3,
            messages=messages
        )

        answer = response.choices[0].message.content.strip()

        return answer

    except Exception as e:
        logger.error(f"answer_student_question ошибка: {e}")

        if not announcements:
            return "📭 Нет объявлений."

        return f"📋 Объявления:\n\n{context}"
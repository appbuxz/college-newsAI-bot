import json
import logging
from datetime import datetime, date
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


def parse_date_safe(date_str):
    if not date_str:
        return None

    formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            pass

    return None


async def format_message(text: str) -> str:
    if not AI_AVAILABLE:
        return text

    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": """
Ты сокращаешь сообщения для студентов колледжа.

ПРАВИЛА:
- Только русский язык.
- Коротко и понятно.
- Не меняй смысл.
- Не придумывай информацию.
- Без английского.
- Без комментариев в скобках.
"""
                },
                {"role": "user", "content": text}
            ]
        )

        result = response.choices[0].message.content.strip()

        banned = [
            "(Answer given in Russian)",
            "(Translated)",
            "(Based on context)"
        ]

        for phrase in banned:
            result = result.replace(phrase, "")

        return result.strip()

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
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": """
Ты классификатор сообщений колледжа.

Верни СТРОГО JSON.
Без markdown.
Без пояснений.
Без ```json.

Формат:
{
  "type": "экзамен | дедлайн | мероприятие | объявление",
  "event_date": "YYYY-MM-DD или null",
  "priority": "высокая | средняя | низкая",
  "formatted_text": "краткий текст"
}

ПРАВИЛА:
- Не придумывай даты.
- Не придумывай типы.
- Только русский язык.
"""
                },
                {"role": "user", "content": text}
            ]
        )

        raw = response.choices[0].message.content.strip()

        raw = (
            raw
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

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
    """
    Формирует контекст только из актуальных объявлений.
    """

    if not announcements:
        return ""

    today = date.today()

    lines = []

    for ann in announcements:
        try:
            type_, event_date, priority, text, sent_at = ann

            parsed_date = parse_date_safe(event_date)

            # пропускаем старые события
            if parsed_date and parsed_date < today:
                continue

            icon = TYPE_ICONS.get(type_, "📢")

            line = f"{icon} [{type_}]"

            if parsed_date:
                line += f" {parsed_date.strftime('%d.%m.%Y')}:"

            line += f" {text}"

            lines.append(line)

        except Exception as e:
            logger.error(f"Ошибка обработки объявления: {e}")

    return "\n".join(lines)


async def answer_student_question(
    question: str,
    student_name: str,
    group_name: str,
    announcements: list,
    history: list = []
) -> str:

    context = build_context_text(announcements)

    today_str = date.today().strftime("%d.%m.%Y")

    if not AI_AVAILABLE or not client:
        if not announcements:
            return "📭 Нет объявлений."

        return f"📋 Объявления:\n\n{context}"

    try:

        system_prompt = f"""
Ты помощник студента колледжа в Казахстане.

СТУДЕНТ:
Имя: {student_name}
Группа: {group_name}

СЕГОДНЯ:
{today_str}

АКТУАЛЬНЫЕ ОБЪЯВЛЕНИЯ:
{context if context else "Объявлений нет"}

ПРАВИЛА:

1. ЯЗЫК
- Отвечай строго на языке пользователя.
- Русский -> русский.
- Казахский -> казахский.
- Английский запрещён.

2. ОБЪЯВЛЕНИЯ И ВОПРОСЫ

- Если вопрос связан с:
  экзаменами,
  дедлайнами,
  расписанием группы,
  объявлениями колледжа —
  используй ТОЛЬКО объявления выше.

- Если в объявлениях нет информации по таким вопросам —
  так и скажи:
  "В объявлениях нет информации."

- Если вопрос ОБЩИЙ:
  праздники,
  выходные,
  календарь,
  погода,
  учёба,
  предметы,
  помощь,
  теория,
  советы —
  отвечай используя свои знания или общую информацию из интернета.

3. СТИЛЬ
- Коротко.
- Чётко.
- Без воды.
- Без markdown.
- Без скобок.
- Без служебных комментариев.

4. ОБЩИЕ ВОПРОСЫ
- Если вопрос не связан с объявлениями —
  отвечай своими знаниями.

5. ИСТОРИЯ
- Учитывай историю сообщений.
"""

        history_without_last = history[:-1] if history else []

        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },

                *history_without_last,

                {
                    "role": "user",
                    "content": question
                }
            ]
        )

        result = response.choices[0].message.content.strip()

        banned = [
            "(Answer given in Russian)",
            "(Translated)",
            "(Based on context)"
        ]

        for phrase in banned:
            result = result.replace(phrase, "")

        return result.strip()

    except Exception as e:
        logger.error(f"answer_student_question ошибка: {e}")

        if not announcements:
            return "📭 Нет объявлений."

        return f"📋 Объявления:\n\n{context}"
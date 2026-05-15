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

COLLEGE_KEYWORDS = [
    "экзамен",
    "экзы",
    "сессия",
    "дедлайн",
    "зачет",
    "зачёт",
    "пара",
    "расписание",
    "объявление",
    "куратор",
    "группа",
    "кабинет",
    "препод",
    "преподаватель",
]

# Общие вопросы
GENERAL_KEYWORDS = [
    "выходной",
    "выходные",
    "праздник",
    "календарь",
    "май",
    "июнь",
    "июль",
    "август",
    "сегодня",
    "завтра",
    "погода",
]


def is_college_question(text: str) -> bool:
    text = text.lower()

    return any(word in text for word in COLLEGE_KEYWORDS)


def is_general_question(text: str) -> bool:
    text = text.lower()

    return any(word in text for word in GENERAL_KEYWORDS)


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
Ты сокращаешь сообщения для студентов.

ПРАВИЛА:
- Только русский язык.
- Коротко.
- Без воды.
- Не придумывай информацию.
"""
                },
                {
                    "role": "user",
                    "content": text
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
Верни только JSON.

{
  "type": "экзамен | дедлайн | мероприятие | объявление",
  "event_date": "YYYY-MM-DD или null",
  "priority": "высокая | средняя | низкая",
  "formatted_text": "краткий текст"
}
"""
                },
                {
                    "role": "user",
                    "content": text
                }
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

    today = date.today()

    lines = []

    for ann in announcements:
        try:
            type_, event_date, priority, text, sent_at = ann

            parsed_date = parse_date_safe(event_date)

            # скрываем старые события
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

    today_str = date.today().strftime("%d.%m.%Y")
    college_question = is_college_question(question)
    general_question = is_general_question(question)

    context = build_context_text(announcements) if college_question else ""

    if not AI_AVAILABLE or not client:

        if college_question:
            if not context:
                return "В объявлениях нет информации."

            return context

        return "Не удалось получить ответ."

    try:

        # ------------------------
        # ПРОМПТ ДЛЯ КОЛЛЕДЖА
        # ------------------------

        if college_question:

            system_prompt = f"""
Ты помощник студента колледжа Казахстана.

Сегодня: {today_str}

Студент: {student_name}
Группа: {group_name}

АКТУАЛЬНЫЕ ОБЪЯВЛЕНИЯ:
{context if context else "Объявлений нет"}

ПРАВИЛА:
- Используй ТОЛЬКО объявления.
- Не придумывай даты.
- Не придумывай экзамены.
- Если информации нет —
  ответь:
  "В объявлениях нет информации."

- Отвечай кратко.
- Только на языке пользователя.
- Без английского.
"""

        # ------------------------
        # ПРОМПТ ДЛЯ ОБЩИХ ВОПРОСОВ
        # ------------------------

        else:

            system_prompt = f"""
Ты полезный помощник студента в Казахстане.

Сегодня: {today_str}

ПРАВИЛА:
- Отвечай на языке пользователя.
- Можно использовать свои знания.
- Если вопрос про праздники или выходные —
  отвечай по календарю Казахстана.
- Отвечай кратко и понятно.
- Без английского.
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

        return "Ошибка получения ответа."
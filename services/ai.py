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
    """Форматирует сообщение для студентов"""
    if not AI_AVAILABLE:
        return text
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Сократи и сделай сообщение понятным для студентов. Отвечай на русском."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"format_message ошибка: {e}")
        return text


async def classify_message(text: str) -> dict:
    """
    Классифицирует сообщение администратора.
    Без AI — возвращает базовую классификацию с оригинальным текстом.
    """
    fallback = {
        "type": "объявление",
        "event_date": None,
        "priority": "средняя",
        "formatted_text": text
    }

    if not AI_AVAILABLE:
        logger.warning("classify_message: AI недоступен, возвращаю fallback")
        return fallback

    try:
        logger.info(f"classify_message: отправляю в OpenRouter: {text[:60]}")
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """Ты помощник для учебного заведения. Проанализируй сообщение и верни JSON:
{
  "type": одно из ["экзамен", "дедлайн", "мероприятие", "объявление"],
  "event_date": дата если есть (например "15 мая"), иначе null,
  "priority": одно из ["высокая", "средняя", "низкая"],
  "formatted_text": краткое понятное сообщение для студентов
}
Отвечай ТОЛЬКО JSON, без пояснений."""
                },
                {"role": "user", "content": text}
            ]
        )

        raw = response.choices[0].message.content.strip()
        logger.info(f"classify_message: ответ: {raw[:100]}")

        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        result.setdefault("type", "объявление")
        result.setdefault("event_date", None)
        result.setdefault("priority", "средняя")
        result.setdefault("formatted_text", text)

        return result

    except json.JSONDecodeError as e:
        logger.error(f"classify_message: не удалось распарсить JSON: {e}")
        return fallback
    except Exception as e:
        logger.error(f"classify_message: ошибка: {e}")
        return fallback


def build_context_text(announcements: list) -> str:
    """Формирует текстовый контекст из объявлений"""
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
    """
    Отвечает на вопрос студента с учётом истории чата.
    Без AI — возвращает список последних объявлений.
    """
    context = build_context_text(announcements)

    if not AI_AVAILABLE or not client:
        logger.warning("answer_student_question: AI недоступен")
        if not announcements:
            return "📭 Для вашей группы пока нет объявлений."
        return (
            f"📋 Последние объявления для группы {group_name}:\n\n"
            f"{context}\n\n"
            "💡 ИИ-ассистент недоступен, показываю все объявления."
        )

    try:
        system_prompt = f"""Ты умный помощник студента учебного заведения.
Студент: {student_name}, группа: {group_name}.

Вот последние объявления для его группы:
{context if context else "Объявлений пока нет."}
Как отвечать:
- На вопросы об объявлениях, экзаменах, дедлайнах — используй данные выше.
- На общие вопросы (химия, математика, история, даты,как готовиться к экзамену, какой день недели, объяснение темы и т.п) — отвечай используя поиск в интернете, не давая ссылок на ресурсы, или свои знания.
- Отвечай чётко и по существу, без лишних слов и воды.
- Если знаешь ответ — давай его сразу, не отправляй искать в учебниках, ищи сам.
- Короткий вопрос = короткий,но понятный ответ. Развёрнутый вопрос = развёрнутый ответ.
- Учитывай историю переписки — если студент ссылается на предыдущий вопрос, понимай контекст.
- Отвечай коротко и по делу, на языке, на котором задали вопрос."""

        logger.info(f"answer_student_question: вопрос от {student_name}: {question[:60]}")

        history_without_last = history[:-1] if history else []

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *history_without_last,
                {"role": "user", "content": question}
            ]
        )

        answer = response.choices[0].message.content
        logger.info(f"answer_student_question: ответ: {answer[:100]}")
        return answer

    except Exception as e:
        logger.error(f"answer_student_question: ошибка: {e}")
        if not announcements:
            return "📭 Для вашей группы пока нет объявлений."
        return (
            f"📋 Последние объявления для группы {group_name}:\n\n"
            f"{context}\n\n"
            "💡 ИИ-ассистент временно недоступен, показываю все объявления."
        )
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from database import get_all_users, get_users_by_group, save_announcement, get_announcements
from services.ai import classify_message
from keyboards.admin import admin_kb, cancel_kb

router = Router()

# Иконки для типов и приоритетов
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


class AdminStates(StatesGroup):
    # Рассылка всем
    waiting_for_broadcast = State()
    confirming_broadcast = State()

    # Рассылка по группе
    waiting_for_group_name = State()
    waiting_for_group_message = State()
    confirming_group_broadcast = State()

    viewing_group = State()

    # Добавление пользователя
    adding_user_name = State()
    adding_user_group = State()
    adding_user_id = State()

    # Удаление пользователя
    deleting_user = State()


def format_preview(classified: dict) -> str:
    """Формирует красивое превью классификации"""
    type_ = classified.get("type", "объявление")
    date = classified.get("event_date")
    priority = classified.get("priority", "средняя")
    text = classified.get("formatted_text", "")

    type_icon = TYPE_ICONS.get(type_, "📢")
    priority_icon = PRIORITY_ICONS.get(priority, "🟡")

    preview = f"🤖 <b>ИИ проанализировал сообщение:</b>\n\n"
    preview += f"{type_icon} <b>Тип:</b> {type_.capitalize()}\n"
    if date:
        preview += f"📅 <b>Дата:</b> {date}\n"
    preview += f"{priority_icon} <b>Важность:</b> {priority.capitalize()}\n\n"
    preview += f"📨 <b>Текст для студентов:</b>\n{text}\n\n"
    preview += "──────────────────\n"
    preview += "Отправить это сообщение?"

    return preview


# ------------------ АДМИН-ПАНЕЛЬ ------------------

@router.message(lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "/admin")
async def admin_panel(message: types.Message):
    await message.answer("Админ-панель:", reply_markup=admin_kb)


# ------------------ РАССЫЛКА ВСЕМ ------------------

@router.message(lambda msg: msg.text == "📢 Рассылка всем" and msg.from_user.id == ADMIN_ID)
async def broadcast_start(message: types.Message, state: FSMContext):
    await message.answer("Введите сообщение для рассылки:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_broadcast)


@router.message(AdminStates.waiting_for_broadcast)
async def broadcast_classify(message: types.Message, state: FSMContext):
    await message.answer("⏳ Анализирую сообщение...")

    classified = await classify_message(message.text)
    await state.update_data(
        original_text=message.text,
        classified=classified,
        target="all"
    )

    preview = format_preview(classified)

    confirm_kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="✅ Отправить")],
            [types.KeyboardButton(text="✏️ Изменить текст")],
            [types.KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True
    )
    await message.answer(preview, reply_markup=confirm_kb, parse_mode="HTML")
    await state.set_state(AdminStates.confirming_broadcast)


@router.message(AdminStates.confirming_broadcast)
async def broadcast_confirm(message: types.Message, state: FSMContext):
    if message.text == "✏️ Изменить текст":
        await message.answer("Введите новый текст:", reply_markup=cancel_kb)
        await state.set_state(AdminStates.waiting_for_broadcast)
        return

    if message.text == "✅ Отправить":
        data = await state.get_data()
        classified = data["classified"]
        original_text = data["original_text"]

        users = await get_all_users()
        success = 0

        for user in users:
            try:
                await message.bot.send_message(user[0], classified["formatted_text"])
                success += 1
            except:
                pass

        await save_announcement(
            original_text=original_text,
            formatted_text=classified["formatted_text"],
            type_=classified["type"],
            event_date=classified.get("event_date"),
            priority=classified["priority"],
            group_name=None
        )

        await message.answer(
            f"✅ Рассылка завершена!\nОтправлено: {success}/{len(users)} студентов",
            reply_markup=admin_kb
        )
        await state.clear()
        return

    await message.answer("Нажмите одну из кнопок выше.")


# ------------------ РАССЫЛКА ПО ГРУППЕ ------------------

@router.message(lambda msg: msg.text == "👥 Рассылка по группе" and msg.from_user.id == ADMIN_ID)
async def group_start(message: types.Message, state: FSMContext):
    await message.answer("Введите название группы:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_group_name)


@router.message(AdminStates.waiting_for_group_name)
async def get_group_name(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    await message.answer("Введите сообщение для группы:")
    await state.set_state(AdminStates.waiting_for_group_message)


@router.message(AdminStates.waiting_for_group_message)
async def group_classify(message: types.Message, state: FSMContext):
    await message.answer("⏳ Анализирую сообщение...")

    classified = await classify_message(message.text)
    data = await state.get_data()

    await state.update_data(
        original_text=message.text,
        classified=classified,
    )

    preview = format_preview(classified)
    preview += f"\n\nГруппа: <b>{data['group']}</b>"

    confirm_kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="✅ Отправить")],
            [types.KeyboardButton(text="✏️ Изменить текст")],
            [types.KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True
    )
    await message.answer(preview, reply_markup=confirm_kb, parse_mode="HTML")
    await state.set_state(AdminStates.confirming_group_broadcast)


@router.message(AdminStates.confirming_group_broadcast)
async def group_confirm(message: types.Message, state: FSMContext):
    if message.text == "✏️ Изменить текст":
        await message.answer("Введите новый текст:", reply_markup=cancel_kb)
        await state.set_state(AdminStates.waiting_for_group_message)
        return

    if message.text == "✅ Отправить":
        data = await state.get_data()
        classified = data["classified"]
        group = data["group"]
        original_text = data["original_text"]

        users = await get_users_by_group(group)
        success = 0

        for user in users:
            try:
                await message.bot.send_message(user[0], classified["formatted_text"])
                success += 1
            except:
                pass

        await save_announcement(
            original_text=original_text,
            formatted_text=classified["formatted_text"],
            type_=classified["type"],
            event_date=classified.get("event_date"),
            priority=classified["priority"],
            group_name=group
        )

        await message.answer(
            f"✅ Отправлено группе {group}!\nДоставлено: {success}/{len(users)} студентов",
            reply_markup=admin_kb
        )
        await state.clear()
        return

    await message.answer("Нажмите одну из кнопок выше.")


# ------------------ ИСТОРИЯ РАССЫЛОК ------------------

@router.message(lambda msg: msg.text == "📜 История рассылок" and msg.from_user.id == ADMIN_ID)
async def show_history(message: types.Message):
    announcements = await get_announcements(limit=10)

    if not announcements:
        await message.answer("История пуста.")
        return

    text = "📜 <b>Последние рассылки:</b>\n\n"
    for ann in announcements:
        type_, date, priority, formatted_text, group, sent_at = ann
        type_icon = TYPE_ICONS.get(type_, "📢")
        priority_icon = PRIORITY_ICONS.get(priority, "🟡")
        group_str = f"Группа: {group}" if group else "Все студенты"

        text += f"{type_icon} {type_.capitalize()} | {priority_icon} {priority.capitalize()}\n"
        if date:
            text += f"📅 {date}\n"
        text += f"👥 {group_str}\n"
        text += f"🕐 {sent_at[:16]}\n"
        text += f"💬 {formatted_text[:80]}{'...' if len(formatted_text) > 80 else ''}\n"
        text += "──────────────────\n"

    await message.answer(text, parse_mode="HTML")


# ------------------ СПИСОК ГРУПП ------------------

@router.message(lambda msg: msg.text == "📋 Список групп" and msg.from_user.id == ADMIN_ID)
async def show_groups(message: types.Message):
    from database import get_all_groups

    groups = await get_all_groups()

    if not groups:
        await message.answer("Групп пока нет.")
        return

    text = "📋 <b>Группы:</b>\n\n"
    for g in groups:
        text += f"• {g[0]}\n"
    text += "\n👉 Напиши: /group ПО-110"

    await message.answer(text, parse_mode="HTML")


@router.message(lambda msg: msg.text and msg.text.startswith("/group") and msg.from_user.id == ADMIN_ID)
async def show_group_users(message: types.Message):
    from database import get_users_in_group

    try:
        _, group_name = message.text.split(maxsplit=1)
    except:
        await message.answer("Формат: /group ПО-110")
        return

    users = await get_users_in_group(group_name)

    if not users:
        await message.answer("В группе никого нет.")
        return

    text = f"👥 <b>Группа {group_name}:</b>\n\n"
    for name, uid in users:
        text += f"• {name} — ID: {uid}\n"

    await message.answer(text, parse_mode="HTML")


# ------------------ ДОБАВИТЬ ПОЛЬЗОВАТЕЛЯ ------------------

from database import add_user

@router.message(lambda msg: msg.text == "➕ Добавить пользователя" and msg.from_user.id == ADMIN_ID)
async def add_user_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите ФИО:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.adding_user_name)


@router.message(AdminStates.adding_user_name)
async def add_user_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите группу:")
    await state.set_state(AdminStates.adding_user_group)


@router.message(AdminStates.adding_user_group)
async def add_user_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    await message.answer("Введите Telegram ID пользователя:")
    await state.set_state(AdminStates.adding_user_id)


@router.message(AdminStates.adding_user_id)
async def add_user_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        await add_user(int(message.text), data["name"], data["group"])
        await message.answer("Пользователь добавлен ✅", reply_markup=admin_kb)
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуйте снова:")
        return
    await state.clear()


# ------------------ УДАЛИТЬ ПОЛЬЗОВАТЕЛЯ ------------------

from database import delete_user

@router.message(lambda msg: msg.text == "❌ Удалить пользователя" and msg.from_user.id == ADMIN_ID)
async def delete_user_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите ID пользователя:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.deleting_user)


@router.message(AdminStates.deleting_user)
async def delete_user_confirm(message: types.Message, state: FSMContext):
    try:
        await delete_user(int(message.text))
        await message.answer("Пользователь удалён ✅", reply_markup=admin_kb)
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуйте снова:")
        return
    await state.clear()


# ------------------ ОТМЕНА ------------------

@router.message(lambda msg: msg.text == "❌ Отмена")
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=admin_kb)


# debug ВСЕГДА ПОСЛЕДНИМ
@router.message()
async def debug(message: types.Message):
    print("TEXT:", message.text)
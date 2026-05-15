from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import (
    get_all_users, get_users_by_group, get_users_by_course,
    save_announcement, get_announcements,
    get_users_in_group, get_users_in_course, get_all_groups
)
from services.ai import classify_message
from keyboards.admin import admin_kb, cancel_kb, course_select_kb, list_type_kb

router = Router()

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

COURSE_MAP = {
    "1 курс": 1, "2 курс": 2, "3 курс": 3, "4 курс": 4
}


class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    confirming_broadcast = State()

    waiting_for_group_name = State()
    waiting_for_group_message = State()
    confirming_group_broadcast = State()

    waiting_for_course = State()
    waiting_for_course_message = State()
    confirming_course_broadcast = State()

    adding_user_name = State()
    adding_user_group = State()
    adding_user_course = State()
    adding_user_id = State()

    deleting_user = State()

    list_choosing_type = State()
    list_choosing_group = State()


def is_admin(msg): return msg.from_user.id in ADMIN_IDS


def format_preview(classified: dict, target: str = "") -> str:
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
    preview += f"{priority_icon} <b>Важность:</b> {priority.capitalize()}\n"
    if target:
        preview += f"👥 <b>Кому:</b> {target}\n"
    preview += f"\n📨 <b>Текст для студентов:</b>\n{text}\n\n"
    preview += "──────────────────\n"
    preview += "Отправить это сообщение?"
    return preview


confirm_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="✅ Отправить")],
        [types.KeyboardButton(text="✏️ Изменить текст")],
        [types.KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True
)


async def _send(bot, user_id: int, text: str) -> bool:
    try:
        await bot.send_message(user_id, text)
        return True
    except:
        return False


# ------------------ АДМИН-ПАНЕЛЬ ------------------

@router.message(lambda msg: is_admin(msg) and msg.text == "/admin")
async def admin_panel(message: types.Message):
    await message.answer("Админ-панель:", reply_markup=admin_kb)


# ------------------ РАССЫЛКА ВСЕМ ------------------

@router.message(lambda msg: is_admin(msg) and msg.text == "📢 Рассылка всем")
async def broadcast_start(message: types.Message, state: FSMContext):
    await message.answer("Введите сообщение для рассылки:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_broadcast)


@router.message(AdminStates.waiting_for_broadcast)
async def broadcast_classify(message: types.Message, state: FSMContext):
    await message.answer("⏳ Анализирую сообщение...")
    classified = await classify_message(message.text)
    await state.update_data(original_text=message.text, classified=classified)
    await message.answer(format_preview(classified, "Все студенты"), reply_markup=confirm_kb, parse_mode="HTML")
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
        users = await get_all_users()
        success = 0
        for user in users:
            if await _send(message.bot, user[0], classified["formatted_text"]):
                success += 1
        await save_announcement(
            original_text=data["original_text"],
            formatted_text=classified["formatted_text"],
            type_=classified["type"],
            event_date=classified.get("event_date"),
            priority=classified["priority"],
        )
        await message.answer(f"✅ Рассылка завершена!\nОтправлено: {success}/{len(users)}", reply_markup=admin_kb)
        await state.clear()
        return
    await message.answer("Нажмите одну из кнопок выше.")


# ------------------ РАССЫЛКА ПО ГРУППЕ ------------------

@router.message(lambda msg: is_admin(msg) and msg.text == "👥 Рассылка по группе")
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
    await state.update_data(original_text=message.text, classified=classified)
    await message.answer(format_preview(classified, f"Группа {data['group']}"), reply_markup=confirm_kb, parse_mode="HTML")
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
        users = await get_users_by_group(group)
        success = 0
        for user in users:
            if await _send(message.bot, user[0], classified["formatted_text"]):
                success += 1
        await save_announcement(
            original_text=data["original_text"],
            formatted_text=classified["formatted_text"],
            type_=classified["type"],
            event_date=classified.get("event_date"),
            priority=classified["priority"],
            group_name=group
        )
        await message.answer(f"✅ Отправлено группе {group}!\nДоставлено: {success}/{len(users)}", reply_markup=admin_kb)
        await state.clear()
        return
    await message.answer("Нажмите одну из кнопок выше.")


# ------------------ РАССЫЛКА ПО КУРСУ ------------------

@router.message(lambda msg: is_admin(msg) and msg.text == "🎓 Рассылка по курсу")
async def course_broadcast_start(message: types.Message, state: FSMContext):
    await message.answer("Выберите курс:", reply_markup=course_select_kb)
    await state.set_state(AdminStates.waiting_for_course)


@router.message(AdminStates.waiting_for_course)
async def get_course_for_broadcast(message: types.Message, state: FSMContext):
    if message.text not in COURSE_MAP:
        await message.answer("Выберите курс из кнопок ниже:", reply_markup=course_select_kb)
        return
    await state.update_data(course=COURSE_MAP[message.text], course_str=message.text)
    await message.answer("Введите сообщение для курса:", reply_markup=cancel_kb)
    await state.set_state(AdminStates.waiting_for_course_message)


@router.message(AdminStates.waiting_for_course_message)
async def course_classify(message: types.Message, state: FSMContext):
    await message.answer("⏳ Анализирую сообщение...")
    classified = await classify_message(message.text)
    data = await state.get_data()
    await state.update_data(original_text=message.text, classified=classified)
    await message.answer(format_preview(classified, data["course_str"]), reply_markup=confirm_kb, parse_mode="HTML")
    await state.set_state(AdminStates.confirming_course_broadcast)


@router.message(AdminStates.confirming_course_broadcast)
async def course_confirm(message: types.Message, state: FSMContext):
    if message.text == "✏️ Изменить текст":
        await message.answer("Введите новый текст:", reply_markup=cancel_kb)
        await state.set_state(AdminStates.waiting_for_course_message)
        return
    if message.text == "✅ Отправить":
        data = await state.get_data()
        classified = data["classified"]
        course = data["course"]
        course_str = data["course_str"]
        users = await get_users_by_course(course)
        success = 0
        for user in users:
            if await _send(message.bot, user[0], classified["formatted_text"]):
                success += 1
        await save_announcement(
            original_text=data["original_text"],
            formatted_text=classified["formatted_text"],
            type_=classified["type"],
            event_date=classified.get("event_date"),
            priority=classified["priority"],
            course=course
        )
        await message.answer(f"✅ Отправлено {course_str}!\nДоставлено: {success}/{len(users)}", reply_markup=admin_kb)
        await state.clear()
        return
    await message.answer("Нажмите одну из кнопок выше.")


# ------------------ /list — СПИСОК СТУДЕНТОВ ------------------

@router.message(lambda msg: is_admin(msg) and (msg.text == "/list" or msg.text == "📋 /list — список студентов"))
async def list_start(message: types.Message, state: FSMContext):
    await message.answer("Показать список по:", reply_markup=list_type_kb)
    await state.set_state(AdminStates.list_choosing_type)


@router.message(AdminStates.list_choosing_type)
async def list_choose_type(message: types.Message, state: FSMContext):
    if message.text == "🎓 По курсу":
        await message.answer("Выберите курс:", reply_markup=course_select_kb)
        await state.update_data(list_type="course")
        await state.set_state(AdminStates.list_choosing_group)
        return

    if message.text == "👥 По группе":
        groups = await get_all_groups()
        if not groups:
            await message.answer("Групп пока нет.", reply_markup=admin_kb)
            await state.clear()
            return

        group_kb = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text=g[0])] for g in groups] + [[types.KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
        await message.answer("Выберите группу:", reply_markup=group_kb)
        await state.update_data(list_type="group")
        await state.set_state(AdminStates.list_choosing_group)
        return

    await message.answer("Выберите из кнопок ниже.", reply_markup=list_type_kb)


@router.message(AdminStates.list_choosing_group)
async def list_show(message: types.Message, state: FSMContext):
    data = await state.get_data()
    list_type = data.get("list_type")

    if list_type == "group":
        users = await get_users_in_group(message.text)
        if not users:
            await message.answer("В этой группе никого нет.", reply_markup=admin_kb)
            await state.clear()
            return
        text = f"👥 <b>Группа {message.text}:</b>\n\n"
        for name, uid, course in users:
            course_str = f" | {course} курс" if course else ""
            text += f"• {name}{course_str}\n  ID: {uid}\n"

    elif list_type == "course":
        if message.text not in COURSE_MAP:
            await message.answer("Выберите курс из кнопок.", reply_markup=course_select_kb)
            return
        course = COURSE_MAP[message.text]
        users = await get_users_in_course(course)
        if not users:
            await message.answer(f"На {message.text} никого нет.", reply_markup=admin_kb)
            await state.clear()
            return
        text = f"🎓 <b>{message.text}:</b>\n\n"
        for name, uid, group in users:
            text += f"• {name} | {group}\n  ID: {uid}\n"
    else:
        await state.clear()
        return

    await message.answer(text, parse_mode="HTML", reply_markup=admin_kb)
    await state.clear()


# ------------------ ИСТОРИЯ РАССЫЛОК ------------------

@router.message(lambda msg: is_admin(msg) and msg.text == "📜 История рассылок")
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


# ------------------ ДОБАВИТЬ ПОЛЬЗОВАТЕЛЯ ------------------

from database import add_user

@router.message(lambda msg: is_admin(msg) and msg.text == "➕ Добавить пользователя")
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
async def add_user_group_handler(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    await message.answer("Введите курс (1/2/3/4):")
    await state.set_state(AdminStates.adding_user_course)


@router.message(AdminStates.adding_user_course)
async def add_user_course_handler(message: types.Message, state: FSMContext):
    try:
        course = int(message.text)
        if course not in [1, 2, 3, 4]:
            raise ValueError
    except ValueError:
        await message.answer("Курс должен быть числом от 1 до 4:")
        return
    await state.update_data(course=course)
    await message.answer("Введите Telegram ID пользователя:")
    await state.set_state(AdminStates.adding_user_id)


@router.message(AdminStates.adding_user_id)
async def add_user_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        await add_user(int(message.text), data["name"], data["group"], data["course"])
        await message.answer("Пользователь добавлен ✅", reply_markup=admin_kb)
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуйте снова:")
        return
    await state.clear()


# ------------------ УДАЛИТЬ ПОЛЬЗОВАТЕЛЯ ------------------

from database import delete_user

@router.message(lambda msg: is_admin(msg) and msg.text == "❌ Удалить пользователя")
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

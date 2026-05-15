from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📢 Рассылка всем")],
        [KeyboardButton(text="👥 Рассылка по группе")],
        [KeyboardButton(text="🎓 Рассылка по курсу")],
        [KeyboardButton(text="📋 /list — список студентов")],
        [KeyboardButton(text="📜 История рассылок")],
        [KeyboardButton(text="➕ Добавить пользователя")],
        [KeyboardButton(text="❌ Удалить пользователя")],
    ],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

course_select_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1 курс"), KeyboardButton(text="2 курс")],
        [KeyboardButton(text="3 курс"), KeyboardButton(text="4 курс")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True
)

list_type_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 По группе"), KeyboardButton(text="🎓 По курсу")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True
)

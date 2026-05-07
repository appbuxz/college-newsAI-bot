from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📢 Рассылка всем")],
        [KeyboardButton(text="👥 Рассылка по группе")],
        [KeyboardButton(text="📋 Список групп")],
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
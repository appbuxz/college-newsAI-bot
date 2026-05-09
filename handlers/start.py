from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from keyboards.reply import main_kb
from database import add_user, get_user_info, get_announcements_for_student
from services.ai import answer_student_question

router = Router()

chat_histories = {}

class Register(StatesGroup):
    name = State()
    group = State()


# ------------------ СТАРТ ------------------

@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()

    # Сбрасываем историю чата при /start
    chat_histories.pop(message.from_user.id, None)

    user = await get_user_info(message.from_user.id)
    if user:
        full_name, group_name = user
        await message.answer(
            f"👋 С возвращением, {full_name}!\n"
            f"Группа: {group_name}\n\n"
            "Задай любой вопрос — я отвечу на основе объявлений твоей группы.",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        await message.answer(
            "Добро пожаловать! Нажмите 'Регистрация' чтобы начать.",
            reply_markup=main_kb
        )


# ------------------ РЕГИСТРАЦИЯ ------------------

@router.message(lambda msg: msg.text == "Регистрация")
async def register(message: types.Message, state: FSMContext):
    await message.answer("Введите ФИО:")
    await state.set_state(Register.name)


@router.message(Register.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите группу:")
    await state.set_state(Register.group)


@router.message(Register.group)
async def get_group(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await add_user(message.from_user.id, data["name"], message.text)

    await message.answer(
        f"✅ Вы зарегистрированы!\n\n"
        f"👤 {data['name']}\n"
        f"📚 Группа: {message.text}\n\n"
        "Теперь задайте любой вопрос — я отвечу на основе объявлений вашей группы.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.clear()


# ------------------ ВОПРОС СТУДЕНТА ------------------

@router.message(lambda msg: msg.from_user.id != ADMIN_ID)
async def student_question(message: types.Message):
    user = await get_user_info(message.from_user.id)

    if not user:
        await message.answer(
            "Вы не зарегистрированы. Нажмите /start чтобы начать.",
            reply_markup=main_kb
        )
        return

    full_name, group_name = user
    user_id = message.from_user.id

    await message.answer("🔍 Ищу информацию...")

    announcements = await get_announcements_for_student(group_name, limit=10)

    if user_id not in chat_histories:
        chat_histories[user_id] = []

    chat_histories[user_id].append({"role": "user", "content": message.text})

    if len(chat_histories[user_id]) > 10:
        chat_histories[user_id] = chat_histories[user_id][-10:]

    answer = await answer_student_question(
        question=message.text,
        student_name=full_name,
        group_name=group_name,
        announcements=announcements,
        history=chat_histories[user_id]
    )
    chat_histories[user_id].append({"role": "assistant", "content": answer})

    await message.answer(answer)
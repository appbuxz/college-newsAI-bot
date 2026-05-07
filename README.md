# 🎓 College Notification Bot

## Russian
Telegram-бот для автоматизации коммуникации между администрацией и студентами учебного заведения. Поддерживает ИИ-классификацию сообщений через OpenRouter и работает без AI-ключа в fallback-режиме.

---

## ✨ Возможности

**Для администратора:**
- 📢 Рассылка сообщений всем студентам
- 👥 Рассылка по конкретной группе
- 🤖 ИИ-классификация сообщений (тип, дата, важность) перед отправкой
- ✅ Подтверждение перед рассылкой с превью
- 📋 Просмотр списка групп и студентов
- 📜 История всех рассылок
- ➕ Добавление и ❌ удаление студентов

**Для студентов:**
- 📝 Регистрация (ФИО + группа)
- 💬 Вопросы на естественном языке — ИИ отвечает на основе объявлений группы
- 📭 Fallback-режим без AI — показывает список последних объявлений

---

## 🗂 Структура проекта

```
├── main.py                  # Точка входа
├── config.py                # Конфигурация и переменные окружения
├── database.py              # Работа с SQLite
├── .env                     # Секретные ключи (не коммитить!)
├── handlers/
│   ├── start.py             # Регистрация и вопросы студентов
│   └── admin.py             # Админ-панель
├── keyboards/
│   ├── reply.py             # Клавиатура для студентов
│   └── admin.py             # Клавиатура для админа
└── services/
    └── ai.py                # Интеграция с OpenRouter
```

---

## ⚙️ Установка

**1. Клонируй репозиторий:**
```bash
git clone https://github.com/username/university-bot.git
cd university-bot
```

**2. Установи зависимости:**
```bash
pip install -r requirements.txt
```

**3. Создай `.env` файл:**
```env
BOT_TOKEN=твой_токен_от_BotFather
ADMIN_ID=твой_telegram_id
OPENROUTER_API_KEY=sk-or-v1-...
```

**4. Запусти бота:**
```bash
python main.py
```

---

## 🔑 Получение ключей

**BOT_TOKEN** — создай бота через [@BotFather](https://t.me/BotFather) в Telegram.

**ADMIN_ID** — твой Telegram ID, узнать можно через [@userinfobot](https://t.me/userinfobot).

**OPENROUTER_API_KEY** — зарегистрируйся на [openrouter.ai](https://openrouter.ai), перейди в API Keys → Create Key. Бесплатно, карта не нужна.

---

## 🤖 Как работает ИИ

Бот использует [OpenRouter](https://openrouter.ai) с моделью `openrouter/free` — она автоматически выбирает доступную бесплатную модель для каждого запроса.

**Классификация сообщений** — при рассылке ИИ анализирует текст и определяет:
| Поле | Варианты |
|------|----------|
| Тип | экзамен / дедлайн / мероприятие / объявление |
| Важность | 🔴 высокая / 🟡 средняя / 🟢 низкая |
| Дата | извлекается автоматически из текста |

**Без AI-ключа** — бот работает в fallback-режиме: сообщения отправляются без изменений, студентам показывается список последних объявлений.

---

## 🗄 База данных

Используется **SQLite** (`students.db`) — не требует отдельного сервера.

**Таблицы:**
- `users` — студенты (user_id, full_name, group_name)
- `announcements` — история рассылок с классификацией

При наличии выделенного сервера легко мигрировать на PostgreSQL — достаточно заменить `aiosqlite` на `asyncpg`.

---

## 📦 Зависимости

```
aiogram==3.18.0
aiosqlite==0.20.0
python-dotenv==1.0.1
openai==1.30.1
httpx==0.27.0
```

---

## 🚀 Команды бота

| Команда | Кто | Описание |
|---------|-----|----------|
| `/start` | Студент | Начало работы / регистрация |
| `/admin` | Админ | Открыть админ-панель |
| `/group ПО-110` | Админ | Показать студентов группы |

---

## 📈 Возможности развития

- [ ] Расписание занятий
- [ ] Статистика рассылок  
- [ ] Docker-контейнер для деплоя
- [ ] Миграция на PostgreSQL для production


## English

A Telegram bot for automating communication between university administration and students. Supports AI-powered message classification via OpenRouter and works without an AI key in fallback mode.

---

## ✨ Features

**For the administrator:**
- 📢 Broadcast messages to all students
- 👥 Send messages to a specific group
- 🤖 AI classification of messages (type, date, priority) before sending
- ✅ Confirmation with preview before broadcasting
- 📋 View list of groups and students
- 📜 Full broadcast history
- ➕ Add and ❌ remove students

**For students:**
- 📝 Registration (full name + group)
- 💬 Ask questions in natural language — AI responds based on group announcements
- 📭 Fallback mode without AI — shows the latest announcements list

---

## 🗂 Project Structure

```
├── main.py                  # Entry point
├── config.py                # Configuration and environment variables
├── database.py              # SQLite database layer
├── .env                     # Secret keys (never commit this!)
├── handlers/
│   ├── start.py             # Student registration and questions
│   └── admin.py             # Admin panel handlers
├── keyboards/
│   ├── reply.py             # Student keyboard
│   └── admin.py             # Admin keyboard
└── services/
    └── ai.py                # OpenRouter AI integration
```

---

## ⚙️ Installation

**1. Clone the repository:**
```bash
git clone https://github.com/username/university-bot.git
cd university-bot
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Create a `.env` file:**
```env
BOT_TOKEN=your_token_from_BotFather
ADMIN_ID=your_telegram_id
OPENROUTER_API_KEY=sk-or-v1-...
```

**4. Run the bot:**
```bash
python main.py
```

---

## 🔑 Getting API Keys

**BOT_TOKEN** — create a bot via [@BotFather](https://t.me/BotFather) on Telegram.

**ADMIN_ID** — your Telegram user ID, find it via [@userinfobot](https://t.me/userinfobot).

**OPENROUTER_API_KEY** — sign up at [openrouter.ai](https://openrouter.ai), go to API Keys → Create Key. Free, no credit card required.

---

## 🤖 How AI Works

The bot uses [OpenRouter](https://openrouter.ai) with the `openrouter/free` router — it automatically selects an available free model for each request.

**Message classification** — when broadcasting, the AI analyzes the text and determines:
| Field | Options |
|-------|---------|
| Type | exam / deadline / event / announcement |
| Priority | 🔴 high / 🟡 medium / 🟢 low |
| Date | automatically extracted from the text |

**Without an AI key** — the bot runs in fallback mode: messages are sent as-is, and students receive a plain list of the latest announcements.

---

## 🗄 Database

Uses **SQLite** (`students.db`) — no separate server required.

**Tables:**
- `users` — students (user_id, full_name, group_name)
- `announcements` — broadcast history with AI classification

Easy to migrate to PostgreSQL when deploying on a server — just replace `aiosqlite` with `asyncpg`.

---

## 📦 Dependencies

```
aiogram==3.18.0
aiosqlite==0.20.0
python-dotenv==1.0.1
openai==1.30.1
httpx==0.27.0
```

---

## 🚀 Bot Commands

| Command | Who | Description |
|---------|-----|-------------|
| `/start` | Student | Start the bot / register |
| `/admin` | Admin | Open the admin panel |
| `/group GR-110` | Admin | Show students in a group |

---

## 📈 Roadmap

- [ ] Class schedule integration
- [ ] Broadcast analytics dashboard
- [ ] Docker container for deployment
- [ ] PostgreSQL migration for production

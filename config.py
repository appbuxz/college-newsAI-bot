import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = set(map(int, os.getenv("ADMIN_IDS", "0").split(",")))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

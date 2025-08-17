from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("LLM_API"))  # Fallback to old name
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Default to cost-effective model

USERNAME = "@mathbot_oleg_bot"
DEFAULT_LANGUAGE = "ru"
SUPPORT_MAIL = "mathbothelp@gmail.com"
SUPPORT_LIMIT_DAY = 5
PASSWORD_LENGTH = 4 

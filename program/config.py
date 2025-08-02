from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
LLM_API_KEY = os.getenv("LLM_API")

USERNAME = "@math_v1bot"
DEFAULT_LANGUAGE = "ru"
SUPPORT_MAIL = "mathbothelp@gmail.com"
SUPPORT_LIMIT_DAY = 5
PASSWORD_LENGTH = 4 

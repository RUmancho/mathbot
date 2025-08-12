from base import User
import telebot
import config
from router import route_message
from core import Process, FileSender

if not config.BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Please set system environment variable BOT_TOKEN.")

bot = telebot.TeleBot(config.BOT_TOKEN)
# Инъекция бота в общие помощники
Process.set_bot(bot)
FileSender.set_bot(bot)

new_user = User("", bot)

@bot.message_handler()
def main(msg):
    route_message(msg, new_user)


if __name__ == "__main__":
    bot.polling(none_stop=True, timeout=60)
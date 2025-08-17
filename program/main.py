import telebot
import config
from core import Process, FileSender
from router import route_message

POLLING_TIMEOUT = 60
POLLING_NONE_STOP = True

bot = telebot.TeleBot(config.BOT_TOKEN)

Process.set_bot(bot)
FileSender.set_bot(bot)

@bot.message_handler()
def main(msg):
    route_message(msg, bot)

if __name__ == "__main__":
    bot.polling(none_stop=POLLING_NONE_STOP, timeout=POLLING_TIMEOUT)
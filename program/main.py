from base import User
import telebot
import config
from router import route_message

bot = telebot.TeleBot(config.BOT_TOKEN)

new_user = User("", bot)

@bot.message_handler()
def main(msg):
    route_message(msg, new_user)


if __name__ == "__main__":
    bot.polling(none_stop=True, timeout=60)
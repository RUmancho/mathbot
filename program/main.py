import user
import telebot
import config
import core
from router import route_message
    
bot = telebot.TeleBot(config.BOT_TOKEN)
core.ButtonCollector.set_bot(bot)

new_user = user.User("", bot)

@bot.message_handler()
def main(msg):
    route_message(msg, new_user)

    
if __name__ == "__main__":
    bot.polling(none_stop=True, timeout = 60)
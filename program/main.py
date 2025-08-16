"""Точка входа бота.

Создаёт экземпляр Telegram-бота, внедряет зависимости в общие утилиты,
и передаёт входящие сообщения в маршрутизатор. Логика работы бота
находится не здесь, а в `router.py` и соответствующих классах ролей.
"""
import telebot
import config
from core import Process, FileSender
from router import route_message, get_or_create_user

# Константы запуска (без «магических» значений в коде)
POLLING_TIMEOUT = 60
POLLING_NONE_STOP = True

if not config.BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Please set system environment variable BOT_TOKEN.")

bot = telebot.TeleBot(config.BOT_TOKEN)

# Инъекция бота в общие помощники (используются многими модулями)
Process.set_bot(bot)
FileSender.set_bot(bot)

@bot.message_handler()
def main(msg):
    try:
        aggregated_user = get_or_create_user(bot, str(msg.chat.id))
        route_message(msg, aggregated_user)
    except Exception as e:
        print(f"Ошибка обработки сообщения: {e}")
        try:
            bot.send_message(msg.chat.id, "Произошла внутренняя ошибка обработки сообщения")
        except Exception as inner_e:
            print(f"Не удалось отправить уведомление об ошибке: {inner_e}")

if __name__ == "__main__":
    bot.polling(none_stop=POLLING_NONE_STOP, timeout=POLLING_TIMEOUT)
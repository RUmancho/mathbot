import core
import keyboards
from theory import handler as theory

START_COMMANDS = [
    "/start", "/главная", "/меню", "/menu", "/main", "/home", "старт", "главная"
]
HELP_COMMANDS = ["помощь", "help", "/help"]

UNKNOWN_REPLY = "Неизвестная команда"
WELCOME_TEXT = "главная"
HELP_TEXT = (
    "Доступные команды:\n"
    "- /главная — открыть главное меню\n"
    "- помощь — показать эту подсказку\n"
)


def _main_keyboard():
    try:
        return keyboards.create_keyboard(["/главная"], ["Помощь"], ["Алгебра", "Графики"], ["Формулы сокращенного умножения"], ["Уравнения", "Неравенства"], ["Тригонометрия"])
    except Exception as e:
        print(f"Не удалось создать клавиатуру: {e}")
        return None


def _try_theory(request: str, bot, chat_id: str) -> bool:
    try:
        def text_out(text: str, kb=None):
            try:
                bot.send_message(chat_id, text, reply_markup=kb)
            except Exception as e:
                print(f"Не удалось отправить сообщение из theory: {e}")
        return bool(theory(request, text_out, chat_id))
    except Exception as e:
        print(f"Ошибка обработки теории: {e}")
        return False


def _get_response(request: str):
    try:
        if request in START_COMMANDS:
            return WELCOME_TEXT, _main_keyboard()
        if request in HELP_COMMANDS or request == "помощь":
            return HELP_TEXT, _main_keyboard()
        return UNKNOWN_REPLY, _main_keyboard()
    except Exception as e:
        print(f"Ошибка в _get_response: {e}")
        return UNKNOWN_REPLY, _main_keyboard()


def route_message(msg, bot) -> None:
    """Сообщение -> ответ."""
    try:
        request = core.transform_request(msg.text)
        chat_id = msg.chat.id

        # Попытка обработать запрос как теорию
        if _try_theory(request, bot, chat_id):
            return

        # Простые команды
        text, keyboard = _get_response(request)
        bot.send_message(chat_id, text, reply_markup=keyboard)
    except Exception as e:
        print(f"Ошибка обработки сообщения: {e}")
        try:
            bot.send_message(msg.chat.id, "Произошла внутренняя ошибка обработки сообщения")
        except Exception as inner_e:
            print(f"Не удалось отправить уведомление об ошибке: {inner_e}")

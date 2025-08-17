import telebot
import config
import core
from core import Process, FileSender
import keyboards
import database
from theory import handler as theory
from sqlalchemy import and_ as SQL_AND

POLLING_TIMEOUT = 60
POLLING_NONE_STOP = True

bot = telebot.TeleBot(config.BOT_TOKEN)

Process.set_bot(bot)
FileSender.set_bot(bot)

START_COMMANDS = ["/start", "/главная", "/меню", "/menu", "/main", "/home", "старт", "главная"]
HELP_COMMANDS = ["помощь", "help", "/help"]

# Простые константы для сценариев (flow)
FLOW_CANCEL = "отмена"
FLOW_DELETE = "delete_profile"
FLOW_SEARCH = "search_student"

# Память активных сценариев в рантайме: chat_id -> {"type": str, "step": str, "data": dict}
ACTIVE_FLOWS: dict[str, dict] = {}


def _out(bot_instance, chat_id: str, text: str, kb=None):
    try:
        bot_instance.send_message(chat_id, text, reply_markup=kb)
    except Exception as e:
        print(f"Не удалось отправить сообщение: {e}")


def _handle_theory(request: str, bot_instance, chat_id: str) -> bool:
    try:
        def text_out(text: str, kb=None):
            _out(bot_instance, chat_id, text, kb)
        return bool(theory(request, text_out, chat_id))
    except Exception as e:
        print(f"Ошибка в обработчике теории: {e}")
        return False


def _show_teacher_students(bot_instance, chat_id: str):
    try:
        me = database.Client(chat_id)
        attached = getattr(me, "my_students", None)
        if not attached:
            _out(bot_instance, chat_id, "У вас пока нет прикрепленных учеников", keyboards.Teacher.main)
            return
        ids = attached.split(";")[:-1]
        if not ids:
            _out(bot_instance, chat_id, "У вас пока нет прикрепленных учеников", keyboards.Teacher.main)
            return
        lines = ["Ваши ученики:", ""]
        for sid in ids:
            st = database.Client(sid)
            school = f"школа №{st.school}" if getattr(st, "school", None) else "школа не указана"
            grade = f"{st.grade} класс" if getattr(st, "grade", None) else "класс не указан"
            lines.append(f"• {st.name} {st.surname} ({school}, {grade})")
        _out(bot_instance, chat_id, "\n".join(lines), keyboards.Teacher.main)
    except Exception as e:
        print(f"Ошибка показа учеников: {e}")
        _out(bot_instance, chat_id, "Не удалось показать список учеников", keyboards.Teacher.main)


def _start_delete_flow(chat_id: str) -> None:
    try:
        ACTIVE_FLOWS[chat_id] = {"type": FLOW_DELETE, "step": "ask_password", "data": {}}
    except Exception as e:
        print(f"Не удалось запустить сценарий удаления профиля: {e}")


def _handle_delete_flow(request: str, chat_id: str) -> bool:
    try:
        flow = ACTIVE_FLOWS.get(chat_id)
        if not flow or flow.get("type") != FLOW_DELETE:
            return False
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _out(bot, chat_id, "Действие отменено")
            return True

        step = flow.get("step")
        if step == "ask_password":
            _out(bot, chat_id, "Введите ваш пароль для удаления профиля")
            flow["step"] = "verify_password"
            return True
        if step == "verify_password":
            # Сверяем пароль
            me = database.Client(chat_id)
            if request == (me.password or ""):
                deleted = database.Manager.delete_record(database.Tables.Users, "telegram_id", chat_id)
                if deleted:
                    _out(bot, chat_id, "Профиль удалён")
                else:
                    _out(bot, chat_id, "Не удалось удалить профиль. Попробуйте позже")
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
            else:
                _out(bot, chat_id, "Неверный пароль, повторите попытку или введите 'отмена'")
                return True
        return False
    except Exception as e:
        print(f"Ошибка сценария удаления профиля: {e}")
        ACTIVE_FLOWS.pop(chat_id, None)
        _out(bot, chat_id, "Не удалось выполнить удаление профиля")
        return True


def _start_search_flow(chat_id: str) -> None:
    try:
        ACTIVE_FLOWS[chat_id] = {"type": FLOW_SEARCH, "step": "ask_city", "data": {}}
    except Exception as e:
        print(f"Не удалось запустить сценарий поиска: {e}")


def _handle_search_flow(request: str, chat_id: str) -> bool:
    try:
        flow = ACTIVE_FLOWS.get(chat_id)
        if not flow or flow.get("type") != FLOW_SEARCH:
            return False
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _out(bot, chat_id, "Действие отменено")
            return True

        step = flow.get("step")
        data = flow.get("data")

        if step == "ask_city":
            _out(bot, chat_id, "В каком городе учатся учащиеся? (название города)")
            flow["step"] = "verify_city"
            return True
        if step == "verify_city":
            if core.Validator.city(request):
                data["city"] = request
                flow["step"] = "ask_school"
            else:
                _out(bot, chat_id, "Некорректный город. Попробуйте снова или введите 'отмена'")
                return True
        if step == "ask_school":
            _out(bot, chat_id, "В какой школе?")
            flow["step"] = "verify_school"
            return True
        if step == "verify_school":
            if core.Validator.school(request):
                try:
                    value = int(request.split(" ")[-1])
                except Exception:
                    value = request
                data["school"] = value
                flow["step"] = "ask_class"
            else:
                _out(bot, chat_id, "Некорректный номер школы. Попробуйте снова или введите 'отмена'")
                return True
        if step == "ask_class":
            _out(bot, chat_id, "В каком классе? (номер класса и буква, например 7А)")
            flow["step"] = "verify_class"
            return True
        if step == "verify_class":
            if core.Validator.class_number(request):
                data["class_number"] = request
                # Выполнить поиск
                condition = SQL_AND(
                    database.Tables.Users.city == data.get("city"),
                    database.Tables.Users.school == data.get("school"),
                    database.Tables.Users.grade == data.get("class_number"),
                )
                results = database.Manager.search_records(database.Tables.Users, condition)
                if results:
                    lines = []
                    for row in results:
                        try:
                            st = database.Client(row["telegram_id"])
                            lines.append(f"{st.name} {st.surname}")
                        except Exception:
                            continue
                    text = "\n".join(lines) if lines else "ничего не найдено"
                    _out(bot, chat_id, text, keyboards.Teacher.attached)
                else:
                    _out(bot, chat_id, "ничего не найдено")
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
            else:
                _out(bot, chat_id, "Некорректный класс. Попробуйте снова или введите 'отмена'")
                return True
        return False
    except Exception as e:
        print(f"Ошибка сценария поиска: {e}")
        ACTIVE_FLOWS.pop(chat_id, None)
        _out(bot, chat_id, "Не удалось выполнить поиск учеников")
        return True


@bot.message_handler()
def main(msg):
    try:
        chat_id = str(msg.chat.id)
        request = core.transform_request(msg.text)

        # 1) Теоретические материалы (единые для всех)
        if _handle_theory(request, bot, chat_id):
            return

        # 2) Активные сценарии (удаление профиля / поиск учеников)
        # Если сценарий активен — продолжаем его и выходим
        if _handle_delete_flow(request, chat_id):
            return
        if _handle_search_flow(request, chat_id):
            return

        # 3) Универсальные команды (единые для всех)
        if request in START_COMMANDS:
            _out(bot, chat_id, "главная", keyboards.create_keyboard(["/главная"], ["Помощь"]))
            return
        if request in HELP_COMMANDS or request == "помощь":
            _out(bot, chat_id, "Доступные команды: /главная, помощь", keyboards.create_keyboard(["/главная"]))
            return

        # 4) Ветвление по роли пользователя
        role = database.find_my_role(chat_id)

        if role == "учитель":
            # Простая, плоская логика для учителя
            if request == "профиль":
                _out(bot, chat_id, "Выберите действие", keyboards.Teacher.profile)
            elif request == "ваши учащиеся":
                _show_teacher_students(bot, chat_id)
            elif request == "прикрепить класс":
                _start_search_flow(chat_id)
                # Немедленно показать первый шаг
                _handle_search_flow("", chat_id)
            elif request == "отправить задание":
                # Запрет если нет учеников
                client = database.Client(chat_id)
                if not getattr(client, "my_students", None):
                    _out(bot, chat_id, "У вас пока нет прикрепленных учеников", keyboards.Teacher.main)
                else:
                    _out(bot, chat_id, "Выберите тип задания", keyboards.Teacher.homework)
            elif request == "отправить индивидуальное задание":
                client = database.Client(chat_id)
                if not getattr(client, "my_students", None):
                    _out(bot, chat_id, "У вас пока нет прикрепленных учеников", keyboards.Teacher.main)
                else:
                    _out(bot, chat_id, "Функция отправки индивидуального задания в упрощенной версии пока недоступна", keyboards.Teacher.main)
            elif request == "отправить задание классу":
                client = database.Client(chat_id)
                if not getattr(client, "my_students", None):
                    _out(bot, chat_id, "У вас пока нет прикрепленных учеников", keyboards.Teacher.main)
                else:
                    _out(bot, chat_id, "Функция отправки задания классу в упрощенной версии пока недоступна", keyboards.Teacher.main)
            elif request == "проверить задания" or request == "проверить индивидуальные задания" or request == "задания для класса":
                _out(bot, chat_id, "Функция проверки заданий в упрощенной версии пока недоступна", keyboards.Teacher.main)
            elif request == "ai помощник":
                _out(bot, chat_id, "Раздел AI Помощник", keyboards.Teacher.ai_helper)
            elif request == "удалить профиль":
                _start_delete_flow(chat_id)
                _handle_delete_flow("", chat_id)
            else:
                _out(bot, chat_id, "Неизвестная команда")
            return

        if role == "ученик":
            # Простая, плоская логика для ученика
            if request == "профиль":
                _out(bot, chat_id, "Выберите действие", keyboards.Student.profile)
            elif request == "заявки":
                _out(bot, chat_id, "Функция заявок в упрощенной версии пока недоступна", keyboards.Student.main)
            elif request == "мои учителя":
                _out(bot, chat_id, "Функция просмотра учителей в упрощенной версии пока недоступна", keyboards.Student.main)
            elif request == "задания":
                _out(bot, chat_id, "Выберите действие с заданиями", keyboards.Student.task)
            elif request in ("получить задания", "отправить решение"):
                _out(bot, chat_id, "Функция работы с заданиями в упрощенной версии пока недоступна", keyboards.Student.main)
            elif request == "сгенерировать задание":
                _out(bot, chat_id, "Укажите тему, по которой сгенерировать одно задание (без решения)")
            elif request == "ai помощник":
                _out(bot, chat_id, "Раздел AI Помощник", keyboards.Student.ai_helper)
            elif request in ("практика", "проверить решение"):
                _out(bot, chat_id, "Функция AI помощника в упрощенной версии пока недоступна", keyboards.Student.ai_helper)
            elif request == "удалить профиль":
                _start_delete_flow(chat_id)
                _handle_delete_flow("", chat_id)
            else:
                _out(bot, chat_id, "Неизвестная команда")
            return

        # Гость / неизвестная роль
        if request == "зарегестрироваться как учитель" or request == "зарегестрироваться как ученик":
            _out(bot, chat_id, "Регистрация в упрощенной версии пока недоступна")
        else:
            _out(bot, chat_id, "Неизвестная команда")
    except Exception as e:
        print(f"Ошибка обработки сообщения: {e}")
        try:
            bot.send_message(msg.chat.id, "Произошла внутренняя ошибка обработки сообщения")
        except Exception as inner_e:
            print(f"Не удалось отправить уведомление об ошибке: {inner_e}")

if __name__ == "__main__":
    bot.polling(none_stop=POLLING_NONE_STOP, timeout=POLLING_TIMEOUT)
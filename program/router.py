"""Маршрутизация входящих сообщений бота.

Содержит обработчики команд для ролей «Ученик», «Учитель», «Гость», а также
главную функцию `route_message`, которая:
- нормализует входящее сообщение,
- определяет роль пользователя,
- делегирует обработку соответствующему обработчику,
- корректно управляет многошаговыми процессами.
Также содержит небольшой кэш агрегированных пользователей по chat_id.
"""
import core
import keyboards
from theory import handler as theory
from base import User as AggregatedUser, find_my_role
from student import Student
from teacher import Teacher
from unregistered import Unregistered

# Простой реестр агрегированных пользователей по chat_id
_AGGREGATED_USERS: dict[str, AggregatedUser] = {}

def get_or_create_user(bot, chat_id: str) -> AggregatedUser:
    """Возвращает агрегированный объект пользователя для chat_id.

    Если в кэше нет объекта — создаёт и сохраняет. Гарантирует актуальный bot.
    """
    try:
        user = _AGGREGATED_USERS.get(chat_id)
        if user is None:
            user = AggregatedUser(chat_id, bot)
            _AGGREGATED_USERS[chat_id] = user
        else:
            try:
                user._telegramBot = bot
            except Exception:
                pass
        return user
    except Exception:
        # На крайний случай создаём новый инстанс
        try:
            return AggregatedUser(chat_id, bot)
        except Exception:
            return None


def handle_student_commands(request: str, user: Student):
    """Обрабатывает команды роли «Ученик».

    Сначала проверяет запрос на соответствие теории и отдаёт материалы, иначе
    роутит по действиям меню ученика.
    """
    is_response = theory(request, user.text_out, user.get_ID())
    if is_response:
        return

    if request in user.SHOW_MAIN_MENU:
        user.show_main_menu()
    elif request == "профиль":
        user.show_profile_actions()
    elif request == "заявки":
        user.show_applications()
    elif request == "мои учителя":
        user.show_my_teachers()
    elif request == "задания":
        user.show_tasks()
    elif request == "получить задания":
        user.get_tasks()
    elif request == "отправить решение":
        user.submit_solution()
    elif request == "сгенерировать задание":
        user.ai_generate_task()
    elif request == "ai помощник":
        user.show_ai_helper_menu()
    elif request == "проверить решение":
        user.ai_check_solution()
    elif request == "сгенерировать задание":
        user.ai_generate_task()
    elif request == "удалить профиль":
        user.delete_account()
    else:
        # Если идет многошаговый процесс (регистрация/удаление/поиск и т.д.), не показываем предупреждение
        if getattr(user, "_current_command", None):
            return
        if hasattr(user, "delete_profile_process") and getattr(user.delete_profile_process, "_is_active", False):
            return
        user.unsupported_command_warning()


def handle_teacher_commands(request: str, user: Teacher):
    """Обрабатывает команды роли «Учитель» (включая AI‑помощник).

    Порядок: теория → меню учителя → AI‑режимы/проверки/назначение заданий.
    """
    is_response = theory(request, user.text_out, user.get_ID())
    if is_response:
        return

    if request in user.SHOW_MAIN_MENU:
        user.show_main_menu()
    elif request == "профиль":
        user.show_profile_actions()
    elif request == "прикрепить класс":
        user.search_class()
    elif request == "ваши учащиеся":
        user.show_my_students()
    elif request == "отправить задание":
        user.assign_homework()
    elif request == "проверить задания":
        user.check_tasks()
    elif request == "отправить индивидуальное задание":
        user.assign_individual_task()
    elif request == "отправить задание классу":
        user.assign_class_task()
    elif request == "проверить индивидуальные задания":
        user.check_individual_tasks()
    elif request == "задания для класса":
        user.check_class_tasks()
    elif request == "ai помощник":
        try:
            user._telegramBot.send_message(user.get_ID(), "Раздел AI Помощник", reply_markup=keyboards.Teacher.ai_helper)
        except Exception:
            pass
    elif request == "сгенерировать задание":
        user.ai_generate_task()
    elif request == "сгенерировать для класса":
        user.assign_class_task()
    elif request == "ai проверка":
        user.check_individual_tasks()
    elif request == "анализ прогресса":
        user.check_class_tasks()
    elif request == "прикрепить всех":
        user.send_application()
    elif request == "удалить профиль":
        user.delete_account()
    else:
        if getattr(user, "_current_command", None):
            return
        if hasattr(user, "delete_profile_process") and getattr(user.delete_profile_process, "_is_active", False):
            return
        user.unsupported_command_warning()


def handle_unregistered_commands(request: str, user: Unregistered):
    """Обрабатывает команды гостя (незарегистрированного пользователя)."""
    is_response = theory(request, user.text_out, user.get_ID())
    if is_response:
        return

    if request in user.RUN_BOT_COMMADS:
        user.current_command = user.getting_started
    elif request in user.SHOW_MAIN_MENU:
        user.current_command = user.show_main_menu
    elif request == "зарегестрироваться как учитель":
        user.current_command = user.teacher_registration
    elif request == "зарегестрироваться как ученик":
        user.current_command = user.student_registration
    elif user.current_registration and not user.current_registration.registration_finished:
        # В процессе регистрации ввод обрабатывается в command_executor
        return
    else:
        if getattr(user, "_current_command", None):
            return
        if hasattr(user, "delete_profile_process") and getattr(user.delete_profile_process, "_is_active", False):
            return
        user.unsupported_command_warning()


def route_message(msg, aggregated_user: AggregatedUser) -> None:
    """Главная точка входа обработки сообщения.

    1) Нормализует текст; 2) Определяет роль; 3) Делегирует обработчику;
    4) Обновляет ввод и выполняет отложенную команду, если есть.
    """
    request = core.transform_request(msg.text)
    ID = str(msg.chat.id)

    aggregated_user.reset_role_change_flag()

    # Определяем роль и активный объект пользователя
    role = find_my_role(ID)
    if role == "ученик":
        active = aggregated_user.set_role(Student, ID)
    elif role == "учитель":
        active = aggregated_user.set_role(Teacher, ID)
    else:
        active = aggregated_user.set_role(Unregistered, ID)

    # Маршрутизация команд согласно роли
    if isinstance(active, Student):
        handle_student_commands(request, active)
    elif isinstance(active, Teacher):
        handle_teacher_commands(request, active)
    else:
        handle_unregistered_commands(request, active)

    # Сначала обновляем ввод, затем выполняем команду — это важно для процессов, ожидающих ввод
    aggregated_user.update_last_request(request)
    aggregated_user.command_executor()


"""Маршрутизация входящих сообщений бота.

Содержит функции-обработчики команд для разных ролей (ученик, учитель,
гость), а также главную функцию `route_message`, которая:
- нормализует входящее сообщение,
- определяет роль пользователя,
- делегирует обработку соответствующему обработчику,
- корректно управляет многошаговыми процессами (регистрация, поиск класса).
"""
import core
from features import theory
from users import User as AggregatedUser
from users import Student, Teacher, Unregistered, find_my_role


def handle_student_commands(request: str, user: Student):
    """Обработка команд, характерных для роли «Ученик»."""
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
    else:
        # Если идет многошаговый процесс, не показываем предупреждение
        if getattr(user, "_current_command", None):
            return
        user.unsupported_command_warning()


def handle_teacher_commands(request: str, user: Teacher):
    """Обработка команд, характерных для роли «Учитель»."""
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
    elif request == "удалить профиль":
        user.delete_account()
    else:
        if getattr(user, "_current_command", None):
            return
        user.unsupported_command_warning()


def handle_unregistered_commands(request: str, user: Unregistered):
    """Обработка команд для незарегистрированного пользователя (гостя)."""
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
        user.unsupported_command_warning()


def _has_pending_command(active_user) -> bool:
    """Есть ли у пользователя отложенная команда (многошаговый процесс)."""
    return bool(getattr(active_user, "_current_command", None))


def route_message(msg, aggregated_user: AggregatedUser) -> None:
    """Главная точка входа для обработки сообщения.

    Параметры:
    - msg: объект сообщения телеграма
    - aggregated_user: агрегирующий объект пользователя, обеспечивающий доступ
      к активной реализации роли и выполнению команд.
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


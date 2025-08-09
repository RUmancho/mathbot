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


def handle_student_commands(request: str, u: Student):
    """Обработка команд, характерных для роли «Ученик»."""
    is_response = theory.handler(request, u.text_out, u.get_ID())
    if is_response:
        return

    if request in u.SHOW_MAIN_MENU:
        u.show_main_menu()
    elif request == "профиль":
        u.show_profile_actions()
    elif request == "заявки":
        u.show_applications()
    elif request == "мои учителя":
        u.show_my_teachers()
    elif request == "задания":
        u.show_tasks()
    elif request == "получить задания":
        u.get_tasks()
    elif request == "отправить решение":
        u.submit_solution()
    else:
        u.unsupported_command_warning()


def handle_teacher_commands(request: str, u: Teacher):
    """Обработка команд, характерных для роли «Учитель»."""
    is_response = theory.handler(request, u.text_out, u.get_ID())
    if is_response:
        return

    if request in u.SHOW_MAIN_MENU:
        u.show_main_menu()
    elif request == "профиль":
        u.show_profile_actions()
    elif request == "прикрепить класс":
        u.search_class()
    elif request == "ваши учащиеся":
        u.show_my_students()
    elif request == "отправить задание":
        u.assign_homework()
    elif request == "проверить задания":
        u.check_tasks()
    elif request == "отправить индивидуальное задание":
        u.assign_individual_task()
    elif request == "отправить задание классу":
        u.assign_class_task()
    elif request == "проверить индивидуальные задания":
        u.check_individual_tasks()
    elif request == "задания для класса":
        u.check_class_tasks()
    elif request == "удалить профиль":
        u.delete_account()
    else:
        u.unsupported_command_warning()


def handle_unregistered_commands(request: str, u: Unregistered):
    """Обработка команд для незарегистрированного пользователя (гостя)."""
    is_response = theory.handler(request, u.text_out, u.get_ID())
    if is_response:
        return

    if request in u.RUN_BOT_COMMADS:
        u.current_command = u.getting_started
    elif request in u.SHOW_MAIN_MENU:
        u.current_command = u.show_main_menu
    elif request == "зарегестрироваться как учитель":
        u.current_command = u.teacher_registration
    elif request == "зарегестрироваться как ученик":
        u.current_command = u.student_registration
    elif u.current_registration and not u.current_registration.registration_finished:
        # В процессе регистрации ввод обрабатывается в command_executor
        pass
    else:
        u.unsupported_command_warning()


def _is_process_active(active_user) -> bool:
    """Проверяет, активен ли у пользователя многошаговый процесс."""
    if isinstance(active_user, Unregistered):
        reg = getattr(active_user, "current_registration", None)
        return bool(reg and not reg.registration_finished)
    if isinstance(active_user, Teacher):
        sc = getattr(active_user, "searchClass", None)
        finished = getattr(sc, "registration_finished", True) if sc else True
        return bool(sc and not finished)
    return False


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

    # Был ли активен пошаговый процесс до маршрутизации
    active_before = aggregated_user.get_user()
    was_in_process = _is_process_active(active_before) if active_before else False

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

    # Выполнение отложенных команд/процессов с корректным порядком обновления ввода
    if was_in_process:
        aggregated_user.update_last_request(request)
        aggregated_user.command_executor()
    else:
        aggregated_user.command_executor()
        aggregated_user.update_last_request(request)


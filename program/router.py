import core
import keyboards
from theory import handler as theory
from base import User as AggregatedUser
from student import Student
from teacher import Teacher
from unregistered import Guest
import database

AGGREGATED_USERS: dict[str, AggregatedUser] = {}

def get_or_create_user(bot, chat_id: str) -> AggregatedUser:
    try:
        user = AGGREGATED_USERS.get(chat_id)
        if user is None:
            user = AggregatedUser(chat_id, bot)
            AGGREGATED_USERS[chat_id] = user
        else:
            user._telegramBot = bot
        return user
    except Exception as e:
        print(f"Не удалось получить/создать агрегированного пользователя: {e}")
        return AggregatedUser(chat_id, bot)


def handle_student_commands(request: str, user: Student):
    is_response = theory(request, user.out, user.get_ID())
    if is_response:
        return

    if request in user.RUN_BOT_COMMADS or request in user.SHOW_MAIN_MENU:
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
        user.unsupported_command_warning()


def handle_teacher_commands(request: str, user: Teacher):
    is_response = theory(request, user.out, user.get_ID())
    if is_response:
        return

    if request in user.RUN_BOT_COMMADS or request in user.SHOW_MAIN_MENU:
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
        user.out("Раздел AI Помощник", keyboards.Teacher.ai_helper)
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
        user.unsupported_command_warning()


def handle_unregistered_commands(request: str, user: Guest):
    is_response = theory(request, user.out, user.get_ID())
    if is_response:
        return

    if request in user.RUN_BOT_COMMADS:
        user.getting_started()
    elif request in user.SHOW_MAIN_MENU:
        user.show_main_menu()
    elif request == "зарегестрироваться как учитель":
        user.teacher_registration()
    elif request == "зарегестрироваться как ученик":
        user.student_registration()
    else:
        user.unsupported_command_warning()


def route_message(msg, aggregated_user: AggregatedUser) -> None:
    request = core.transform_request(msg.text)
    ID = str(msg.chat.id)

    aggregated_user.reset_role_change_flag()

    role = database.find_my_role(ID)
    if role == "ученик":
        active = aggregated_user.set_role(Student, ID)
        handler = handle_student_commands
    elif role == "учитель":
        active = aggregated_user.set_role(Teacher, ID)
        handler = handle_teacher_commands
    else:
        active = aggregated_user.set_role(Guest, ID)
        handler = handle_unregistered_commands

    aggregated_user.update_last_request(request)

    if active.has_active_process() and active.handle_active_process():
        return

    handler(request, active)

    # Выполнить отложенную команду роли (если она была установлена внутри обработчика)
    try:
        aggregated_user.command_executor()
    except Exception as e:
        print(f"Ошибка выполнения отложенной команды: {e}")


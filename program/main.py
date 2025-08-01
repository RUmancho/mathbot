import functional
import telebot
import config
import theory
import core
    
bot = telebot.TeleBot(config.BOT_TOKEN)
core.ButtonCollector.set_bot(bot)

teacher = functional.Teacher(telegramBot=bot)
student = functional.Student(telegramBot=bot)
unregistered = functional.Unregistered(telegramBot=bot)

def transform_request(request: str):
    request = request.lower().strip()
    if "ё" in request:
        request = request.replace("ё", "е")
    return request

@bot.message_handler()
def main(msg):
    global teacher, student, unregistered
    request = transform_request(msg.text)
    ID = str(msg.chat.id)
    
    if ID in functional.User.registered_users_IDS():
        role = functional.User.find_my_role(ID)
        print(f"Пользователь зарегистрирован, роль: {role}")

        if role == "ученик":
            student.ID = ID
            student.update_last_request(request)
            student.load_user()
            handle_student_commands(request)

        elif role == "учитель":
            teacher.ID = ID
            teacher.update_last_request(request)
            teacher.load_user()
            handle_teacher_commands(request)
    else:
        print(f"Пользователь НЕ зарегистрирован, обрабатываем как незарегистрированный")
        unregistered.ID = ID
        unregistered.update_last_request(request)
        handle_unregistered_commands(request)

def handle_student_commands(request: str):
    is_response = theory.handler(request, student.text_out, student.ID)
    
    if is_response: ...

    elif request in student.SHOW_MAIN_MENU:
        student.show_main_menu()
    elif request == "профиль":
        student.show_profile_actions()
    elif request == "заявки":
        student.show_applications()
    elif request == "мои учителя":
        student.show_my_teachers()
    elif request == "задания":
        student.show_tasks()
    elif request == "получить задания":
        student.get_tasks()
    elif request == "отправить решение":
        student.submit_solution()
    else:
        student.unsupported_command_warning()

def handle_teacher_commands(request: str):
    print(f"Обработка команды учителя: '{request}'")
    is_response = theory.handler(request, teacher.text_out, teacher.ID)
    
    if is_response: ...

    elif request in teacher.SHOW_MAIN_MENU:
        teacher.show_main_menu()
    elif request == "профиль":
        teacher.show_profile_actions()
    elif request == "прикрепить класс":
        teacher.search_class()
    elif request == "ваши учащиеся":
        teacher.show_my_students()
    elif request == "отправить задание":
        teacher.assign_homework()
    elif request == "проверить задания":
        teacher.check_tasks()
    elif request == "отправить индивидуальное задание":
        teacher.assign_individual_task()
    elif request == "отправить задание классу":
        teacher.assign_class_task()
    elif request == "проверить индивидуальные задания":
        teacher.check_individual_tasks()
    elif request == "задания для класса":
        teacher.check_class_tasks()
    else:
        teacher.unsupported_command_warning()

def handle_unregistered_commands(request: str):
    is_response = theory.handler(request, unregistered.text_out, unregistered.ID)
    
    if is_response: ...

    elif request in unregistered.RUN_BOT_COMMADS:
        unregistered.current_command = unregistered.getting_started
        unregistered.execute()

    elif request in unregistered.SHOW_MAIN_MENU:
        unregistered.current_command = unregistered.show_main_menu
        unregistered.execute()

    elif request == "зарегестрироваться как учитель":
        unregistered.current_command = unregistered.teacher_registration
        unregistered.execute()

    elif request == "зарегестрироваться как ученик":
        unregistered.current_command = unregistered.student_registration
        unregistered.execute()
    
    elif unregistered.current_registration and not unregistered.current_registration.registration_finished:
        unregistered.handle_registration_input()
    else:
        unregistered.unsupported_command_warning()

if __name__ == "__main__":
    bot.polling(none_stop=True, timeout = 60)
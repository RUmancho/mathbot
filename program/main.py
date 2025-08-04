import user
import telebot
import config
import theory
import core
    
bot = telebot.TeleBot(config.BOT_TOKEN)
core.ButtonCollector.set_bot(bot)

new_user = None

is_set = False
def set_role(user_type, ID):
    global new_user, is_set
    if not is_set:
        new_user = user_type(ID, bot)
        is_set = True

@bot.message_handler()
def main(msg):
    request = core.transform_request(msg.text)
    ID = str(msg.chat.id)

    role = user.find_my_role(ID)
    if role:
        print(f"Пользователь зарегистрирован, роль: {role}")

        if role == "ученик":
            set_role(user.Student, ID)
            handle_student_commands(request, new_user)

        elif role == "учитель":
            set_role(user.Teacher, ID)
            handle_teacher_commands(request, new_user)
    else:
        set_role(user.Unregistered, ID)
        print(f"Пользователь НЕ зарегистрирован, обрабатываем как незарегистрированный")
        handle_unregistered_commands(request, new_user)

    new_user.update_last_request(request)
    new_user.command_executor()

    
def handle_student_commands(request: str, user: user.Student):
    is_response = theory.handler(request, user.text_out, user.get_ID())
    
    if is_response: ...

    elif request in user.SHOW_MAIN_MENU:
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
        user.unsupported_command_warning()
    

def handle_teacher_commands(request: str, user: user.Teacher):
    print(f"Обработка команды учителя: '{request}'")
    is_response = theory.handler(request, user.text_out, user.get_ID())
    
    if is_response: ...
    elif request in user.SHOW_MAIN_MENU:
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
        user.unsupported_command_warning()
    

def handle_unregistered_commands(request: str, user: user.Unregistered):
    is_response = theory.handler(request, user.text_out, user.get_ID())
    
    if is_response: ...

    elif request in user.RUN_BOT_COMMADS:
        user.current_command = user.getting_started

    elif request in user.SHOW_MAIN_MENU:
        user.current_command = user.show_main_menu

    elif request == "зарегестрироваться как учитель":
        user.current_command = user.teacher_registration

    elif request == "зарегестрироваться как ученик":
        user.current_command = user.student_registration
    
    elif user.current_registration and not user.current_registration.registration_finished:
        user.handle_registration_input()
    else:
        user.unsupported_command_warning()

if __name__ == "__main__":
    bot.polling(none_stop=True, timeout = 60)
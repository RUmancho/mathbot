import functional
import telebot
import config
import theory
import core
    
bot = telebot.TeleBot(config.BOT_TOKEN)
core.ButtonCollector.set_bot(bot)

me = functional.NewUser(bot)

def transform_request(request: str):
    request = request.lower().strip()
    if "ё" in request:
        request = request.replace("ё", "е")
    return request

@bot.message_handler()
def main(msg):
    global me
    request = transform_request(msg.text)
    ID = str(msg.chat.id)
    me.set_ID(ID)
    me.update_last_request(request)
    
    if ID in functional.User.registered_users_IDS():
        role = functional.User.find_my_role(ID)
        print(f"Пользователь зарегистрирован, роль: {role}")

        if role == "ученик":
            me.set_user_type(functional.Student)
            handle_student_commands(request)

        elif role == "учитель":
            me.set_user_type(functional.Teacher)
            handle_teacher_commands(request)
    else:
        me.set_user_type(functional.Unregistered)
        print(f"Пользователь НЕ зарегистрирован, обрабатываем как незарегистрированный")
        handle_unregistered_commands(request)

def handle_student_commands(request: str):
    is_response = theory.handler(request, me.text_out, me.get_ID())
    
    if is_response: ...

    elif request in me.SHOW_MAIN_MENU:
        me.show_main_menu()
    elif request == "профиль":
        me.show_profile_actions()
    elif request == "заявки":
        me.show_applications()
    elif request == "мои учителя":
        me.show_my_teachers()
    elif request == "задания":
        me.show_tasks()
    elif request == "получить задания":
        me.get_tasks()
    elif request == "отправить решение":
        me.submit_solution()
    else:
        me.unsupported_command_warning()

def handle_teacher_commands(request: str):
    print(f"Обработка команды учителя: '{request}'")
    is_response = theory.handler(request, me.text_out, me.get_ID())
    
    if is_response: ...
    elif request in me.SHOW_MAIN_MENU:
        me.show_main_menu()
    elif request == "профиль":
        me.show_profile_actions()
    elif request == "прикрепить класс":
        me.search_class()
    elif request == "ваши учащиеся":
        me.show_my_students()
    elif request == "отправить задание":
        me.assign_homework()
    elif request == "проверить задания":
        me.check_tasks()
    elif request == "отправить индивидуальное задание":
        me.assign_individual_task()
    elif request == "отправить задание классу":
        me.assign_class_task()
    elif request == "проверить индивидуальные задания":
        me.check_individual_tasks()
    elif request == "задания для класса":
        me.check_class_tasks()
    elif request == "удалить профиль":
        me.delete_account()
    else:
        me.unsupported_command_warning()
    
    me.command_executor()

def handle_unregistered_commands(request: str):
    is_response = theory.handler(request, me.text_out, me.get_ID())
    
    if is_response: ...

    elif request in me.RUN_BOT_COMMADS:
        me.current_command = me.getting_started
        me.command_executor()

    elif request in me.SHOW_MAIN_MENU:
        me.current_command = me.show_main_menu
        me.command_executor()

    elif request == "зарегестрироваться как учитель":
        me.current_command = me.teacher_registration
        me.command_executor()

    elif request == "зарегестрироваться как ученик":
        me.current_command = me.student_registration
        me.command_executor()
    
    elif me.current_registration and not me.current_registration.registration_finished:
        me.handle_registration_input()
    else:
        me.unsupported_command_warning()

if __name__ == "__main__":
    bot.polling(none_stop=True, timeout = 60)
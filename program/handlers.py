import keyboards


def handle_student(request: str, ctx) -> None:
    """Команды для ученика (функциональный стиль)."""
    try:
        is_response = False
        try:
            from theory import handler as theory
            is_response = theory(request, ctx.out, ctx.get_ID())
        except Exception as e:
            print(f"Ошибка вызова theory для ученика: {e}")

        if is_response:
            return

        if request in ctx.RUN_BOT_COMMADS or request in ctx.SHOW_MAIN_MENU:
            ctx.show_main_menu()
        elif request == "профиль":
            ctx.show_profile_actions()
        elif request == "заявки":
            ctx.show_applications()
        elif request == "мои учителя":
            ctx.show_my_teachers()
        elif request == "задания":
            ctx.show_tasks()
        elif request == "получить задания":
            ctx.get_tasks()
        elif request == "отправить решение":
            ctx.submit_solution()
        elif request == "сгенерировать задание":
            ctx.ai_generate_task()
        elif request == "ai помощник":
            ctx.show_ai_helper_menu()
        elif request == "практика":
            ctx.ai_practice()
        elif request == "проверить решение":
            ctx.ai_check_solution()
        elif request == "удалить профиль":
            ctx.delete_account()
        else:
            ctx.unsupported_command_warning()
    except Exception as e:
        print(f"Ошибка обработки команды ученика: {e}")


def handle_teacher(request: str, ctx) -> None:
    """Команды для учителя (функциональный стиль)."""
    try:
        is_response = False
        try:
            from theory import handler as theory
            is_response = theory(request, ctx.out, ctx.get_ID())
        except Exception as e:
            print(f"Ошибка вызова theory для учителя: {e}")

        if is_response:
            return

        if request in ctx.RUN_BOT_COMMADS or request in ctx.SHOW_MAIN_MENU:
            ctx.show_main_menu()
        elif request == "профиль":
            ctx.show_profile_actions()
        elif request == "прикрепить класс":
            ctx.search_class()
        elif request == "ваши учащиеся":
            ctx.show_my_students()
        elif request == "отправить задание":
            ctx.assign_homework()
        elif request == "проверить задания":
            ctx.check_tasks()
        elif request == "отправить индивидуальное задание":
            ctx.assign_individual_task()
        elif request == "отправить задание классу":
            ctx.assign_class_task()
        elif request == "проверить индивидуальные задания":
            ctx.check_individual_tasks()
        elif request == "задания для класса":
            ctx.check_class_tasks()
        elif request == "ai помощник":
            ctx.out("Раздел AI Помощник", keyboards.Teacher.ai_helper)
        elif request == "сгенерировать задание":
            ctx.ai_generate_task()
        elif request == "сгенерировать для класса":
            ctx.assign_class_task()
        elif request == "ai проверка":
            ctx.check_individual_tasks()
        elif request == "анализ прогресса":
            ctx.check_class_tasks()
        elif request == "прикрепить всех":
            ctx.send_application()
        elif request == "удалить профиль":
            ctx.delete_account()
        else:
            ctx.unsupported_command_warning()
    except Exception as e:
        print(f"Ошибка обработки команды учителя: {e}")


def handle_guest(request: str, ctx) -> None:
    """Команды для незарегистрированного (функциональный стиль)."""
    try:
        is_response = False
        try:
            from theory import handler as theory
            is_response = theory(request, ctx.out, ctx.get_ID())
        except Exception as e:
            print(f"Ошибка вызова theory для гостя: {e}")

        if is_response:
            return

        try:
            if getattr(ctx, "in_registration", False):
                return
        except Exception:
            pass

        if request in ctx.RUN_BOT_COMMADS:
            ctx.getting_started()
        elif request in ctx.SHOW_MAIN_MENU:
            ctx.show_main_menu()
        elif request == "зарегестрироваться как учитель":
            ctx.teacher_registration()
        elif request == "зарегестрироваться как ученик":
            ctx.student_registration()
        else:
            ctx.unsupported_command_warning()
    except Exception as e:
        print(f"Ошибка обработки команды гостя: {e}")



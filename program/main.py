import telebot
import config
import core
from core import Process, FileSender
import keyboards
import database
from theory import handler as theory
from sqlalchemy import and_ as SQL_AND
import datetime
from colorama import Fore, Back, Style, init

# Инициализируем colorama
init(autoreset=True)

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
FLOW_REGISTER_STUDENT = "register_student"
FLOW_REGISTER_TEACHER = "register_teacher"
FLOW_SEND_APPLICATION = "send_application"
FLOW_MANAGE_APPLICATIONS = "manage_applications"
FLOW_EDIT_PROFILE = "edit_profile"
FLOW_RESET_PASSWORD = "reset_password"
FLOW_INDIVIDUAL_ASSIGNMENT = "individual_assignment"
FLOW_SUBMIT_ANSWER = "submit_answer"
FLOW_REVIEW_ASSIGNMENT = "review_assignment"
FLOW_QUIZ = "quiz"

# Память активных сценариев в рантайме: chat_id -> {"type": str, "step": str, "data": dict}
ACTIVE_FLOWS: dict[str, dict] = {}


def _log(message: str, chat_id: str = None, level: str = "INFO"):
    """Логирование событий бота с временной меткой, цветами и эмодзи."""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chat_info = f" [Chat: {chat_id}]" if chat_id else ""
        
        # Определяем цвет и эмодзи для уровня логирования
        if level == "INFO":
            color = Fore.CYAN
            emoji = "ℹ️"
        elif level == "WARNING":
            color = Fore.YELLOW
            emoji = "⚠️"
        elif level == "ERROR":
            color = Fore.RED
            emoji = "❌"
        elif level == "SUCCESS":
            color = Fore.GREEN
            emoji = "✅"
        elif level == "DEBUG":
            color = Fore.MAGENTA
            emoji = "🔍"
        else:
            color = Fore.WHITE
            emoji = "📝"
        
        # Форматируем и выводим сообщение
        timestamp_colored = f"{Fore.BLUE}[{timestamp}]"
        level_colored = f"{color}[{emoji} {level}]"
        chat_colored = f"{Fore.GREEN}{chat_info}" if chat_id else ""
        message_colored = f"{Style.BRIGHT}{message}{Style.RESET_ALL}"
        
        print(f"{timestamp_colored} {level_colored}{chat_colored} {message_colored}")
    except Exception as e:
        print(f"{Fore.RED}❌ Ошибка логирования: {e}{Style.RESET_ALL}")


def _out(bot_instance, chat_id: str, text: str, kb=None):
    try:
        bot_instance.send_message(chat_id, text, reply_markup=kb)
    except Exception as e:
        print(f"Не удалось отправить сообщение: {e}")

def _verify_password(entered_password: str, stored_password_hash: str) -> bool:
    """Проверяет соответствие введенного пароля с хешированным паролем из БД"""
    try:
        import hashlib
        entered_password_hash = hashlib.sha256(entered_password.encode()).hexdigest()
        return entered_password_hash == stored_password_hash
    except Exception:
        return False


def _handle_theory(request: str, bot_instance, chat_id: str) -> bool:
    try:
        def text_out(text: str, kb=None):
            _out(bot_instance, chat_id, text, kb)
        return bool(theory(request, text_out, chat_id, bot_instance))
    except Exception as e:
        print(f"Ошибка в обработчике теории: {e}")
        return False


def _show_student_assignments(bot_instance, chat_id: str) -> None:
    """Показывает все задания ученика"""
    try:
        assignments = database.Manager.get_student_assignments(chat_id)
        
        if not assignments:
            _out(bot_instance, chat_id, "У вас пока нет заданий от учителей", keyboards.Student.main)
            return
        
        lines = ["📚 Ваши задания:", ""]
        for assignment in assignments:
            # Получаем имя учителя
            try:
                teacher = database.Client(assignment['sender_id'])
                teacher_name = f"{teacher.name} {teacher.surname}"
            except:
                teacher_name = "Неизвестный учитель"
            
            # Форматируем дату
            created_date = assignment['created_at'][:10] if assignment['created_at'] else "Дата неизвестна"
            
            # Определяем статус
            status_emoji = {
                "sent": "📤",
                "completed": "✅", 
                "overdue": "⏰",
                "graded": "🎯"
            }.get(assignment['status'], "❓")
            
            lines.append(f"{status_emoji} **{assignment['topic']}** ({assignment['difficulty']})")
            lines.append(f"👨‍🏫 От: {teacher_name}")
            lines.append(f"📅 Создано: {created_date}")
            lines.append(f"⏰ Срок: {assignment['deadline'][:10] if assignment['deadline'] else 'Не указан'}")
            lines.append(f"📝 {assignment['task_text']}")
            
            # Показываем статус и действия
            if assignment['status'] == "sent":
                lines.append("📝 Нажмите '✍️ ответить #ID' чтобы выполнить задание")
            elif assignment['status'] == "completed":
                lines.append("✅ Ответ отправлен, ожидайте проверки")
            elif assignment['status'] == "graded":
                lines.append("🎯 Задание проверено учителем")
            elif assignment['status'] == "overdue":
                lines.append("⏰ Срок выполнения истек")
            
            lines.append("")
        
        result_text = "\n".join(lines)
        
        # Создаем клавиатуру с кнопками для каждого задания
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        
        # Добавляем кнопки для каждого задания
        for assignment in assignments:
            if assignment['status'] == "sent":
                button_text = f"✍️ Ответить #{assignment['id']}"
                keyboard.add(button_text)
                _log(f"🔍 Добавлена кнопка: '{button_text}' для задания #{assignment['id']}", chat_id, "DEBUG")
            elif assignment['status'] == "graded":
                button_text = f"🎯 Оценка #{assignment['id']}"
                keyboard.add(button_text)
                _log(f"🔍 Добавлена кнопка: '{button_text}' для задания #{assignment['id']}", chat_id, "DEBUG")
        
        keyboard.add("Назад")
        
        _log(f"🔍 Клавиатура создана с {len(assignments)} кнопками заданий", chat_id, "DEBUG")
        _out(bot_instance, chat_id, result_text, keyboard)
        
    except Exception as e:
        print(f"Ошибка показа заданий: {e}")
        _out(bot_instance, chat_id, "Произошла ошибка при загрузке заданий", keyboards.Student.main)


def _show_teacher_assignments(bot_instance, chat_id: str) -> None:
    """Показывает все задания, отправленные учителем"""
    try:
        assignments = database.Manager.get_teacher_assignments(chat_id)
        
        if not assignments:
            _out(bot_instance, chat_id, "Вы пока не отправляли заданий", keyboards.Teacher.main)
            return
        
        lines = ["📚 Отправленные задания:", ""]
        for assignment in assignments:
            # Получаем имя ученика
            try:
                student = database.Client(assignment['recipient_id'])
                student_name = f"{student.name} {student.surname}"
            except:
                student_name = "Неизвестный ученик"
            
            # Форматируем дату
            created_date = assignment['created_at'][:10] if assignment['created_at'] else "Дата неизвестна"
            
            # Определяем статус
            status_emoji = {
                "sent": "📤",
                "completed": "✅", 
                "overdue": "⏰",
                "graded": "🎯"
            }.get(assignment['status'], "❓")
            
            lines.append(f"{status_emoji} **{assignment['topic']}** ({assignment['difficulty']})")
            lines.append(f"👨‍🎓 Ученик: {student_name}")
            lines.append(f"📅 Создано: {created_date}")
            lines.append(f"⏰ Срок: {assignment['deadline'][:10] if assignment['deadline'] else 'Не указан'}")
            lines.append(f"📝 {assignment['task_text']}")
            
            # Показываем статус и действия
            if assignment['status'] == "sent":
                lines.append("📤 Ожидает выполнения учеником")
            elif assignment['status'] == "completed":
                lines.append("✅ Ответ получен, ожидает проверки")
                lines.append("📝 Нажмите '✍️ проверить #ID' для оценки")
            elif assignment['status'] == "graded":
                lines.append("🎯 Задание проверено и оценено")
            elif assignment['status'] == "overdue":
                lines.append("⏰ Срок выполнения истек")
            
            lines.append("")
        
        result_text = "\n".join(lines)
        
        # Создаем клавиатуру с кнопками для каждого задания
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        
        # Добавляем кнопки для каждого задания
        for assignment in assignments:
            if assignment['status'] == "completed":
                keyboard.add(f"✍️ Проверить #{assignment['id']}")
        
        keyboard.add("Назад")
        
        _out(bot_instance, chat_id, result_text, keyboard)
        
    except Exception as e:
        print(f"Ошибка показа заданий учителя: {e}")
        _out(bot_instance, chat_id, "Произошла ошибка при загрузке заданий", keyboards.Teacher.main)



def _show_teacher_students(bot_instance, chat_id: str):
    try:
        me = database.Client(chat_id)
        attached = getattr(me, "my_students", None)
        print(f"DEBUG: _show_teacher_students - teacher_id: {chat_id}, my_students: '{attached}'")
        
        if not attached:
            print(f"DEBUG: No my_students found")
            _out(bot_instance, chat_id, "У вас пока нет прикрепленных учеников", keyboards.Teacher.main)
            return
        
        # Use comma as separator (not semicolon)
        ids = attached.split(",") if attached else []
        print(f"DEBUG: Parsed student IDs: {ids}")
        
        if not ids:
            print(f"DEBUG: No student IDs after parsing")
            _out(bot_instance, chat_id, "У вас пока нет прикрепленных учеников", keyboards.Teacher.main)
            return
        
        lines = ["Ваши ученики:", ""]
        for sid in ids:
            try:
                st = database.Client(sid)
                school = f"школа №{st.school}" if getattr(st, "school", None) else "школа не указана"
                grade = f"{st.grade} класс" if getattr(st, "grade", None) else "класс не указан"
                lines.append(f"• {st.name} {st.surname} ({school}, {grade})")
                print(f"DEBUG: Added student: {st.name} {st.surname}")
            except Exception as e:
                print(f"DEBUG: Error processing student {sid}: {e}")
                continue
        
        result_text = "\n".join(lines)
        print(f"DEBUG: Final result text: {result_text}")
        _out(bot_instance, chat_id, result_text, keyboards.Teacher.main)
        
    except Exception as e:
        print(f"Ошибка показа учеников: {e}")
        _out(bot_instance, chat_id, "Не удалось показать список учеников", keyboards.Teacher.main)


def _start_submit_answer_flow(chat_id: str, assignment_id: str) -> None:
    """Запускает процесс отправки ответа на задание"""
    try:
        _log(f"🔍 Запуск submit answer flow для задания #{assignment_id}", chat_id, "DEBUG")
        ACTIVE_FLOWS[chat_id] = {"type": FLOW_SUBMIT_ANSWER, "step": "ask_answer", "data": {"assignment_id": assignment_id}}
        _log("🚀 Запущен процесс отправки ответа", chat_id, "SUCCESS")
        _log(f"🔍 ACTIVE_FLOWS после запуска: {ACTIVE_FLOWS}", chat_id, "DEBUG")
    except Exception as e:
        _log(f"❌ Не удалось запустить отправку ответа: {e}", chat_id, "ERROR")
        print(f"Не удалось запустить сценарий отправки ответа: {e}")


def _handle_submit_answer_flow(request: str, chat_id: str) -> bool:
    """Обрабатывает процесс отправки ответа на задание"""
    try:
        _log(f"🔍 _handle_submit_answer_flow вызван с request: '{request}'", chat_id, "DEBUG")
        flow = ACTIVE_FLOWS.get(chat_id)
        _log(f"🔍 Текущий flow: {flow}", chat_id, "DEBUG")
        if not flow or flow.get("type") != FLOW_SUBMIT_ANSWER:
            _log(f"🔍 Flow не найден или неверный тип: {flow}", chat_id, "DEBUG")
            return False
        
        # Отмена отправки ответа
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("❌ Отправка ответа отменена пользователем", chat_id, "WARNING")
            _out(bot, chat_id, "Отправка ответа отменена", keyboards.Student.main)
            return True

        step = flow.get("step")
        data = flow.get("data", {})
        assignment_id = data.get("assignment_id")
        
        _log(f"📝 Шаг отправки ответа: {step}", chat_id, "DEBUG")

        # Шаг 1: Запрос ответа
        if step == "ask_answer":
            # Показываем задание и запрашиваем ответ
            try:
                assignment = database.Manager.get_student_assignments(chat_id)
                assignment = next((a for a in assignment if str(a['id']) == assignment_id), None)
                
                if not assignment:
                    _out(bot, chat_id, "Задание не найдено", keyboards.Student.main)
                    ACTIVE_FLOWS.pop(chat_id, None)
                    return True
                
                # Показываем задание
                lines = [
                    "📝 **Задание для выполнения:**",
                    f"**Тема:** {assignment['topic']}",
                    f"**Сложность:** {assignment['difficulty']}",
                    f"**Текст задания:**",
                    assignment['task_text'],
                    "",
                    "✍️ **Напишите ваш ответ ниже:**",
                    "",
                    "💡 **Подсказка:** Просто напишите ваш ответ текстом, не используйте кнопки."
                ]
                
                result_text = "\n".join(lines)
                
                _out(bot, chat_id, result_text)
                
                # Переходим к следующему шагу
                flow["step"] = "receive_answer"
                return True
                
            except Exception as e:
                print(f"Error showing assignment: {e}")
                _out(bot, chat_id, "Ошибка при загрузке задания", keyboards.Student.main)
                ACTIVE_FLOWS.pop(chat_id, None)
                return True

        # Шаг 2: Получение ответа
        elif step == "receive_answer":
            if not request or request == "Отмена":
                ACTIVE_FLOWS.pop(chat_id, None)
                _out(bot, chat_id, "Отправка ответа отменена", keyboards.Student.main)
                return True
            
            # Сохраняем ответ в базе данных
            try:
                success = database.Manager.submit_student_answer(int(assignment_id), request)
                
                if success:
                    _out(bot, chat_id, "✅ Ваш ответ успешно отправлен! Учитель проверит его и поставит оценку.", keyboards.Student.main)
                    _log("✅ Ответ студента отправлен", chat_id, "SUCCESS")
                else:
                    _out(bot, chat_id, "❌ Не удалось отправить ответ. Попробуйте еще раз.", keyboards.Student.main)
                    _log("❌ Ошибка отправки ответа", chat_id, "ERROR")
                
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
                
            except Exception as e:
                print(f"Error submitting answer: {e}")
                _out(bot, chat_id, "Произошла ошибка при отправке ответа", keyboards.Student.main)
                ACTIVE_FLOWS.pop(chat_id, None)
                return True

        return False
        
    except Exception as e:
        _log(f"💥 Ошибка в процессе отправки ответа: {e}", chat_id, "ERROR")
        print(f"Ошибка в процессе отправки ответа: {e}")
        ACTIVE_FLOWS.pop(chat_id, None)
        return True


def _start_review_assignment_flow(chat_id: str, assignment_id: str) -> None:
    """Запускает процесс проверки ответа на задание"""
    try:
        ACTIVE_FLOWS[chat_id] = {"type": FLOW_REVIEW_ASSIGNMENT, "step": "show_answer", "data": {"assignment_id": assignment_id}}
        _log("🚀 Запущен процесс проверки ответа", chat_id, "SUCCESS")
    except Exception as e:
        _log(f"❌ Не удалось запустить проверку ответа: {e}", chat_id, "ERROR")
        print(f"Не удалось запустить сценарий проверки ответа: {e}")


def _handle_review_assignment_flow(request: str, chat_id: str) -> bool:
    """Обрабатывает процесс проверки ответа на задание"""
    try:
        flow = ACTIVE_FLOWS.get(chat_id)
        if not flow or flow.get("type") != FLOW_REVIEW_ASSIGNMENT:
            return False
        
        # Отмена проверки
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("❌ Проверка ответа отменена пользователем", chat_id, "WARNING")
            _out(bot, chat_id, "Проверка ответа отменена", keyboards.Teacher.main)
            return True

        step = flow.get("step")
        data = flow.get("data", {})
        assignment_id = data.get("assignment_id")
        
        _log(f"📝 Шаг проверки ответа: {step}", chat_id, "DEBUG")

        # Шаг 1: Показ ответа студента
        if step == "show_answer":
            try:
                # Получаем задание с ответом студента
                assignments = database.Manager.get_completed_assignments_for_teacher(chat_id)
                assignment = next((a for a in assignments if str(a['id']) == assignment_id), None)
                
                if not assignment:
                    _out(bot, chat_id, "Ответ студента не найден", keyboards.Teacher.main)
                    ACTIVE_FLOWS.pop(chat_id, None)
                    return True
                
                # Получаем имя студента
                try:
                    student = database.Client(assignment['recipient_id'])
                    student_name = f"{student.name} {student.surname}"
                except:
                    student_name = "Неизвестный ученик"
                
                # Показываем задание и ответ
                lines = [
                    "📝 **Ответ студента для проверки:**",
                    f"**Ученик:** {student_name}",
                    f"**Тема:** {assignment['topic']}",
                    f"**Сложность:** {assignment['difficulty']}",
                    f"**Задание:**",
                    assignment['task_text'],
                    "",
                    "✍️ **Ответ студента:**",
                    assignment['student_answer'],
                    "",
                    "📅 **Отправлен:** " + (assignment['answer_submitted_at'][:10] if assignment['answer_submitted_at'] else "Дата неизвестна"),
                    "",
                    "🎯 **Поставьте оценку и напишите отзыв:**"
                ]
                
                result_text = "\n".join(lines)
                
                # Создаем клавиатуру с оценками
                keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.add("5 (Отлично)", "4 (Хорошо)", "3 (Удовлетворительно)", "2 (Неудовлетворительно)")
                
                _out(bot, chat_id, result_text, keyboard)
                
                # Переходим к следующему шагу
                flow["step"] = "receive_grade"
                return True
                
            except Exception as e:
                print(f"Error showing student answer: {e}")
                _out(bot, chat_id, "Ошибка в процессе проверки ответа: {e}", keyboards.Teacher.main)
                ACTIVE_FLOWS.pop(chat_id, None)
                return True

        # Шаг 2: Получение оценки
        elif step == "receive_grade":
            if not request or request == "Отмена":
                ACTIVE_FLOWS.pop(chat_id, None)
                _out(bot, chat_id, "Проверка ответа отменена", keyboards.Teacher.main)
                return True
            
            # Сохраняем оценку
            data["grade"] = request
            flow["step"] = "receive_feedback"
            
            _out(bot, chat_id, "✍️ **Теперь напишите отзыв к работе студента:**")
            return True

        # Шаг 3: Получение отзыва
        elif step == "receive_feedback":
            if not request or request == "Отмена":
                ACTIVE_FLOWS.pop(chat_id, None)
                _out(bot, chat_id, "Проверка ответа отменена", keyboards.Teacher.main)
                return True
            
            # Сохраняем оценку и отзыв в базе данных
            try:
                grade = data.get("grade", "Без оценки")
                success = database.Manager.grade_assignment(int(assignment_id), grade, request)
                
                if success:
                    _out(bot, chat_id, "✅ Ответ студента успешно проверен и оценен!", keyboards.Teacher.main)
                    _log("✅ Ответ студента проверен", chat_id, "SUCCESS")
                else:
                    _out(bot, chat_id, "❌ Не удалось сохранить оценку. Попробуйте еще раз.", keyboards.Teacher.main)
                    _log("❌ Ошибка сохранения оценки", chat_id, "ERROR")
                
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
                
            except Exception as e:
                print(f"Error grading assignment: {e}")
                _out(bot, chat_id, "Произошла ошибка при сохранении оценки", keyboards.Student.main)
                ACTIVE_FLOWS.pop(chat_id, None)
                return True

        return False
        
    except Exception as e:
        _log(f"💥 Ошибка в процессе проверки ответа: {e}", chat_id, "ERROR")
        print(f"Ошибка в процессе проверки ответа: {e}")
        ACTIVE_FLOWS.pop(chat_id, None)
        return True


def _show_assignment_grade(bot_instance, chat_id: str, assignment_id: str) -> None:
    """Показывает оценку и отзыв учителя по заданию"""
    try:
        # Получаем оцененные задания студента
        assignments = database.Manager.get_graded_assignments_for_student(chat_id)
        assignment = next((a for a in assignments if str(a['id']) == assignment_id), None)
        
        if not assignment:
            _out(bot_instance, chat_id, "Оценка по данному заданию не найдена", keyboards.Student.main)
            return
        
        # Получаем имя учителя
        try:
            teacher = database.Client(assignment.get('sender_id', ''))
            teacher_name = f"{teacher.name} {teacher.surname}"
            lines.append(f"**Учитель:** {teacher_name}")
        except:
            pass
        
        # Показываем оценку и отзыв
        lines = [
            "🎯 **Оценка по заданию:**",
            f"**Тема:** {assignment['topic']}",
            f"**Сложность:** {assignment['difficulty']}",
            f"**Ваш ответ:**",
            assignment['student_answer'],
            "",
            f"**Оценка:** {assignment['grade']}",
            f"**Отзыв учителя:**",
            assignment['teacher_feedback'],
            "",
            f"**Дата проверки:** {assignment['graded_at'][:10] if assignment['graded_at'] else 'Дата неизвестна'}"
        ]
        
        result_text = "\n".join(lines)
        _out(bot_instance, chat_id, result_text, keyboards.Student.main)
        
    except Exception as e:
        print(f"Ошибка показа оценки: {e}")
        _out(bot_instance, chat_id, "Произошла ошибка при загрузке оценки", keyboards.Student.main)


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
            # Сверяем пароль с использованием функции проверки
            me = database.Client(chat_id)
            
            if _verify_password(request, me.password or ""):
                deleted = database.Manager.delete_record(database.Tables.Users, "telegram_id", chat_id)
                if deleted:
                    _out(bot, chat_id, "✅ Профиль успешно удален")
                    _log(f"🗑️ Профиль пользователя {chat_id} удален", chat_id, "SUCCESS")
                else:
                    _out(bot, chat_id, "❌ Не удалось удалить профиль. Попробуйте позже")
                    _log("❌ Ошибка удаления профиля из БД", chat_id, "ERROR")
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
            else:
                _out(bot, chat_id, "❌ Неверный пароль, повторите попытку или введите 'отмена'")
                _log("❌ Неверный пароль при удалении профиля", chat_id, "WARNING")
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

def _start_registration_flow(chat_id: str, role: str) -> None:
    """Запускает процесс регистрации для ученика или учителя"""
    try:
        flow_type = FLOW_REGISTER_STUDENT if role == "ученик" else FLOW_REGISTER_TEACHER
        ACTIVE_FLOWS[chat_id] = {
            "type": flow_type, 
            "step": "ask_name", 
            "data": {"role": role}
        }
        _log(f"🚀 Запущен процесс регистрации: {role}", chat_id, "SUCCESS")
    except Exception as e:
        _log(f"❌ Не удалось запустить регистрацию: {e}", chat_id, "ERROR")
        print(f"Не удалось запустить сценарий регистрации: {e}")


def _handle_search_flow(request: str, chat_id: str) -> bool:
    """Handle search flow step by step"""
    flow = ACTIVE_FLOWS.get(chat_id)
    if not flow or flow["type"] != FLOW_SEARCH:
        return False
    
    step = flow["step"]
    data = flow["data"]
    
    print(f"DEBUG: _handle_search_flow - step: {step}, request: '{request}', data: {data}")
    
    if step == "ask_city":
        print(f"DEBUG: Sending city question")
        _out(bot, chat_id, "В каком городе?", keyboards.Teacher.attached)
        flow["step"] = "verify_city"
        print(f"DEBUG: Changed step to verify_city")
        return True
    
    elif step == "verify_city":
        print(f"DEBUG: Verifying city: '{request}'")
        if core.Validator.city(request):
            print(f"DEBUG: City validation passed")
            data["city"] = request
            flow["step"] = "verify_school"
            print(f"DEBUG: Changed step to verify_school, asking school question")
            _out(bot, chat_id, "В какой школе?", keyboards.Teacher.attached)
            return True
        else:
            print(f"DEBUG: City validation failed")
            _out(bot, chat_id, "Пожалуйста, введите корректное название города", keyboards.Teacher.attached)
            return True
    
    elif step == "verify_school":
        print(f"DEBUG: Verifying school: '{request}'")
        if core.Validator.school(request):
            print(f"DEBUG: School validation passed")
            data["school"] = request
            flow["step"] = "verify_class"
            print(f"DEBUG: Changed step to verify_class, asking class question")
            _out(bot, chat_id, "В каком классе?", keyboards.Teacher.attached)
            return True
        else:
            print(f"DEBUG: School validation failed")
            _out(bot, chat_id, "Пожалуйста, введите корректное название школы", keyboards.Teacher.attached)
            return True
    
    elif step == "verify_class":
        print(f"DEBUG: Verifying class: '{request}'")
        if core.Validator.class_number(request):
            print(f"DEBUG: Class validation passed")
            data["class_number"] = request
            print(f"DEBUG: All data collected: {data}")
            
            # Search for students using the existing database search
            filter_dict = {
                "city": data.get("city"),
                "school": data.get("school"),
                "grade": data.get("class_number"),
                "role": "ученик"  # Looking for students
            }
            print(f"DEBUG: Searching with filter: {filter_dict}")
            
            try:
                results = database.Manager.search_records_unicode_insensitive(database.Tables.Users, filter_dict)
                print(f"DEBUG: Search results: {results}")
                
                if results:
                    lines = []
                    for row in results:
                        try:
                            st = database.Client(row["telegram_id"])
                            lines.append(f"{st.name} {st.surname}")
                        except Exception as e:
                            print(f"DEBUG: Error processing student record: {e}")
                            continue
                    
                    if lines:
                        text = "\n".join(lines)
                        print(f"DEBUG: Sending student list: {text}")
                        _out(bot, chat_id, f"Найдены ученики:\n{text}", keyboards.Teacher.attached)
                        # Store search results and wait for user action
                        flow["step"] = "wait_for_action"
                        flow["data"]["search_results"] = results
                        print(f"DEBUG: Changed step to wait_for_action, waiting for user choice")
                    else:
                        print(f"DEBUG: No valid student records found")
                        _out(bot, chat_id, "ничего не найдено", keyboards.Teacher.main)
                        # Clear the flow if no results
                        del ACTIVE_FLOWS[chat_id]
                        print(f"DEBUG: Cleared flow for chat_id: {chat_id}")
                else:
                    print(f"DEBUG: No search results")
                    _out(bot, chat_id, "ничего не найдено", keyboards.Teacher.main)
                    # Clear the flow if no results
                    del ACTIVE_FLOWS[chat_id]
                    print(f"DEBUG: Cleared flow for chat_id: {chat_id}")
                
            except Exception as e:
                print(f"DEBUG: Error during database search: {e}")
                _out(bot, chat_id, "Произошла ошибка при поиске в базе данных", keyboards.Teacher.main)
                # Clear the flow on error
                del ACTIVE_FLOWS[chat_id]
                print(f"DEBUG: Cleared flow for chat_id: {chat_id}")
            
            return True
        else:
            print(f"DEBUG: Class validation failed")
            _out(bot, chat_id, "Пожалуйста, введите корректный номер класса", keyboards.Teacher.attached)
            return True
    
    elif step == "wait_for_action":
        print(f"DEBUG: Waiting for user action: '{request}'")
        if request.lower() == "прикрепить всех":
            print(f"DEBUG: User chose to attach all students")
            search_results = data.get("search_results", [])
            if search_results:
                # Process attaching all students
                attached_count = 0
                teacher_id = chat_id
                
                for student_record in search_results:
                    try:
                        student_id = student_record.get('telegram_id')
                        print(f"DEBUG: Processing attachment for student: {student_id}")
                        
                        # Get teacher and student objects
                        teacher = database.Client(teacher_id)
                        student = database.Client(student_id)
                        
                        # Update teacher's my_students field
                        current_students = teacher.my_students or ""
                        if student_id not in current_students:
                            new_students = f"{current_students},{student_id}" if current_students else student_id
                            success_teacher = database.Manager.update(
                                database.Tables.Users,
                                {"telegram_id": teacher_id},
                                {"my_students": new_students}
                            )
                            print(f"DEBUG: Updated teacher my_students: {new_students}, success: {success_teacher}")
                        else:
                            print(f"DEBUG: Student {student_id} already in teacher's list")
                            success_teacher = True
                        
                        # Update student's my_teachers field
                        current_teachers = student.my_teachers or ""
                        if teacher_id not in current_teachers:
                            new_teachers = f"{current_teachers},{teacher_id}" if current_teachers else teacher_id
                            success_student = database.Manager.update(
                                database.Tables.Users,
                                {"telegram_id": student_id},
                                {"my_teachers": new_teachers}
                            )
                            print(f"DEBUG: Updated student my_teachers: {new_teachers}, success: {success_student}")
                        else:
                            print(f"DEBUG: Teacher {teacher_id} already in student's list")
                            success_student = True
                        
                        if success_teacher and success_student:
                            attached_count += 1
                            print(f"DEBUG: Successfully attached student {student_id}")
                        else:
                            print(f"DEBUG: Failed to attach student {student_id}")
                            
                    except Exception as e:
                        print(f"DEBUG: Error processing student attachment: {e}")
                        continue
                
                if attached_count > 0:
                    _out(bot, chat_id, f"Успешно прикреплено {attached_count} учеников!", keyboards.Teacher.main)
                else:
                    _out(bot, chat_id, "Не удалось прикрепить учеников", keyboards.Teacher.main)
            else:
                _out(bot, chat_id, "Нет учеников для прикрепления", keyboards.Teacher.main)
            
            # Clear the flow after action
            del ACTIVE_FLOWS[chat_id]
            print(f"DEBUG: Cleared flow for chat_id: {chat_id}")
            return True
            
        elif request.lower() == "отмена":
            print(f"DEBUG: User cancelled attachment")
            _out(bot, chat_id, "Прикрепление отменено", keyboards.Teacher.main)
            # Clear the flow
            del ACTIVE_FLOWS[chat_id]
            print(f"DEBUG: Cleared flow for chat_id: {chat_id}")
            return True
        
        else:
            print(f"DEBUG: Unknown action in wait_for_action: '{request}'")
            _out(bot, chat_id, "Пожалуйста, выберите действие", keyboards.Teacher.attached)
            return True

def _handle_registration_flow(request: str, chat_id: str) -> bool:
    """Обрабатывает процесс регистрации пользователя"""
    try:
        flow = ACTIVE_FLOWS.get(chat_id)
        if not flow or flow.get("type") not in [FLOW_REGISTER_STUDENT, FLOW_REGISTER_TEACHER]:
            return False
        
        # Отмена регистрации
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("❌ Регистрация отменена пользователем", chat_id, "WARNING")
            _out(bot, chat_id, "Регистрация отменена", keyboards.Guest.main)
            return True

        step = flow.get("step")
        data = flow.get("data", {})
        role = data.get("role")
        
        _log(f"📝 Шаг регистрации: {step}, роль: {role}", chat_id, "DEBUG")

        # Шаг 1: Запрос имени
        if step == "ask_name":
            _out(bot, chat_id, f"📝 Регистрация как {role}\n\n🔸 Введите ваше имя:", keyboards.cancel)
            flow["step"] = "get_name"
            return True
        
        # Шаг 2: Получение имени, запрос фамилии
        elif step == "get_name":
            if not request or len(request.strip()) < 2:
                _out(bot, chat_id, "❌ Имя должно содержать минимум 2 символа. Попробуйте еще раз:", keyboards.cancel)
                return True
            
            data["name"] = request.strip().title()
            _log(f"✅ Получено имя: {data['name']}", chat_id, "SUCCESS")
            _out(bot, chat_id, f"✅ Имя: {data['name']}\n\n🔸 Теперь введите вашу фамилию:", keyboards.cancel)
            flow["step"] = "get_surname"
            return True
        
        # Шаг 3: Получение фамилии, запрос пароля
        elif step == "get_surname":
            if not request or len(request.strip()) < 2:
                _out(bot, chat_id, "❌ Фамилия должна содержать минимум 2 символа. Попробуйте еще раз:", keyboards.cancel)
                return True
            
            data["surname"] = request.strip().title()
            _log(f"✅ Получена фамилия: {data['surname']}", chat_id, "SUCCESS")
            _out(bot, chat_id, f"✅ Фамилия: {data['surname']}\n\n🔸 Придумайте пароль (минимум 6 символов):", keyboards.cancel)
            flow["step"] = "get_password"
            return True
        
        # Шаг 4: Получение пароля
        elif step == "get_password":
            if not request or len(request.strip()) < 6:
                _out(bot, chat_id, "❌ Пароль должен содержать минимум 6 символов. Попробуйте еще раз:", keyboards.cancel)
                return True
            
            data["password"] = request.strip()
            _log("✅ Пароль получен", chat_id, "SUCCESS")
            
            # Переходим к специфичным для роли шагам
            if role == "ученик":
                _out(bot, chat_id, f"✅ Пароль сохранен\n\n🔸 Введите ваш город:", keyboards.cancel)
                flow["step"] = "get_city"
            else:  # учитель
                _out(bot, chat_id, f"✅ Пароль сохранен\n\n🔸 Введите предмет, который вы преподаете:", keyboards.cancel)
                flow["step"] = "get_subject"
            return True
        
        # Шаги для ученика
        elif step == "get_city" and role == "ученик":
            if not request or len(request.strip()) < 2:
                _out(bot, chat_id, "❌ Название города должно содержать минимум 2 символа. Попробуйте еще раз:", keyboards.cancel)
                return True
            
            data["city"] = request.strip().title()
            _log(f"✅ Получен город: {data['city']}", chat_id, "SUCCESS")
            _out(bot, chat_id, f"✅ Город: {data['city']}\n\n🔸 Введите номер школы (только цифры):", keyboards.cancel)
            flow["step"] = "get_school"
            return True
        
        elif step == "get_school" and role == "ученик":
            try:
                school_num = int(request.strip())
                if school_num <= 0:
                    raise ValueError()
            except ValueError:
                _out(bot, chat_id, "❌ Введите корректный номер школы (положительное число):", keyboards.cancel)
                return True
            
            data["school"] = school_num
            _log(f"✅ Получена школа: {data['school']}", chat_id, "SUCCESS")
            _out(bot, chat_id, f"✅ Школа: {data['school']}\n\n🔸 Введите ваш класс (например: 9А, 11Б):", keyboards.cancel)
            flow["step"] = "get_grade"
            return True
        
        elif step == "get_grade" and role == "ученик":
            if not request or len(request.strip()) < 1:
                _out(bot, chat_id, "❌ Укажите ваш класс. Попробуйте еще раз:", keyboards.cancel)
                return True
            
            data["grade"] = request.strip().upper()
            _log(f"✅ Получен класс: {data['grade']}", chat_id, "SUCCESS")
            
            # Завершаем регистрацию ученика
            return _complete_student_registration(chat_id, data)
        
        # Шаги для учителя
        elif step == "get_subject" and role == "учитель":
            if not request or len(request.strip()) < 2:
                _out(bot, chat_id, "❌ Название предмета должно содержать минимум 2 символа. Попробуйте еще раз:", keyboards.cancel)
                return True
            
            data["subject"] = request.strip().title()
            _log(f"✅ Получен предмет: {data['subject']}", chat_id, "SUCCESS")
            _out(bot, chat_id, f"✅ Предмет: {data['subject']}\n\n🔸 Введите ваш город:", keyboards.cancel)
            flow["step"] = "get_teacher_city"
            return True
        
        elif step == "get_teacher_city" and role == "учитель":
            if not request or len(request.strip()) < 2:
                _out(bot, chat_id, "❌ Название города должно содержать минимум 2 символа. Попробуйте еще раз:", keyboards.cancel)
                return True
            
            data["city"] = request.strip().title()
            _log(f"✅ Получен город: {data['city']}", chat_id, "SUCCESS")
            _out(bot, chat_id, f"✅ Город: {data['city']}\n\n🔸 Введите номер школы (только цифры):", keyboards.cancel)
            flow["step"] = "get_teacher_school"
            return True
        
        elif step == "get_teacher_school" and role == "учитель":
            try:
                school_num = int(request.strip())
                if school_num <= 0:
                    raise ValueError()
            except ValueError:
                _out(bot, chat_id, "❌ Введите корректный номер школы (положительное число):", keyboards.cancel)
                return True
            
            data["school"] = school_num
            _log(f"✅ Получена школа: {data['school']}", chat_id, "SUCCESS")
            
            # Завершаем регистрацию учителя
            return _complete_teacher_registration(chat_id, data)
        
        return False
        
    except Exception as e:
        _log(f"💥 Ошибка в процессе регистрации: {e}", chat_id, "ERROR")
        ACTIVE_FLOWS.pop(chat_id, None)
        _out(bot, chat_id, "❌ Произошла ошибка при регистрации. Попробуйте еще раз.", keyboards.Guest.main)
        return True

def _complete_student_registration(chat_id: str, data: dict) -> bool:
    """Завершает регистрацию ученика и создает запись в БД"""
    try:
        _log("📝 Завершение регистрации ученика...", chat_id, "SUCCESS")
        
        # Хешируем пароль (простой пример, в продакшене используйте bcrypt)
        import hashlib
        password_hash = hashlib.sha256(data["password"].encode()).hexdigest()
        
        # Создаем пользователя
        user = database.Tables.Users(
            telegram_id=chat_id,
            username=None,  # Можно добавить позже
            password=password_hash,
            name=data["name"],
            surname=data["surname"],
            role="ученик",
            city=data["city"],
            school=data["school"],
            grade=data["grade"],
            my_teachers=None,
            application=None
        )
        
        # Сохраняем в БД
        success = database.Manager.write(user)
        
        if success:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("🎉 Регистрация ученика завершена успешно", chat_id, "SUCCESS")
            
            welcome_text = f"""🎉 **Регистрация завершена!**

👤 **Ваши данные:**
• Имя: {data['name']} {data['surname']}
• Роль: Ученик
• Город: {data['city']}
• Школа: №{data['school']}
• Класс: {data['grade']}

📚 Теперь вы можете:
• Изучать материалы по алгебре и геометрии
• Искать учителей в вашем городе
• Отправлять заявки на прикрепление
• Получать задания от учителей

🔍 Для поиска учителей используйте команду "заявки" в главном меню."""
            
            _out(bot, chat_id, welcome_text, keyboards.Student.main)
            return True
        else:
            _log("❌ Ошибка сохранения ученика в БД", chat_id, "ERROR")
            _out(bot, chat_id, "❌ Ошибка при сохранении данных. Попробуйте еще раз.", keyboards.Guest.main)
            ACTIVE_FLOWS.pop(chat_id, None)
            return True
            
    except Exception as e:
        _log(f"💥 Ошибка завершения регистрации ученика: {e}", chat_id, "ERROR")
        _out(bot, chat_id, "❌ Произошла ошибка при завершении регистрации.", keyboards.Guest.main)
        ACTIVE_FLOWS.pop(chat_id, None)
        return True

def _complete_teacher_registration(chat_id: str, data: dict) -> bool:
    """Завершает регистрацию учителя и создает запись в БД"""
    try:
        _log("🎓 Завершение регистрации учителя...", chat_id, "SUCCESS")
        
        # Хешируем пароль
        import hashlib
        password_hash = hashlib.sha256(data["password"].encode()).hexdigest()
        
        # Создаем пользователя (для учителя добавляем subject в поле city временно)
        # В будущем можно добавить отдельное поле для предмета
        user = database.Tables.Users(
            telegram_id=chat_id,
            username=None,
            password=password_hash,
            name=data["name"],
            surname=data["surname"],
            role="учитель",
            city=f"{data['city']} - {data['subject']}",  # Временное решение
            school=data["school"],
            grade=None,  # Учителям не нужен класс
            my_students=None,
            application=None
        )
        
        # Сохраняем в БД
        success = database.Manager.write(user)
        
        if success:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("🎉 Регистрация учителя завершена успешно", chat_id, "SUCCESS")
            
            welcome_text = f"""🎉 **Регистрация завершена!**

👨‍🏫 **Ваши данные:**
• Имя: {data['name']} {data['surname']}
• Роль: Учитель
• Предмет: {data['subject']}
• Город: {data['city']}
• Школа: №{data['school']}

📚 Теперь вы можете:
• Создавать и отправлять задания
• Принимать заявки от учеников
• Управлять своими классами
• Проверять решения учеников

👥 Для работы с учениками используйте команды в главном меню."""
            
            _out(bot, chat_id, welcome_text, keyboards.Teacher.main)
            return True
        else:
            _log("❌ Ошибка сохранения учителя в БД", chat_id, "ERROR")
            _out(bot, chat_id, "❌ Ошибка при сохранении данных. Попробуйте еще раз.", keyboards.Guest.main)
            ACTIVE_FLOWS.pop(chat_id, None)
            return True
            
    except Exception as e:
        _log(f"💥 Ошибка завершения регистрации учителя: {e}", chat_id, "ERROR")
        _out(bot, chat_id, "❌ Произошла ошибка при завершении регистрации.", keyboards.Guest.main)
        ACTIVE_FLOWS.pop(chat_id, None)
        return True

def _start_application_flow(chat_id: str) -> None:
    """Запускает процесс отправки заявки учителю"""
    try:
        ACTIVE_FLOWS[chat_id] = {
            "type": FLOW_SEND_APPLICATION, 
            "step": "search_teachers", 
            "data": {}
        }
        _log("📝 Запущен процесс отправки заявки", chat_id, "SUCCESS")
    except Exception as e:
        _log(f"❌ Не удалось запустить процесс заявки: {e}", chat_id, "ERROR")
        print(f"Не удалось запустить сценарий заявки: {e}")

def _handle_application_flow(request: str, chat_id: str) -> bool:
    """Обрабатывает процесс отправки заявки ученика учителю"""
    try:
        flow = ACTIVE_FLOWS.get(chat_id)
        if not flow or flow.get("type") != FLOW_SEND_APPLICATION:
            return False
        
        # Отмена заявки
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("❌ Отправка заявки отменена пользователем", chat_id, "WARNING")
            _out(bot, chat_id, "Отправка заявки отменена", keyboards.Student.main)
            return True

        step = flow.get("step")
        data = flow.get("data", {})
        
        _log(f"📧 Шаг отправки заявки: {step}", chat_id, "DEBUG")

        # Шаг 1: Поиск учителей
        if step == "search_teachers":
            student = database.Client(chat_id)
            student_city = student.city
            student_school = student.school
            
            # Ищем учителей в том же городе и школе
            try:
                # Используем регистронезависимый поиск для города
                filter_dict = {
                    "role": "учитель",
                    "school": student_school
                }
                results = database.Manager.search_records_case_insensitive(database.Tables.Users, filter_dict)
                
                # Дополнительно фильтруем по городу (начинается с города студента)
                if results:
                    filtered_results = []
                    for row in results:
                        if row['city'] and row['city'].lower().startswith(student_city.lower()):
                            filtered_results.append(row)
                    results = filtered_results
                
                if results:
                    teachers_list = []
                    teachers_data = {}
                    
                    for i, row in enumerate(results, 1):
                        try:
                            teacher_id = row["telegram_id"]
                            teacher_name = f"{row['name']} {row['surname']}"
                            # Извлекаем предмет из поля city (формат: "Город - Предмет")
                            city_subject = row['city']
                            subject = city_subject.split(' - ')[-1] if ' - ' in city_subject else "Математика"
                            
                            teachers_list.append(f"{i}. {teacher_name} ({subject})")
                            teachers_data[str(i)] = {
                                "id": teacher_id,
                                "name": teacher_name,
                                "subject": subject
                            }
                        except Exception as e:
                            _log(f"Ошибка обработки учителя: {e}", chat_id, "WARNING")
                            continue
                    
                    if teachers_list:
                        data["teachers"] = teachers_data
                        flow["step"] = "select_teacher"
                        
                        teachers_text = "\n".join(teachers_list)
                        message = f"""👨‍🏫 **Найденные учителя в вашей школе:**

{teachers_text}

🔹 Введите номер учителя, которому хотите отправить заявку:"""
                        
                        _out(bot, chat_id, message, keyboards.cancel)
                        return True
                    else:
                        _out(bot, chat_id, "❌ В вашей школе пока нет зарегистрированных учителей", keyboards.Student.main)
                        ACTIVE_FLOWS.pop(chat_id, None)
                        return True
                else:
                    _out(bot, chat_id, "❌ В вашей школе пока нет зарегистрированных учителей", keyboards.Student.main)
                    ACTIVE_FLOWS.pop(chat_id, None)
                    return True
                    
            except Exception as e:
                _log(f"Ошибка поиска учителей: {e}", chat_id, "ERROR")
                _out(bot, chat_id, "❌ Ошибка при поиске учителей", keyboards.Student.main)
                ACTIVE_FLOWS.pop(chat_id, None)
                return True

        # Шаг 2: Выбор учителя
        elif step == "select_teacher":
            teachers = data.get("teachers", {})
            
            if request not in teachers:
                available_numbers = ", ".join(teachers.keys())
                _out(bot, chat_id, f"❌ Введите корректный номер учителя ({available_numbers}) или 'отмена':", keyboards.cancel)
                return True
            
            selected_teacher = teachers[request]
            data["selected_teacher"] = selected_teacher
            flow["step"] = "write_message"
            
            _log(f"✅ Выбран учитель: {selected_teacher['name']}", chat_id, "SUCCESS")
            
            message = f"""✅ **Выбранный учитель:** {selected_teacher['name']} ({selected_teacher['subject']})

📝 Напишите сообщение для заявки (например, представьтесь и объясните, почему хотите заниматься с этим учителем):"""
            
            _out(bot, chat_id, message, keyboards.cancel)
            return True

        # Шаг 3: Написание сообщения
        elif step == "write_message":
            if not request or len(request.strip()) < 10:
                _out(bot, chat_id, "❌ Сообщение должно содержать минимум 10 символов. Попробуйте еще раз:", keyboards.cancel)
                return True
            
            data["message"] = request.strip()
            flow["step"] = "confirm_send"
            
            selected_teacher = data["selected_teacher"]
            student = database.Client(chat_id)
            
            confirm_text = f"""📋 **Подтверждение заявки:**

👨‍🏫 **Учитель:** {selected_teacher['name']} ({selected_teacher['subject']})
👤 **От:** {student.name} {student.surname} ({student.grade} класс)

📝 **Ваше сообщение:**
{data['message']}

✅ Отправить заявку? (да/нет)"""
            
            _out(bot, chat_id, confirm_text, keyboards.cancel)
            return True

        # Шаг 4: Подтверждение отправки
        elif step == "confirm_send":
            if request.lower() in ["да", "yes", "отправить", "подтвердить"]:
                return _send_application_to_teacher(chat_id, data)
            elif request.lower() in ["нет", "no", "отменить"]:
                ACTIVE_FLOWS.pop(chat_id, None)
                _out(bot, chat_id, "❌ Отправка заявки отменена", keyboards.Student.main)
                return True
            else:
                _out(bot, chat_id, "❌ Введите 'да' для отправки или 'нет' для отмены:", keyboards.cancel)
                return True

        return False
        
    except Exception as e:
        _log(f"💥 Ошибка в процессе заявки: {e}", chat_id, "ERROR")
        ACTIVE_FLOWS.pop(chat_id, None)
        _out(bot, chat_id, "❌ Произошла ошибка при отправке заявки", keyboards.Student.main)
        return True

def _send_application_to_teacher(chat_id: str, data: dict) -> bool:
    """Отправляет заявку учителю и сохраняет в БД"""
    try:
        student = database.Client(chat_id)
        selected_teacher = data["selected_teacher"]
        teacher_id = selected_teacher["id"]
        message = data["message"]
        
        # Формируем заявку для сохранения в БД (в поле application ученика)
        application_data = f"TO:{teacher_id}|MSG:{message}|STATUS:pending"
        
        # Обновляем поле application у ученика
        success = database.Manager.update(
            database.Tables.Users,
            {"telegram_id": chat_id},
            {"application": application_data}
        )
        
        if success:
            # Отправляем уведомление учителю
            teacher_message = f"""📨 **Новая заявка от ученика!**

👤 **От:** {student.name} {student.surname}
🏫 **Школа:** №{student.school}, класс {student.grade}
🏙️ **Город:** {student.city}

📝 **Сообщение:**
{message}

✅ Для принятия заявки используйте команду "заявки" в главном меню.
❌ Для отклонения заявки свяжитесь с учеником напрямую."""

            try:
                bot.send_message(teacher_id, teacher_message)
                _log(f"📧 Уведомление отправлено учителю {teacher_id}", chat_id, "SUCCESS")
            except Exception as e:
                _log(f"⚠️ Не удалось отправить уведомление учителю: {e}", chat_id, "WARNING")
            
            # Сообщение ученику об успешной отправке
            ACTIVE_FLOWS.pop(chat_id, None)
            
            success_message = f"""✅ **Заявка отправлена!**

👨‍🏫 **Учитель:** {selected_teacher['name']} ({selected_teacher['subject']})

📧 Учитель получил уведомление о вашей заявке.
⏳ Ожидайте ответа от учителя.

💡 Вы можете просмотреть статус заявки в главном меню."""
            
            _out(bot, chat_id, success_message, keyboards.Student.main)
            _log("✅ Заявка успешно отправлена", chat_id, "SUCCESS")
            return True
        else:
            _log("❌ Ошибка сохранения заявки в БД", chat_id, "ERROR")
            _out(bot, chat_id, "❌ Ошибка при отправке заявки", keyboards.Student.main)
            ACTIVE_FLOWS.pop(chat_id, None)
            return True
            
    except Exception as e:
        _log(f"💥 Ошибка отправки заявки: {e}", chat_id, "ERROR")
        _out(bot, chat_id, "❌ Произошла ошибка при отправке заявки", keyboards.Student.main)
        ACTIVE_FLOWS.pop(chat_id, None)
        return True

def _show_applications_for_teacher(chat_id: str) -> None:
    """Показывает все заявки для учителя"""
    try:
        # Ищем всех учеников, которые отправили заявки данному учителю
        filter_dict = {
            "role": "ученик"
        }
        results = database.Manager.search_records_unicode_insensitive(database.Tables.Users, filter_dict)
        
        # Дополнительно фильтруем по заявкам
        if results:
            filtered_results = []
            for row in results:
                if row['application'] and f"TO:{chat_id}" in row['application']:
                    filtered_results.append(row)
            results = filtered_results
        
        if not results:
            _out(bot, chat_id, "📭 У вас пока нет заявок от учеников", keyboards.Teacher.main)
            return
        
        applications = []
        for i, row in enumerate(results, 1):
            try:
                student_name = f"{row['name']} {row['surname']}"
                student_id = row['telegram_id']
                grade = row['grade']
                city = row['city']
                school = row['school']
                application_data = row['application']
                
                # Парсим данные заявки
                if application_data and f"TO:{chat_id}" in application_data:
                    parts = application_data.split('|')
                    message = ""
                    status = "pending"
                    
                    for part in parts:
                        if part.startswith("MSG:"):
                            message = part[4:]
                        elif part.startswith("STATUS:"):
                            status = part[7:]
                    
                    status_emoji = "⏳" if status == "pending" else "✅" if status == "accepted" else "❌"
                    
                    applications.append(f"""{i}. {status_emoji} **{student_name}** ({grade} класс)
   🏫 Школа №{school}, {city}
   💬 "{message[:50]}{"..." if len(message) > 50 else ""}"
   👤 ID: `{student_id}`""")
                    
            except Exception as e:
                _log(f"Ошибка обработки заявки: {e}", chat_id, "WARNING")
                continue
        
        if applications:
            applications_text = "\n\n".join(applications)
            message = f"""📨 **Ваши заявки от учеников:**

{applications_text}

💡 **Как принять заявку:**
1. Скопируйте ID ученика
2. Используйте команду "принять ученика"
3. Вставьте ID ученика

❌ **Для отклонения** свяжитесь с учеником напрямую через Telegram."""
            
            _out(bot, chat_id, message, keyboards.Teacher.main)
        else:
            _out(bot, chat_id, "📭 У вас пока нет активных заявок", keyboards.Teacher.main)
            
    except Exception as e:
        _log(f"Ошибка получения заявок: {e}", chat_id, "ERROR")
        _out(bot, chat_id, "❌ Ошибка при получении заявок", keyboards.Teacher.main)

def _start_accept_student_flow(chat_id: str) -> None:
    """Запускает процесс принятия ученика"""
    try:
        ACTIVE_FLOWS[chat_id] = {
            "type": FLOW_MANAGE_APPLICATIONS, 
            "step": "get_student_id", 
            "data": {}
        }
        _log("👥 Запущен процесс принятия ученика", chat_id, "SUCCESS")
        _out(bot, chat_id, "👥 **Принятие ученика**\n\n📋 Введите ID ученика (скопируйте из списка заявок):", keyboards.cancel)
    except Exception as e:
        _log(f"❌ Не удалось запустить процесс принятия ученика: {e}", chat_id, "ERROR")
        print(f"Не удалось запустить сценарий принятия ученика: {e}")

def _handle_accept_student_flow(request: str, chat_id: str) -> bool:
    """Обрабатывает процесс принятия ученика учителем"""
    try:
        flow = ACTIVE_FLOWS.get(chat_id)
        if not flow or flow.get("type") != FLOW_MANAGE_APPLICATIONS:
            return False
        
        # Отмена процесса
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("❌ Принятие ученика отменено", chat_id, "WARNING")
            _out(bot, chat_id, "Принятие ученика отменено", keyboards.Teacher.main)
            return True

        step = flow.get("step")
        
        if step == "get_student_id":
            student_id = request.strip()
            
            # Проверяем, что ученик существует и отправлял заявку этому учителю
            try:
                student = database.Client(student_id)
                if student.role != "ученик":
                    _out(bot, chat_id, "❌ Указанный ID не принадлежит ученику. Попробуйте еще раз:", keyboards.cancel)
                    return True
                
                # Проверяем заявку
                application_data = student.application
                if not application_data or f"TO:{chat_id}" not in application_data:
                    _out(bot, chat_id, "❌ От этого ученика нет заявки для вас. Проверьте ID:", keyboards.cancel)
                    return True
                
                # Принимаем ученика
                return _accept_student(chat_id, student_id, student)
                
            except Exception as e:
                _log(f"Ошибка проверки ученика: {e}", chat_id, "ERROR")
                _out(bot, chat_id, "❌ Ученик с таким ID не найден. Проверьте правильность ID:", keyboards.cancel)
                return True

        return False
        
    except Exception as e:
        _log(f"💥 Ошибка принятия ученика: {e}", chat_id, "ERROR")
        ACTIVE_FLOWS.pop(chat_id, None)
        _out(bot, chat_id, "❌ Произошла ошибка при принятии ученика", keyboards.Teacher.main)
        return True

def _accept_student(teacher_id: str, student_id: str, student) -> bool:
    """Принимает ученика - обновляет связи в БД"""
    try:
        teacher = database.Client(teacher_id)
        
        # Обновляем my_teachers у ученика
        current_teachers = student.my_teachers or ""
        if teacher_id not in current_teachers:
            new_teachers = f"{current_teachers},{teacher_id}" if current_teachers else teacher_id
            
            # Обновляем статус заявки на accepted
            application_parts = student.application.split('|')
            new_application_parts = []
            for part in application_parts:
                if part.startswith("STATUS:"):
                    new_application_parts.append("STATUS:accepted")
                else:
                    new_application_parts.append(part)
            new_application = "|".join(new_application_parts)
            
            success_student = database.Manager.update(
                database.Tables.Users,
                {"telegram_id": student_id},
                {"my_teachers": new_teachers, "application": new_application}
            )
        else:
            success_student = True  # Уже добавлен
        
        # Обновляем my_students у учителя
        current_students = teacher.my_students or ""
        if student_id not in current_students:
            new_students = f"{current_students},{student_id}" if current_students else student_id
            success_teacher = database.Manager.update(
                database.Tables.Users,
                {"telegram_id": teacher_id},
                {"my_students": new_students}
            )
        else:
            success_teacher = True  # Уже добавлен
        
        if success_student and success_teacher:
            ACTIVE_FLOWS.pop(teacher_id, None)
            
            # Уведомляем учителя
            teacher_message = f"""✅ **Ученик принят!**

👤 **Ученик:** {student.name} {student.surname}
🏫 **Школа:** №{student.school}, класс {student.grade}
🏙️ **Город:** {student.city}

🎉 Теперь вы можете отправлять задания этому ученику!
📚 Используйте команду "создать задание" в главном меню."""
            
            _out(bot, teacher_id, teacher_message, keyboards.Teacher.main)
            
            # Уведомляем ученика
            try:
                teacher_city_subject = teacher.city
                subject = teacher_city_subject.split(' - ')[-1] if ' - ' in teacher_city_subject else "Математика"
                
                student_message = f"""🎉 **Ваша заявка принята!**

👨‍🏫 **Учитель:** {teacher.name} {teacher.surname} ({subject})
🏫 **Школа:** №{teacher.school}

📚 Теперь вы можете получать задания от этого учителя!
💡 Следите за новыми сообщениями в боте."""
                
                bot.send_message(student_id, student_message)
                _log(f"📧 Уведомление отправлено ученику {student_id}", teacher_id, "SUCCESS")
            except Exception as e:
                _log(f"⚠️ Не удалось отправить уведомление ученику: {e}", teacher_id, "WARNING")
            
            _log(f"✅ Ученик {student_id} принят учителем {teacher_id}", teacher_id, "SUCCESS")
            return True
        else:
            _log("❌ Ошибка обновления БД при принятии ученика", teacher_id, "ERROR")
            _out(bot, teacher_id, "❌ Ошибка при принятии ученика", keyboards.Teacher.main)
            ACTIVE_FLOWS.pop(teacher_id, None)
            return True
            
    except Exception as e:
        _log(f"💥 Ошибка принятия ученика: {e}", teacher_id, "ERROR")
        _out(bot, teacher_id, "❌ Произошла ошибка при принятии ученика", keyboards.Teacher.main)
        ACTIVE_FLOWS.pop(teacher_id, None)
        return True

def _show_profile_for_editing(chat_id: str) -> None:
    """Показывает текущий профиль пользователя с возможностью выбора поля для редактирования"""
    try:
        user = database.Client(chat_id)
        role = user.role
        
        if role == "ученик":
            profile_text = f"""👤 **Ваш профиль (Ученик):**

📝 **Основная информация:**
• Имя: {user.name}
• Фамилия: {user.surname}
• Роль: {user.role}

🏫 **Учебная информация:**
• Город: {user.city}
• Школа: №{user.school}
• Класс: {user.grade}

🔹 **Что вы хотите изменить?**
Выберите поле для редактирования:"""

            edit_keyboard = keyboards.create_keyboard(
                ["Изменить имя", "Изменить фамилию"],
                ["Изменить город", "Изменить школу"],
                ["Изменить класс", "Изменить пароль"],
                ["/главная", "Отмена"]
            )
            
        else:  # учитель
            # Извлекаем город и предмет из поля city
            city_subject = user.city if user.city else "Не указано"
            if " - " in city_subject:
                city, subject = city_subject.split(" - ", 1)
            else:
                city = city_subject
                subject = "Не указан"
            
            profile_text = f"""👨‍🏫 **Ваш профиль (Учитель):**

📝 **Основная информация:**
• Имя: {user.name}
• Фамилия: {user.surname}
• Роль: {user.role}

🏫 **Профессиональная информация:**
• Предмет: {subject}
• Город: {city}
• Школа: №{user.school}

🔹 **Что вы хотите изменить?**
Выберите поле для редактирования:"""

            edit_keyboard = keyboards.create_keyboard(
                ["Изменить имя", "Изменить фамилию"],
                ["Изменить предмет", "Изменить город"],
                ["Изменить школу", "Изменить пароль"],
                ["/главная", "Отмена"]
            )
        
        _out(bot, chat_id, profile_text, edit_keyboard)
        
    except Exception as e:
        _log(f"Ошибка показа профиля для редактирования: {e}", chat_id, "ERROR")
        role = database.find_my_role(chat_id)
        main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
        _out(bot, chat_id, "❌ Ошибка при загрузке профиля", main_keyboard)

def _start_edit_profile_flow(chat_id: str) -> None:
    """Запускает процесс редактирования профиля"""
    try:
        ACTIVE_FLOWS[chat_id] = {"type": FLOW_EDIT_PROFILE, "step": "ask_field", "data": {}}
        _log("🚀 Запущен процесс редактирования профиля", chat_id, "SUCCESS")
    except Exception as e:
        _log(f"❌ Не удалось запустить редактирование профиля: {e}", chat_id, "ERROR")
        print(f"Не удалось запустить сценарий редактирования профиля: {e}")

def _handle_edit_profile_flow(request: str, chat_id: str) -> bool:
    """Обрабатывает процесс редактирования профиля"""
    try:
        flow = ACTIVE_FLOWS.get(chat_id)
        if not flow or flow.get("type") != FLOW_EDIT_PROFILE:
            return False
        
        # Отмена редактирования
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("❌ Редактирование профиля отменено", chat_id, "WARNING")
            role = database.find_my_role(chat_id)
            main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
            _out(bot, chat_id, "Редактирование профиля отменено", main_keyboard)
            return True

        step = flow.get("step")
        data = flow.get("data", {})
        user = database.Client(chat_id)
        
        _log(f"✏️ Шаг редактирования профиля: {step}", chat_id, "DEBUG")

        # Выбор поля для редактирования
        if step == "show_profile":
            field_mappings = {
                "изменить имя": "name",
                "изменить фамилию": "surname", 
                "изменить город": "city",
                "изменить школу": "school",
                "изменить класс": "grade",
                "изменить предмет": "subject",
                "изменить пароль": "password"
            }
            
            field_key = field_mappings.get(request)
            if not field_key:
                _out(bot, chat_id, "❌ Выберите поле для редактирования из предложенных вариантов:", keyboards.cancel)
                return True
            
            data["field"] = field_key
            flow["step"] = "get_new_value"
            
            # Определяем текст запроса в зависимости от поля
            field_prompts = {
                "name": "📝 Введите новое имя:",
                "surname": "📝 Введите новую фамилию:",
                "city": "🏙️ Введите новый город:",
                "school": "🏫 Введите новый номер школы (только цифры):",
                "grade": "📚 Введите новый класс (например: 9А, 11Б):",
                "subject": "📖 Введите новый предмет:",
                "password": "🔒 Введите новый пароль (минимум 6 символов):"
            }
            
            prompt = field_prompts.get(field_key, "Введите новое значение:")
            _out(bot, chat_id, prompt, keyboards.cancel)
            return True
        
        # Получение нового значения
        elif step == "get_new_value":
            field = data.get("field")
            new_value = request.strip()
            
            # Валидация в зависимости от поля
            if field == "name" or field == "surname":
                if len(new_value) < 2:
                    _out(bot, chat_id, "❌ Минимум 2 символа. Попробуйте еще раз:", keyboards.cancel)
                    return True
                new_value = new_value.title()
                
            elif field == "city":
                if len(new_value) < 2:
                    _out(bot, chat_id, "❌ Название города должно содержать минимум 2 символа:", keyboards.cancel)
                    return True
                new_value = new_value.title()
                
            elif field == "school":
                try:
                    school_num = int(new_value)
                    if school_num <= 0:
                        raise ValueError()
                    new_value = school_num
                except ValueError:
                    _out(bot, chat_id, "❌ Введите корректный номер школы (положительное число):", keyboards.cancel)
                    return True
                    
            elif field == "grade":
                if len(new_value) < 1:
                    _out(bot, chat_id, "❌ Укажите ваш класс:", keyboards.cancel)
                    return True
                new_value = new_value.upper()
                
            elif field == "subject":
                if len(new_value) < 2:
                    _out(bot, chat_id, "❌ Название предмета должно содержать минимум 2 символа:", keyboards.cancel)
                    return True
                new_value = new_value.title()
                
            elif field == "password":
                if len(new_value) < 6:
                    _out(bot, chat_id, "❌ Пароль должен содержать минимум 6 символов:", keyboards.cancel)
                    return True
                # Хешируем новый пароль
                import hashlib
                new_value = hashlib.sha256(new_value.encode()).hexdigest()
            
            # Сохраняем изменения
            return _update_profile_field(chat_id, field, new_value, user)
        
        return False
        
    except Exception as e:
        _log(f"💥 Ошибка редактирования профиля: {e}", chat_id, "ERROR")
        ACTIVE_FLOWS.pop(chat_id, None)
        role = database.find_my_role(chat_id)
        main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
        _out(bot, chat_id, "❌ Произошла ошибка при редактировании профиля", main_keyboard)
        return True

def _update_profile_field(chat_id: str, field: str, new_value, user) -> bool:
    """Обновляет конкретное поле профиля пользователя"""
    try:
        success = False
        
        # Специальная обработка для учителей (предмет сохраняется в city)
        if field == "subject" and user.role == "учитель":
            # Извлекаем текущий город
            current_city_subject = user.city if user.city else ""
            if " - " in current_city_subject:
                city = current_city_subject.split(" - ")[0]
            else:
                city = current_city_subject
            
            # Формируем новое значение city с предметом
            new_city_value = f"{city} - {new_value}"
            success = database.Manager.update(
                database.Tables.Users,
                {"telegram_id": chat_id},
                {"city": new_city_value}
            )
            
        elif field == "city" and user.role == "учитель":
            # Сохраняем предмет при изменении города учителя
            current_city_subject = user.city if user.city else ""
            if " - " in current_city_subject:
                subject = current_city_subject.split(" - ", 1)[1]
            else:
                subject = "Математика"  # значение по умолчанию
            
            new_city_value = f"{new_value} - {subject}"
            success = database.Manager.update(
                database.Tables.Users,
                {"telegram_id": chat_id},
                {"city": new_city_value}
            )
        else:
            # Обычное обновление поля
            success = database.Manager.update(
                database.Tables.Users,
                {"telegram_id": chat_id},
                {field: new_value}
            )
        
        if success:
            ACTIVE_FLOWS.pop(chat_id, None)
            
            # Определяем название поля для пользователя
            field_names = {
                "name": "Имя",
                "surname": "Фамилия", 
                "city": "Город",
                "school": "Школа",
                "grade": "Класс",
                "subject": "Предмет",
                "password": "Пароль"
            }
            
            field_name = field_names.get(field, "Поле")
            display_value = new_value if field != "password" else "••••••"
            
            success_message = f"""✅ **Профиль обновлен!**

📝 **{field_name}** изменен{'' if field in ['имя', 'фамилия'] else 'о'} на: **{display_value}**

Изменения сохранены в базе данных."""
            
            role = database.find_my_role(chat_id)
            main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
            _out(bot, chat_id, success_message, main_keyboard)
            
            _log(f"✅ Поле {field} успешно обновлено для пользователя {chat_id}", chat_id, "SUCCESS")
            return True
        else:
            _log("❌ Ошибка сохранения изменений в БД", chat_id, "ERROR")
            role = database.find_my_role(chat_id)
            main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
            _out(bot, chat_id, "❌ Ошибка при сохранении изменений", main_keyboard)
            ACTIVE_FLOWS.pop(chat_id, None)
            return True
            
    except Exception as e:
        _log(f"💥 Ошибка обновления поля профиля: {e}", chat_id, "ERROR")
        role = database.find_my_role(chat_id)
        main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
        _out(bot, chat_id, "❌ Произошла ошибка при обновлении профиля", main_keyboard)
        ACTIVE_FLOWS.pop(chat_id, None)
        return True

def _start_password_reset_flow(chat_id: str) -> None:
    """Запускает процесс восстановления пароля"""
    try:
        # Проверяем, зарегистрирован ли пользователь
        role = database.find_my_role(chat_id)
        if not role:
            _out(bot, chat_id, "❌ Вы не зарегистрированы в системе. Для начала пройдите регистрацию.", keyboards.Guest.main)
            return
            
        ACTIVE_FLOWS[chat_id] = {
            "type": FLOW_RESET_PASSWORD, 
            "step": "verify_identity", 
            "data": {"role": role}
        }
        _log("🔑 Запущен процесс восстановления пароля", chat_id, "SUCCESS")
        
        user = database.Client(chat_id)
        
        # Показываем информацию для верификации
        if role == "ученик":
            verification_text = f"""🔑 **Восстановление пароля**

👤 **Для подтверждения личности введите:**
• Ваше полное имя (Имя Фамилия)

📝 **Пример:** Иван Петров

⚠️ **Внимание:** Данные должны точно совпадать с теми, что указаны в вашем профиле."""
        else:  # учитель
            verification_text = f"""🔑 **Восстановление пароля**

👨‍🏫 **Для подтверждения личности введите:**
• Ваше полное имя (Имя Фамилия)

📝 **Пример:** Мария Иванова

⚠️ **Внимание:** Данные должны точно совпадать с теми, что указаны в вашем профиле."""
        
        _out(bot, chat_id, verification_text, keyboards.cancel)
        
    except Exception as e:
        _log(f"❌ Не удалось запустить восстановление пароля: {e}", chat_id, "ERROR")
        print(f"Не удалось запустить сценарий восстановления пароля: {e}")

def _handle_password_reset_flow(request: str, chat_id: str) -> bool:
    """Обрабатывает процесс восстановления пароля"""
    try:
        flow = ACTIVE_FLOWS.get(chat_id)
        if not flow or flow.get("type") != FLOW_RESET_PASSWORD:
            return False
        
        # Отмена восстановления
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("❌ Восстановление пароля отменено", chat_id, "WARNING")
            role = database.find_my_role(chat_id)
            main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
            _out(bot, chat_id, "Восстановление пароля отменено", main_keyboard)
            return True

        step = flow.get("step")
        data = flow.get("data", {})
        role = data.get("role")
        
        _log(f"🔑 Шаг восстановления пароля: {step}", chat_id, "DEBUG")

        # Верификация личности
        if step == "verify_identity":
            user = database.Client(chat_id)
            
            # Проверяем введенное полное имя
            input_name = request.strip().title()
            expected_name = f"{user.name} {user.surname}"
            
            if input_name != expected_name:
                _out(bot, chat_id, f"❌ Неверные данные. Ожидается: {expected_name}\nПопробуйте еще раз или введите 'отмена':", keyboards.cancel)
                return True
            
            # Дополнительная верификация для большей безопасности
            flow["step"] = "verify_additional"
            
            if role == "ученик":
                additional_text = f"""✅ **Имя подтверждено!**

🏫 **Дополнительная проверка:**
Введите номер вашей школы

📝 Введите только цифры (например: 15)"""
            else:  # учитель
                # Извлекаем предмет учителя
                city_subject = user.city if user.city else ""
                if " - " in city_subject:
                    subject = city_subject.split(" - ", 1)[1]
                else:
                    subject = "Математика"
                
                additional_text = f"""✅ **Имя подтверждено!**

📖 **Дополнительная проверка:**
Введите предмет, который вы преподаете

📝 Ожидается: {subject}"""
                
                data["expected_subject"] = subject
            
            _out(bot, chat_id, additional_text, keyboards.cancel)
            return True
        
        # Дополнительная верификация
        elif step == "verify_additional":
            user = database.Client(chat_id)
            
            if role == "ученик":
                try:
                    input_school = int(request.strip())
                    if input_school != user.school:
                        _out(bot, chat_id, f"❌ Неверный номер школы. Попробуйте еще раз или введите 'отмена':", keyboards.cancel)
                        return True
                except ValueError:
                    _out(bot, chat_id, "❌ Введите корректный номер школы (только цифры):", keyboards.cancel)
                    return True
            else:  # учитель
                input_subject = request.strip().title()
                expected_subject = data.get("expected_subject", "")
                
                if input_subject != expected_subject:
                    _out(bot, chat_id, f"❌ Неверный предмет. Ожидается: {expected_subject}\nПопробуйте еще раз или введите 'отмена':", keyboards.cancel)
                    return True
            
            # Верификация пройдена, запрашиваем новый пароль
            flow["step"] = "get_new_password"
            _out(bot, chat_id, "✅ **Личность подтверждена!**\n\n🔒 Введите новый пароль (минимум 6 символов):", keyboards.cancel)
            return True
        
        # Получение нового пароля
        elif step == "get_new_password":
            new_password = request.strip()
            
            if len(new_password) < 6:
                _out(bot, chat_id, "❌ Пароль должен содержать минимум 6 символов. Попробуйте еще раз:", keyboards.cancel)
                return True
            
            # Подтверждение пароля
            data["new_password"] = new_password
            flow["step"] = "confirm_password"
            _out(bot, chat_id, "🔒 Повторите новый пароль для подтверждения:", keyboards.cancel)
            return True
        
        # Подтверждение нового пароля
        elif step == "confirm_password":
            confirm_password = request.strip()
            new_password = data.get("new_password")
            
            if confirm_password != new_password:
                _out(bot, chat_id, "❌ Пароли не совпадают. Введите подтверждение пароля еще раз:", keyboards.cancel)
                return True
            
            # Сохраняем новый пароль
            return _save_new_password(chat_id, new_password)
        
        return False
        
    except Exception as e:
        _log(f"💥 Ошибка восстановления пароля: {e}", chat_id, "ERROR")
        ACTIVE_FLOWS.pop(chat_id, None)
        role = database.find_my_role(chat_id)
        main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
        _out(bot, chat_id, "❌ Произошла ошибка при восстановлении пароля", main_keyboard)
        return True

def _save_new_password(chat_id: str, new_password: str) -> bool:
    """Сохраняет новый пароль в БД"""
    try:
        # Хешируем новый пароль
        import hashlib
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        # Обновляем пароль в БД
        success = database.Manager.update(
            database.Tables.Users,
            {"telegram_id": chat_id},
            {"password": password_hash}
        )
        
        if success:
            ACTIVE_FLOWS.pop(chat_id, None)
            
            success_message = """🎉 **Пароль успешно восстановлен!**

🔒 Ваш новый пароль сохранен в системе.
✅ Теперь вы можете использовать его для различных операций.

💡 Рекомендуем запомнить или записать новый пароль в безопасном месте."""
            
            role = database.find_my_role(chat_id)
            main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
            _out(bot, chat_id, success_message, main_keyboard)
            
            _log(f"✅ Пароль успешно восстановлен для пользователя {chat_id}", chat_id, "SUCCESS")
            return True
        else:
            _log("❌ Ошибка сохранения нового пароля в БД", chat_id, "ERROR")
            role = database.find_my_role(chat_id)
            main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
            _out(bot, chat_id, "❌ Ошибка при сохранении нового пароля", main_keyboard)
            ACTIVE_FLOWS.pop(chat_id, None)
            return True
            
    except Exception as e:
        _log(f"💥 Ошибка сохранения нового пароля: {e}", chat_id, "ERROR")
        role = database.find_my_role(chat_id)
        main_keyboard = keyboards.Student.main if role == "ученик" else keyboards.Teacher.main
        _out(bot, chat_id, "❌ Произошла ошибка при сохранении пароля", main_keyboard)
        ACTIVE_FLOWS.pop(chat_id, None)
        return True

def _show_my_teachers(chat_id: str) -> None:
    """Показывает список учителей ученика"""
    try:
        student = database.Client(chat_id)
        teachers_ids = student.my_teachers
        
        if not teachers_ids:
            message = """👨‍🏫 **Мои учителя**

📭 У вас пока нет прикрепленных учителей.

💡 **Как прикрепиться к учителю:**
1. Используйте команду "заявки"
2. Выберите учителя из списка
3. Отправьте заявку
4. Дождитесь принятия от учителя"""
            
            _out(bot, chat_id, message, keyboards.Student.main)
            return
        
        # Получаем информацию об учителях
        teacher_list = []
        teacher_ids_array = teachers_ids.split(',')
        
        for teacher_id in teacher_ids_array:
            if teacher_id.strip():
                try:
                    teacher = database.Client(teacher_id.strip())
                    teacher_city_subject = teacher.city
                    subject = teacher_city_subject.split(' - ')[-1] if ' - ' in teacher_city_subject else "Математика"
                    
                    teacher_list.append(f"👨‍🏫 **{teacher.name} {teacher.surname}**")
                    teacher_list.append(f"   📚 Предмет: {subject}")
                    teacher_list.append(f"   🏫 Школа: №{teacher.school}")
                    teacher_list.append(f"   📞 ID: `{teacher_id.strip()}`")
                    teacher_list.append("")
                    
                except Exception as e:
                    _log(f"Ошибка получения данных учителя {teacher_id}: {e}", chat_id, "WARNING")
                    continue
        
        if teacher_list:
            teachers_text = "\n".join(teacher_list[:-1])  # Убираем последний пустой элемент
            message = f"""👨‍🏫 **Мои учителя**

{teachers_text}

💬 Для связи с учителем используйте его Telegram ID.
📚 Ожидайте задания от ваших учителей в боте."""
        else:
            message = "❌ Не удалось загрузить информацию об учителях"
        
        _out(bot, chat_id, message, keyboards.Student.main)
        
    except Exception as e:
        _log(f"Ошибка получения списка учителей: {e}", chat_id, "ERROR")
        _out(bot, chat_id, "❌ Ошибка при получении списка учителей", keyboards.Student.main)


def _get_help_text(role: str) -> str:
    """Возвращает текст помощи в зависимости от роли пользователя."""
    
    # Базовые команды для всех
    base_help = """📚 ДОСТУПНЫЕ КОМАНДЫ:

🔸 ОСНОВНЫЕ КОМАНДЫ:
• /главная - вернуться в главное меню
• помощь - показать эту справку
• забыл пароль - восстановление забытого пароля

🔸 ТЕОРЕТИЧЕСКИЕ МАТЕРИАЛЫ (доступны всем):
• алгебра - 🤖 Полностью AI-управляемые материалы
• геометрия - 🤖 AI-управляемые материалы с изображениями
• вычислительные навыки - работа с числами и дробями
• найти значение выражения - упрощение выражений
• формулы сокращённого умножения - ФСУ
• уравнения - решение различных уравнений
• неравенства - решение неравенств
• графики - построение графиков функций
• тригонометрия - тригонометрические функции

🔸 СОЦИАЛЬНЫЕ ФУНКЦИИ:
• Прикрепить класс - учителя могут прикреплять учеников к себе
• Мои учителя - ученики видят список прикрепленных учителей
• Система заявок - ученики отправляют заявки учителям

🤖 AI ФУНКЦИИ В АЛГЕБРЕ:
Раздел "алгебра" полностью переведен на AI! Доступны:
• 🤖 AI Объяснение - интерактивный AI помощник
• 🤖 AI Практика - генерация задач и проверка решений
• 📚 AI Материалы - все темы алгебры генерируются AI

🔸 РАЗДЕЛЫ АЛГЕБРЫ (AI-генерируемые):
• вычислительные навыки - дроби, проценты, степени
• найти значение выражения - подстановка и упрощение
• работа с формулами - преобразования и применение
• формулы сокращённого умножения - ФСУ
• уравнения - все типы уравнений
• неравенства - линейные и квадратные
• графики - функции и их графики
• тригонометрия - основы и уравнения
• теория вероятностей - основные понятия

🔸 РАЗДЕЛЫ ГЕОМЕТРИИ (🤖 AI-управляемые с изображениями):
• треугольники - 📐 типы, свойства, формулы с диаграммами
• четырёхугольники - ⬜ квадрат, ромб, параллелограмм с визуализацией
• окружность - ⭕ элементы окружности, формулы с диаграммами
• площади и объёмы - 📏 формулы 2D и 3D фигур с изображениями
• координатная геометрия - 📊 координатная плоскость с графиками

🤖 ПОДРОБНО О AI ФУНКЦИЯХ:

КАК ИСПОЛЬЗОВАТЬ:
1. Наберите "алгебра"
2. Нажмите "🤖 AI Объяснение" или "🤖 AI Практика" (вверху меню)
3. Выберите нужную функцию
4. Следуйте инструкциям бота
5. Для выхода из AI режима: нажмите /главная или "отмена"

ДОСТУПНЫЕ AI КОМАНДЫ:
• 🤖 объяснить тему - подробное объяснение любой темы
• 🤖 решить задачу - пошаговое решение задач  
• 🤖 сгенерировать задачи - создание практических заданий
• 🤖 проверить решение - анализ и исправление ошибок
• 🤖 дать советы - практические рекомендации по изучению
• 🤖 план изучения - персональный план обучения

💡 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:
• "Объясни квадратные уравнения"
• "Реши: x² - 5x + 6 = 0"
• "Создай задачи по логарифмам"
• "Проверь мое решение..."

⏳ ВРЕМЯ ОТВЕТА: AI обработка займет 10-15 секунд
🎨 ФОРМАТИРОВАНИЕ: Ответы отправляются с Markdown форматированием (**жирный**, *курсив*, `формулы`)
📝 ПРИМЕЧАНИЕ: LaTeX символы ($$ или $) автоматически удаляются
⚠️ ТРЕБУЕТСЯ: API ключ OpenAI для работы AI функций"""

    if role == "учитель":
        return base_help + """

🔸 КОМАНДЫ ДЛЯ УЧИТЕЛЯ:
• профиль - управление профилем
• заявки - просмотр заявок от учеников ✅
• принять ученика - принять заявку ученика ✅
• прикрепить класс - найти и прикрепить учеников ✅
• мои учащиеся - список прикреплённых учеников ✅
• отправить задание - работа с заданиями ✅
• проверить задания - проверка решений ✅
• ai помощник - AI инструменты для учителя
• удалить профиль - удаление аккаунта

🔸 РАБОТА С ЗАДАНИЯМИ:
• Отправить индивидуальное задание - создание и отправка заданий ученикам
• Получить задания - просмотр отправленных заданий
• ✍️ проверить #ID - проверка решений учеников
• Выставление оценок и комментариев

✅ **Система заявок активна!** Ученики могут отправлять вам заявки."""
    
    elif role == "ученик":
        return base_help + """

🔸 КОМАНДЫ ДЛЯ УЧЕНИКА:
• профиль - управление профилем
• заявки - отправить заявку учителю ✅
• мои учителя - список прикрепленных учителей ✅
• задания - работа с заданиями
• получить задания - получить новые задания
• отправить решение - отправить выполненную работу
• сгенерировать задание - создать задание по теме
• тест-викторина - интерактивные тесты по математике ✅

✅ **Система заявок активна!** Найдите учителей в вашей школе и отправьте заявку.

🔸 РАБОТА С ЗАДАНИЯМИ:
• Получить задания - просмотр заданий от учителей
• ✍️ ответить #ID - отправка решения по заданию
• 🎯 оценка #ID - просмотр оценки и комментария учителя

🔸 ТЕСТ-ВИКТОРИНА:
• Выбор темы: алгебра, геометрия, тригонометрия, арифметика
• Уровни сложности: легкий, средний, сложный
• 5 вопросов с множественным выбором
• Автоматическая проверка и оценка

• ai помощник - AI помощь в обучении
• проверить решение - проверка решения через AI
• практика - тренировочные задания
• удалить профиль - удаление аккаунта"""
    
    else:
        return base_help + """

🔸 ДЛЯ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ:
• зарегистрироваться как ученик - регистрация ученика
• зарегистрироваться как учитель - регистрация учителя

📝 Процесс регистрации включает:
Для учеников: имя, фамилия, город, школа, класс, пароль
Для учителей: имя, фамилия, предмет, город, школа, пароль

После регистрации ученики могут искать учителей и отправлять заявки на прикрепление."""

    return base_help

def _start_individual_assignment_flow(chat_id: str) -> None:
    """Запускает процесс создания и отправки индивидуального задания"""
    try:
        ACTIVE_FLOWS[chat_id] = {"type": FLOW_INDIVIDUAL_ASSIGNMENT, "step": "ask_student", "data": {}}
        _log("🚀 Запущен процесс создания индивидуального задания", chat_id, "SUCCESS")
    except Exception as e:
        _log(f"❌ Не удалось запустить создание задания: {e}", chat_id, "ERROR")
        print(f"Не удалось запустить сценарий создания задания: {e}")

def _handle_individual_assignment_flow(request: str, chat_id: str) -> bool:
    """Обрабатывает процесс создания и отправки индивидуального задания"""
    try:
        flow = ACTIVE_FLOWS.get(chat_id)
        if not flow or flow.get("type") != FLOW_INDIVIDUAL_ASSIGNMENT:
            return False
        
        # Отмена создания задания
        if request == FLOW_CANCEL:
            ACTIVE_FLOWS.pop(chat_id, None)
            _log("❌ Создание задания отменено пользователем", chat_id, "WARNING")
            _out(bot, chat_id, "Создание задания отменено", keyboards.Teacher.main)
            return True

        step = flow.get("step")
        data = flow.get("data", {})
        
        _log(f"📝 Шаг создания задания: {step}", chat_id, "DEBUG")

        # Шаг 1: Выбор ученика
        if step == "ask_student":
            # Получаем список прикрепленных учеников
            teacher = database.Client(chat_id)
            student_ids = teacher.my_students.split(",") if teacher.my_students else []
            
            if not student_ids:
                _out(bot, chat_id, "У вас нет прикрепленных учеников", keyboards.Teacher.main)
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
            
            # Создаем список учеников для выбора
            student_options = []
            student_names = []
            for sid in student_ids:
                try:
                    student = database.Client(sid)
                    student_names.append(f"{student.name} {student.surname}")
                    student_options.append(sid)
                except Exception as e:
                    print(f"DEBUG: Error getting student {sid}: {e}")
                    continue
            
            if not student_names:
                _out(bot, chat_id, "Не удалось загрузить список учеников", keyboards.Teacher.main)
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
            
            # Сохраняем список учеников для выбора
            data["student_options"] = student_options
            data["student_names"] = student_names
            
            # Создаем клавиатуру с учениками
            student_keyboard = keyboards.create_keyboard(
                student_names,
                ["Отмена"]
            )
            
            _out(bot, chat_id, "Выберите ученика для отправки задания:", student_keyboard)
            flow["step"] = "verify_student"
            return True
        
        # Шаг 2: Проверка выбора ученика
        elif step == "verify_student":
            student_names = data.get("student_names", [])
            student_options = data.get("student_options", [])
            
            print(f"DEBUG: verify_student - request: '{request}'")
            print(f"DEBUG: verify_student - student_names: {student_names}")
            print(f"DEBUG: verify_student - student_options: {student_options}")
            
            # Проверяем точное совпадение
            if request in student_names:
                print(f"DEBUG: Exact match found for '{request}'")
                # Находим ID выбранного ученика
                student_index = student_names.index(request)
                selected_student_id = student_options[student_index]
                data["selected_student_id"] = selected_student_id
                data["selected_student_name"] = request
                
                flow["step"] = "ask_topic"
                _out(bot, chat_id, "Выберите тему для задания:", keyboards.create_keyboard(
                    ["Алгебра", "Геометрия", "Тригонометрия", "Арифметика"],
                    ["Отмена"]
                ))
                return True
            else:
                # Проверяем совпадение без учета регистра и с заменой "ё" на "е"
                transformed_request = core.transform_request(request)
                print(f"DEBUG: Transformed request: '{transformed_request}'")
                
                for i, name in enumerate(student_names):
                    transformed_name = core.transform_request(name)
                    print(f"DEBUG: Comparing '{transformed_request}' with '{transformed_name}'")
                    if transformed_request == transformed_name:
                        print(f"DEBUG: Transformed match found for '{request}' -> '{name}'")
                        # Находим ID выбранного ученика
                        selected_student_id = student_options[i]
                        data["selected_student_id"] = selected_student_id
                        data["selected_student_name"] = name
                        
                        flow["step"] = "ask_topic"
                        _out(bot, chat_id, "Выберите тему для задания:", keyboards.create_keyboard(
                            ["Алгебра", "Геометрия", "Тригонометрия", "Арифметика"],
                            ["Отмена"]
                        ))
                        return True
                
                # Если совпадение не найдено
                print(f"DEBUG: No match found for '{request}'")
                _out(bot, chat_id, "Пожалуйста, выберите ученика из списка", keyboards.create_keyboard(
                    data.get("student_names", []),
                    ["Отмена"]
                ))
                return True
        
        # Шаг 3: Выбор темы
        elif step == "ask_topic":
            # Проверяем совпадение без учета регистра
            topics = ["Алгебра", "Геометрия", "Тригонометрия", "Арифметика"]
            topic_match = None
            
            # Сначала проверяем точное совпадение
            if request in topics:
                topic_match = request
            else:
                # Проверяем совпадение без учета регистра
                transformed_request = core.transform_request(request)
                for topic in topics:
                    if core.transform_request(topic) == transformed_request:
                        topic_match = topic
                        break
            
            if topic_match:
                data["topic"] = topic_match
                flow["step"] = "ask_difficulty"
                _out(bot, chat_id, "Выберите сложность задания:", keyboards.create_keyboard(
                    ["Легкая", "Средняя", "Сложная"],
                    ["Отмена"]
                ))
                return True
            else:
                _out(bot, chat_id, "Пожалуйста, выберите тему из списка", keyboards.create_keyboard(
                    ["Алгебра", "Геометрия", "Тригонометрия", "Арифметика"],
                    ["Отмена"]
                ))
                return True
        
        # Шаг 4: Выбор сложности
        elif step == "ask_difficulty":
            # Проверяем совпадение без учета регистра
            difficulties = ["Легкая", "Средняя", "Сложная"]
            difficulty_match = None
            
            # Сначала проверяем точное совпадение
            if request in difficulties:
                difficulty_match = request
            else:
                # Проверяем совпадение без учета регистра
                transformed_request = core.transform_request(request)
                for difficulty in difficulties:
                    if core.transform_request(difficulty) == transformed_request:
                        difficulty_match = difficulty
                        break
            
            if difficulty_match:
                data["difficulty"] = difficulty_match
                flow["step"] = "generate_assignment"
                
                # Генерируем задание с помощью LLM
                _out(bot, chat_id, "🤖 Генерирую задание... Пожалуйста, подождите.")
                
                try:
                    # Импортируем LLM модуль
                    from LLM import LLM, ResponseType
                    
                    llm = LLM()
                    llm.set_role("math teacher")
                    llm.set_response_type(ResponseType.EXPLANATION)
                    
                    # Формируем промпт для генерации задания
                    prompt = f"""Создай математическое задание по теме "{data['topic']}" со сложностью "{data['difficulty']}".

Требования:
- Задание должно быть понятным и интересным
- Уровень сложности должен соответствовать выбранному
- Задание должно быть на русском языке
- Не давай решение, только условие
- Используй Markdown форматирование

Формат ответа:
**Задание по {data['topic']} ({data['difficulty']} уровень)**

[Условие задания]

**Что нужно найти/доказать/вычислить:**
[Описание того, что требуется от ученика]"""
                    
                    assignment_text = llm.ask(prompt)
                    
                    if assignment_text and "OpenAI клиент недоступен" not in assignment_text:
                        # Сохраняем задание в данных
                        data["assignment_text"] = assignment_text
                        
                        # Показываем сгенерированное задание
                        _out(bot, chat_id, f"✅ Задание сгенерировано!\n\n{assignment_text}\n\nОтправить это задание ученику {data['selected_student_name']}?", 
                              keyboards.create_keyboard(["Да, отправить", "Нет, отменить"]))
                        
                        flow["step"] = "confirm_send"
                        return True
                    else:
                        _out(bot, chat_id, "❌ Не удалось сгенерировать задание. Попробуйте позже.", keyboards.Teacher.main)
                        ACTIVE_FLOWS.pop(chat_id, None)
                        return True
                        
                except Exception as e:
                    print(f"DEBUG: Error generating assignment: {e}")
                    _out(bot, chat_id, f"❌ Ошибка при генерации задания: {e}", keyboards.Teacher.main)
                    ACTIVE_FLOWS.pop(chat_id, None)
                    return True
            else:
                _out(bot, chat_id, "Пожалуйста, выберите сложность из списка", keyboards.create_keyboard(
                    ["Легкая", "Средняя", "Сложная"],
                    ["Отмена"]
                ))
                return True
        
        # Шаг 5: Подтверждение отправки
        elif step == "confirm_send":
            # Проверяем совпадение без учета регистра
            if request == "Да, отправить" or core.transform_request(request) == "да, отправить":
                try:
                    # Отправляем задание ученику
                    student_id = data.get("selected_student_id")
                    student_name = data.get("selected_student_name")
                    topic = data.get("topic")
                    difficulty = data.get("difficulty")
                    assignment_text = data.get("assignment_text")
                    
                    # Формируем сообщение для ученика
                    student_message = f"""📚 **Новое задание от вашего учителя!**

**Предмет:** {topic}
**Сложность:** {difficulty}

{assignment_text}

💡 **Срок выполнения:** до следующего урока
📝 **Отправьте решение в ответном сообщении**"""
                    
                    # Сохраняем задание в базе данных
                    assignment_saved = database.Manager.create_assignment(
                        sender_id=chat_id,
                        recipient_id=student_id,
                        task_text=assignment_text,
                        topic=topic,
                        difficulty=difficulty
                    )
                    
                    if assignment_saved:
                        # Отправляем задание ученику
                        bot.send_message(student_id, student_message)
                        
                        # Уведомляем учителя об успешной отправке
                        _out(bot, chat_id, f"✅ Задание успешно отправлено ученику {student_name} и сохранено в базе данных!", keyboards.Teacher.main)
                        
                        _log(f"📚 Задание по {topic} отправлено ученику {student_id} и сохранено", chat_id, "SUCCESS")
                    else:
                        _out(bot, chat_id, f"⚠️ Задание отправлено ученику {student_name}, но не удалось сохранить в базе данных", keyboards.Teacher.main)
                    
                except Exception as e:
                    print(f"DEBUG: Error sending assignment: {e}")
                    _out(bot, chat_id, f"❌ Ошибка при отправке задания: {e}", keyboards.Teacher.main)
                
                # Завершаем flow
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
                
            elif request == "Нет, отменить" or core.transform_request(request) == "нет, отменить":
                _out(bot, chat_id, "Создание задания отменено", keyboards.Teacher.main)
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
            else:
                _out(bot, chat_id, "Пожалуйста, выберите действие", keyboards.create_keyboard(["Да, отправить", "Нет, отменить"]))
                return True
        
        return False
        
    except Exception as e:
        _log(f"💥 Ошибка создания индивидуального задания: {e}", chat_id, "ERROR")
        _out(bot, chat_id, "Произошла ошибка при создании задания", keyboards.Teacher.main)
        ACTIVE_FLOWS.pop(chat_id, None)
        return True


def _start_quiz_flow(chat_id: str) -> None:
    """Запускает flow тест-викторины"""
    try:
        _log("🧩 Запуск flow тест-викторины", chat_id, "SUCCESS")
        ACTIVE_FLOWS[chat_id] = {
            "type": FLOW_QUIZ,
            "step": "ask_topic",
            "data": {}
        }
    except Exception as e:
        _log(f"💥 Ошибка запуска flow тест-викторины: {e}", chat_id, "ERROR")


def _handle_quiz_flow(request: str, chat_id: str) -> bool:
    """Обрабатывает flow тест-викторины"""
    try:
        if chat_id not in ACTIVE_FLOWS:
            return False
        
        flow = ACTIVE_FLOWS[chat_id]
        step = flow["step"]
        data = flow["data"]
        
        # Шаг 1: Выбор темы
        if step == "ask_topic":
            _out(bot, chat_id, "🧩 **Тест-викторина по математике**\n\nВыберите тему для тестирования:", 
                  keyboards.create_keyboard(
                      ["Алгебра", "Геометрия", "Тригонометрия", "Арифметика"],
                      ["Отмена"]
                  ))
            flow["step"] = "receive_topic"
            return True
        
        # Шаг 2: Получение темы
        elif step == "receive_topic":
            topics = ["Алгебра", "Геометрия", "Тригонометрия", "Арифметика"]
            topic_match = None
            
            # Проверяем совпадение без учета регистра
            if request in topics:
                topic_match = request
            else:
                transformed_request = core.transform_request(request)
                for topic in topics:
                    if core.transform_request(topic) == transformed_request:
                        topic_match = topic
                        break
            
            if topic_match:
                data["topic"] = topic_match
                flow["step"] = "ask_difficulty"
                
                _out(bot, chat_id, f"✅ Тема: {topic_match}\n\nТеперь выберите уровень сложности:", 
                      keyboards.create_keyboard(
                          ["Легкая", "Средняя", "Сложная"],
                          ["Отмена"]
                      ))
                return True
            else:
                _out(bot, chat_id, "Пожалуйста, выберите тему из списка", keyboards.create_keyboard(
                    ["Алгебра", "Геометрия", "Тригонометрия", "Арифметика"],
                    ["Отмена"]
                ))
                return True
        
        # Шаг 3: Выбор сложности
        elif step == "ask_difficulty":
            difficulties = ["Легкая", "Средняя", "Сложная"]
            difficulty_match = None
            
            # Проверяем совпадение без учета регистра
            if request in difficulties:
                difficulty_match = request
            else:
                transformed_request = core.transform_request(request)
                for difficulty in difficulties:
                    if core.transform_request(difficulty) == transformed_request:
                        difficulty_match = difficulty
                        break
            
            if difficulty_match:
                data["difficulty"] = difficulty_match
                flow["step"] = "generate_quiz"
                
                # Генерируем тест-викторину с помощью LLM
                _out(bot, chat_id, "🤖 Генерирую тест-викторину... Пожалуйста, подождите.")
                
                try:
                    # Импортируем LLM модуль
                    from LLM import LLM, ResponseType
                    
                    llm = LLM()
                    llm.set_role("math teacher")
                    llm.set_response_type(ResponseType.EXPLANATION)
                    
                    # Формируем промпт для генерации тест-викторины
                    prompt = f"""Создай тест-викторину по математике на тему "{data['topic']}" со сложностью "{data['difficulty']}".

Требования:
- Создай 5 заданий (вопросов)
- Каждое задание должно содержать 3 утверждения
- Ученик должен выбрать правильные утверждения (1, 2, 3 или их комбинации)
- Уровень сложности должен соответствовать выбранному
- Задания должны быть на русском языке
- В конце дай правильные ответы

Формат ответа (строго соблюдай):
### Задание 1:

1. [утверждение 1]
2. [утверждение 2] 
3. [утверждение 3]

Ваш ответ: __

### Задание 2:

1. [утверждение 1]
2. [утверждение 2]
3. [утверждение 3]

Ваш ответ: __

[и так далее для 5 заданий]

### Ответы:
Задание 1 - [правильные номера]
Задание 2 - [правильные номера]
[и так далее]"""
                    
                    quiz_text = llm.ask(prompt)
                    
                    if quiz_text and "OpenAI клиент недоступен" not in quiz_text:
                        # Сохраняем тест-викторину в данных
                        data["quiz_text"] = quiz_text
                        
                        # Показываем сообщение о готовности, но НЕ показываем вопросы
                        _out(bot, chat_id, f"✅ Тест-викторина готова!\n\nТеперь отвечайте на вопросы по одному. Начните с первого задания.", 
                              keyboards.create_keyboard(["Начать ответы", "Отмена"]))
                        
                        flow["step"] = "start_answers"
                        return True
                    else:
                        _out(bot, chat_id, "❌ Не удалось сгенерировать тест-викторину. Попробуйте позже.", keyboards.Student.task)
                        ACTIVE_FLOWS.pop(chat_id, None)
                        return True
                        
                except Exception as e:
                    print(f"DEBUG: Error generating quiz: {e}")
                    _out(bot, chat_id, f"❌ Ошибка при генерации тест-викторины: {e}", keyboards.Student.task)
                    ACTIVE_FLOWS.pop(chat_id, None)
                    return True
            else:
                _out(bot, chat_id, "Пожалуйста, выберите сложность из списка", keyboards.create_keyboard(
                    ["Легкая", "Средняя", "Сложная"],
                    ["Отмена"]
                ))
                return True
        
        # Шаг 4: Начало ответов
        elif step == "start_answers":
            if request == "Начать ответы" or request == "начать ответы":
                data["current_question"] = 1
                data["student_answers"] = {}
                flow["step"] = "ask_question"
                
                # Показываем первое задание (без правильных ответов)
                quiz_text = data.get("quiz_text", "")
                questions = _extract_questions_from_quiz(quiz_text)
                
                # Сохраняем вопросы в flow data для последующего показа в результатах
                data["questions"] = questions
                
                # Добавляем отладочную информацию
                _log(f"🔍 Извлечено вопросов: {len(questions) if questions else 0}", chat_id, "DEBUG")
                if questions:
                    _log(f"🔍 Первый вопрос: {questions[0][:100]}...", chat_id, "DEBUG")
                
                if questions and len(questions) > 0:
                    first_question = questions[0]
                    # Убираем строку "Ваш ответ: __" из вопроса
                    first_question_clean = first_question.replace("Ваш ответ: __", "").replace("Ваш ответ: _", "").strip()
                    _out(bot, chat_id, f"🧩 **Задание 1:**\n\n{first_question_clean}\n\nВведите ваш ответ (например: 1, 2, 12, 23, 123, 1,2,3):", 
                          keyboards.create_keyboard(["Отмена"]))
                    return True
                else:
                    _out(bot, chat_id, "❌ Ошибка при разборе тест-викторины", keyboards.Student.task)
                    ACTIVE_FLOWS.pop(chat_id, None)
                    return True
            else:
                _out(bot, chat_id, "Пожалуйста, выберите действие", keyboards.create_keyboard(["Начать ответы", "Отмена"]))
                return True
        
        # Шаг 5: Обработка ответов на вопросы
        elif step == "ask_question":
            current_question = data.get("current_question", 1)
            
            # Очищаем ввод от лишних пробелов, но сохраняем запятые
            cleaned_input = request.strip()
            
            # Проверяем, что ответ содержит только цифры 1, 2, 3 и запятые
            if not cleaned_input.replace(" ", "").replace(",", "").isdigit() or not all(c in "123," for c in cleaned_input.replace(" ", "")):
                _out(bot, chat_id, "❌ Пожалуйста, введите ответ, используя только цифры 1, 2, 3 и запятые (например: 1, 12, 23, 123, 1,2,3):", 
                      keyboards.create_keyboard(["Отмена"]))
                return True
            
            # Сохраняем ответ ученика в оригинальном формате (только убираем лишние пробелы)
            student_answer = cleaned_input
            data["student_answers"][current_question] = student_answer
            
            # Проверяем, есть ли еще вопросы
            quiz_text = data.get("quiz_text", "")
            questions = _extract_questions_from_quiz(quiz_text)
            
            if current_question < len(questions):
                # Переходим к следующему вопросу
                next_question = current_question + 1
                data["current_question"] = next_question
                
                next_question_text = questions[next_question - 1]
                # Убираем строку "Ваш ответ: __" из вопроса
                next_question_clean = next_question_text.replace("Ваш ответ: __", "").replace("Ваш ответ: _", "").strip()
                _out(bot, chat_id, f"✅ Ответ на задание {current_question} сохранен!\n\n🧩 **Задание {next_question}:**\n\n{next_question_clean}\n\nВведите ваш ответ (например: 1, 2, 12, 23, 123, 1,2,3):", 
                      keyboards.create_keyboard(["Отмена"]))
                return True
            else:
                # Все вопросы отвечены, показываем результаты
                flow["step"] = "show_results"
                
                _out(bot, chat_id, "🎯 Все задания выполнены! Сейчас покажу ваши результаты.", 
                      keyboards.create_keyboard(["Показать результаты", "Отмена"]))
                return True
        
        # Шаг 6: Показ результатов
        elif step == "show_results":
            if request == "Показать результаты" or request == "показать результаты":
                # Получаем данные для детального отчета
                quiz_text = data.get("quiz_text", "")
                correct_answers = _extract_correct_answers_from_quiz(quiz_text)
                student_answers = data.get("student_answers", {})
                questions = data.get("questions", [])  # Получаем сохраненные вопросы
                
                # Формируем детальный отчет о результатах
                results_text = "🎯 **Детальные результаты тест-викторины:**\n\n"
                
                total_questions = len(correct_answers)
                correct_count = 0
                
                for question_num in range(1, total_questions + 1):
                    student_answer = student_answers.get(question_num, "Не отвечено")
                    correct_answer = correct_answers.get(question_num, "Не найдено")
                    
                    # Нормализуем ответы для сравнения (убираем пробелы и сортируем цифры)
                    def normalize_answer(answer):
                        if not answer or answer in ["Не отвечено", "Не найдено"]:
                            return answer
                        # Убираем пробелы, разбиваем по запятым, сортируем и соединяем
                        digits = [d.strip() for d in str(answer).replace(" ", "").split(",") if d.strip()]
                        return "".join(sorted(digits))
                    
                    normalized_student = normalize_answer(student_answer)
                    normalized_correct = normalize_answer(correct_answer)
                    is_correct = normalized_student == normalized_correct
                    if is_correct:
                        correct_count += 1
                        status = "✅ Правильно"
                    else:
                        status = "❌ Неправильно"
                    
                    # Добавляем полный вопрос с вариантами ответов
                    results_text += f"📝 **Задание {question_num}:**\n"
                    
                    # Показываем вопрос с вариантами ответов
                    if question_num <= len(questions):
                        question_text = questions[question_num - 1]
                        # Убираем "Ваш ответ: __" из отображения
                        question_display = question_text.replace("Ваш ответ: __", "").replace("Ваш ответ: _", "").strip()
                        results_text += f"{question_display}\n\n"
                    
                    # Показываем ответы студента и правильные
                    results_text += f"🎯 **Ваш ответ:** {student_answer}\n"
                    results_text += f"✅ **Правильный ответ:** {correct_answer}\n"
                    results_text += f"📊 **Статус:** {status}\n"
                    
                    # Добавляем анализ ответа
                    if not is_correct and student_answer != "Не отвечено":
                        results_text += f"💡 **Анализ:** Ваш ответ '{student_answer}' не совпадает с правильным '{correct_answer}'\n"
                    
                    results_text += "\n" + "─" * 40 + "\n\n"
                
                # Вычисляем процент правильных ответов
                percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
                
                results_text += f"📊 **Итоговый результат:**\n"
                results_text += f"Правильных ответов: {correct_count} из {total_questions}\n"
                results_text += f"Процент правильных ответов: {percentage:.1f}%\n\n"
                
                if percentage >= 80:
                    grade = "Отлично! 🏆"
                elif percentage >= 60:
                    grade = "Хорошо! 👍"
                elif percentage >= 40:
                    grade = "Удовлетворительно! 📝"
                else:
                    grade = "Требует доработки! 💪"
                
                results_text += f"**Оценка:** {grade}\n\n"
                results_text += f"📚 **Тема:** {data.get('topic', 'Неизвестно')}\n"
                results_text += f"⚡ **Сложность:** {data.get('difficulty', 'Неизвестно')}\n\n"
                results_text += f"💡 **Рекомендации:**\n"
                
                if percentage >= 80:
                    results_text += "• Отличный результат! Продолжайте в том же духе!\n"
                    results_text += "• Можете попробовать более сложные задания\n"
                elif percentage >= 60:
                    results_text += "• Хороший результат! Есть небольшие пробелы в знаниях\n"
                    results_text += "• Рекомендуется повторить материал по темам с ошибками\n"
                elif percentage >= 40:
                    results_text += "• Удовлетворительный результат, но есть пробелы\n"
                    results_text += "• Рекомендуется детально изучить материал\n"
                else:
                    results_text += "• Результат требует улучшения\n"
                    results_text += "• Рекомендуется повторить материал и попробовать снова\n"
                
                _out(bot, chat_id, results_text, keyboards.Student.task)
                
                # Завершаем flow
                ACTIVE_FLOWS.pop(chat_id, None)
                return True
            else:
                _out(bot, chat_id, "Пожалуйста, выберите действие", keyboards.create_keyboard(["Показать результаты", "Отмена"]))
                return True
        
        # Обработка отмены
        if request == "Отмена" or core.transform_request(request) == "отмена":
            _out(bot, chat_id, "Тест-викторина отменена", keyboards.Student.task)
            ACTIVE_FLOWS.pop(chat_id, None)
            return True
        
        return False
        
    except Exception as e:
        _log(f"💥 Ошибка тест-викторины: {e}", chat_id, "ERROR")
        _out(bot, chat_id, "Произошла ошибка при проведении тест-викторины", keyboards.Student.task)
        ACTIVE_FLOWS.pop(chat_id, None)
        return True


def _extract_questions_from_quiz(quiz_text: str) -> list:
    """Извлекает вопросы из текста тест-викторины"""
    try:
        questions = []
        lines = quiz_text.split('\n')
        current_question_lines = []
        in_question_block = False
        
        print(f"DEBUG: Parsing quiz text with {len(lines)} lines")
        
        # Debug: show first few lines to understand the format
        print(f"DEBUG: First 10 lines:")
        for j in range(min(10, len(lines))):
            print(f"DEBUG: Line {j}: '{lines[j].strip()}'")
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Check for question header (e.g., "### Задание 1:", "#### Задание 1:", or "Задание 1:")
            is_question_header = (line.startswith("### Задание") or line.startswith("#### Задание") or line.startswith("Задание")) and \
                                 any(f" {num}:" in line for num in range(1, 6))  # Check for " 1:", " 2:", ..., " 5:"
            
            # Debug logging for header detection
            if line.startswith("### Задание") or line.startswith("#### Задание") or line.startswith("Задание"):
                print(f"DEBUG: Potential header at line {i}: '{line}' - is_question_header: {is_question_header}")
            
            # Check for end of question block markers
            is_answer_prompt = line.startswith("Ваш ответ:")
            is_quiz_answers_section = line.startswith("### Ответы:") or line.startswith("Ответы:")
            
            if is_question_header:
                print(f"DEBUG: Found question header at line {i}: '{line}'")
                # If we were in a question block, save the previous question
                if in_question_block and current_question_lines:
                    questions.append("\n".join(current_question_lines).strip())
                    current_question_lines = []  # Reset for new question
                in_question_block = True
                current_question_lines.append(line)
            elif is_answer_prompt:
                print(f"DEBUG: Found answer prompt at line {i}: '{line}'")
                if in_question_block and current_question_lines:
                    current_question_lines.append(line)  # Include "Ваш ответ: __" as part of the question
                    questions.append("\n".join(current_question_lines).strip())
                    current_question_lines = []  # Reset for next question
                in_question_block = False  # End of a question block
            elif is_quiz_answers_section:
                print(f"DEBUG: Found quiz answers section at line {i}: '{line}'")
                if in_question_block and current_question_lines:
                    questions.append("\n".join(current_question_lines).strip())
                current_question_lines = []  # Clear any remaining lines, as we are past questions
                in_question_block = False  # End of all question blocks
                break  # Stop processing lines for questions
            elif in_question_block:
                current_question_lines.append(line)
        
        # Add any remaining question if the quiz text ended without an explicit answer section
        if in_question_block and current_question_lines:
            questions.append("\n".join(current_question_lines).strip())
        
        print(f"DEBUG: Extracted {len(questions)} questions")
        for i, q in enumerate(questions):
            print(f"DEBUG: Question {i+1}: {q[:100]}...")
        return questions
    except Exception as e:
        print(f"DEBUG: Error extracting questions: {e}")
        return []


def _extract_correct_answers_from_quiz(quiz_text: str) -> dict:
    """Извлекает правильные ответы из текста тест-викторины"""
    try:
        answers = {}
        lines = quiz_text.split('\n')
        
        print(f"DEBUG: Extracting answers from quiz text with {len(lines)} lines")
        
        for i, line in enumerate(lines):
            line = line.strip()
            print(f"DEBUG: Processing line {i}: '{line}'")
            
            # Проверяем различные форматы ответов
            if line.startswith("Задание") and (" - " in line or "- " in line):
                # Форматы: "Задание 1 - 23", "Задание 2- 13", "Задание 3 - 1"
                if " - " in line:
                    parts = line.split(" - ")
                else:
                    parts = line.split("- ")
                
                if len(parts) == 2:
                    question_part = parts[0].strip()
                    answer_part = parts[1].strip()
                    
                    print(f"DEBUG: Found answer line - question_part: '{question_part}', answer_part: '{answer_part}'")
                    
                    # Извлекаем номер задания
                    if "Задание" in question_part:
                        question_num = question_part.replace("Задание", "").strip().replace(":", "").strip()
                        try:
                            question_num = int(question_num)
                            answers[question_num] = answer_part
                            print(f"DEBUG: Extracted answer for question {question_num}: '{answer_part}'")
                        except ValueError:
                            print(f"DEBUG: Could not parse question number from '{question_num}'")
                            continue
        
        print(f"DEBUG: Final extracted answers: {answers}")
        return answers
    except Exception as e:
        print(f"DEBUG: Error extracting answers: {e}")
        return {}

@bot.message_handler()
def main(msg):
    try:
        chat_id = str(msg.chat.id)
        original_text = msg.text
        request = core.transform_request(msg.text)
        
        # Логируем входящее сообщение
        _log(f"📨 Получено сообщение: '{original_text}' -> преобразовано: '{request}'", chat_id)
        
        # Определяем роль пользователя для логирования
        role = database.find_my_role(chat_id)
        if role:
            _log(f"👤 Роль пользователя: {role}", chat_id, "SUCCESS")
        else:
            _log("👤 Пользователь не зарегистрирован (гость)", chat_id, "WARNING")

        # 1) Активные сценарии (удаление профиля / поиск учеников / регистрация) - ПРИОРИТЕТ!
        _log("🔄 Проверка активных сценариев...", chat_id, "DEBUG")
        
        # Показываем текущий flow для отладки
        current_flow = ACTIVE_FLOWS.get(chat_id)
        if current_flow:
            _log(f"🔍 Текущий flow: {current_flow}", chat_id, "DEBUG")
            print(f"DEBUG: Main handler - Current flow: {current_flow}")
        else:
            _log("🔍 Активных flow нет", chat_id, "DEBUG")
            print(f"DEBUG: Main handler - No active flow")
        
        _log(f"🔍 Обрабатываемое сообщение: '{request}'", chat_id, "DEBUG")
        
        if _handle_delete_flow(request, chat_id):
            _log("🗑️ Запрос обработан сценарием удаления профиля", chat_id, "SUCCESS")
            return
        if _handle_search_flow(request, chat_id):
            _log("🔍 Запрос обработан сценарием поиска учеников", chat_id, "SUCCESS")
            return
        if _handle_registration_flow(request, chat_id):
            _log("📝 Запрос обработан сценарием регистрации", chat_id, "SUCCESS")
            return
        if _handle_application_flow(request, chat_id):
            _log("📧 Запрос обработан сценарием заявки", chat_id, "SUCCESS")
            return
        if _handle_accept_student_flow(request, chat_id):
            _log("👥 Запрос обработан сценарием принятия ученика", chat_id, "SUCCESS")
            return
        if _handle_edit_profile_flow(request, chat_id):
            _log("✏️ Запрос обработан сценарием редактирования профиля", chat_id, "SUCCESS")
            return
        if _handle_password_reset_flow(request, chat_id):
            _log("🔑 Запрос обработан сценарием восстановления пароля", chat_id, "SUCCESS")
            return
        if _handle_individual_assignment_flow(request, chat_id):
            _log("📚 Запрос обработан сценарием создания индивидуального задания", chat_id, "SUCCESS")
            return
        if _handle_quiz_flow(request, chat_id):
            _log("🧩 Запрос обработан сценарием тест-викторины", chat_id, "SUCCESS")
            return
        if _handle_submit_answer_flow(request, chat_id):
            _log("✍️ Запрос обработан сценарием отправки ответа", chat_id, "SUCCESS")
            return
        if _handle_review_assignment_flow(request, chat_id):
            _log("📝 Запрос обработан сценарием проверки ответа", chat_id, "SUCCESS")
            return

        # 2) Теоретические материалы (единые для всех)
        _log("🔍 Проверка теоретических материалов...", chat_id, "DEBUG")
        if _handle_theory(request, bot, chat_id):
            _log("📚 Запрос обработан модулем теории", chat_id, "SUCCESS")
            return

        # 3) Универсальные команды (единые для всех)
        _log("🌐 Проверка универсальных команд...", chat_id, "DEBUG")
        if request in START_COMMANDS:
            _log(f"🏠 Обработка START команды: {request}", chat_id, "SUCCESS")
            _out(bot, chat_id, "главная", keyboards.create_keyboard(["/главная"], ["Помощь"]))
            return
        if request in HELP_COMMANDS or request == "помощь":
            _log(f"❓ Обработка HELP команды: {request}", chat_id, "SUCCESS")
            # Определяем роль пользователя для показа соответствующих команд
            help_role = database.find_my_role(chat_id)
            help_text = _get_help_text(help_role)
            _out(bot, chat_id, help_text, keyboards.create_keyboard(["/главная"]))
            return
        if request in ("забыл пароль", "восстановить пароль", "сбросить пароль", "forgot password"):
            _log(f"🔑 Обработка команды восстановления пароля: {request}", chat_id, "SUCCESS")
            _start_password_reset_flow(chat_id)
            return
        if request == "назад":
            _log(f"⬅️ Обработка команды 'Назад': {request}", chat_id, "SUCCESS")
            # Определяем роль пользователя и возвращаем к соответствующему главному меню
            user_role = database.find_my_role(chat_id)
            if user_role == "ученик":
                _out(bot, chat_id, "Главное меню", keyboards.Student.main)
            elif user_role == "учитель":
                _out(bot, chat_id, "Главное меню", keyboards.Teacher.main)
            else:
                _out(bot, chat_id, "Главное меню", keyboards.Guest.main)
            return

        # 4) Ветвление по роли пользователя
        _log("🎭 Обработка команд по роли пользователя...", chat_id, "DEBUG")
        role = database.find_my_role(chat_id)

        if role == "учитель":
            _log(f"👩‍🏫 Обработка команды учителя: {request}", chat_id, "SUCCESS")
            # Простая, плоская логика для учителя
            if request == "профиль":
                _out(bot, chat_id, "Выберите действие", keyboards.Teacher.profile)
            elif request == "мои учащиеся":
                _show_teacher_students(bot, chat_id)
            elif request == "прикрепить класс":
                _start_search_flow(chat_id)
                # Немедленно показать первый шаг
                _handle_search_flow("", chat_id)
            elif request == "заявки":
                _log("📨 Показ заявок учителю", chat_id, "SUCCESS")
                _show_applications_for_teacher(chat_id)
            elif request == "принять ученика":
                _log("👥 Запуск процесса принятия ученика", chat_id, "SUCCESS")
                _start_accept_student_flow(chat_id)
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
                    _log("📝 Запуск процесса отправки индивидуального задания", chat_id, "SUCCESS")
                    _start_individual_assignment_flow(chat_id)
                    _handle_individual_assignment_flow("", chat_id)  # Запускаем первый шаг
            elif request == "отправить задание классу":
                client = database.Client(chat_id)
                if not getattr(client, "my_students", None):
                    _out(bot, chat_id, "У вас пока нет прикрепленных учеников", keyboards.Teacher.main)
                else:
                    _out(bot, chat_id, "Функция отправки задания классу в упрощенной версии пока недоступна", keyboards.Teacher.main)
            elif request == "проверить задания" or request == "проверить индивидуальные задания" or request == "задания для класса":
                _show_teacher_assignments(bot, chat_id)
            elif request == "мои задания":
                _show_teacher_assignments(bot, chat_id)
            elif request.startswith("✍️ проверить #"):
                # Извлекаем ID задания из кнопки
                assignment_id = request.split("#")[1]
                _start_review_assignment_flow(chat_id, assignment_id)
                _handle_review_assignment_flow(request, chat_id)  # Инициируем первый шаг flow
            elif request == "ai помощник":
                _out(bot, chat_id, "Раздел AI Помощник", keyboards.Teacher.ai_helper)
            elif request == "редактировать профиль":
                _start_edit_profile_flow(chat_id)
            elif request == "удалить профиль":
                _start_delete_flow(chat_id)
                _handle_delete_flow("", chat_id)
            else:
                _out(bot, chat_id, "Неизвестная команда")
            return

        if role == "ученик":
            _log(f"👨‍🎓 Обработка команды ученика: {request}", chat_id, "SUCCESS")
            _log(f"🔍 Проверяем команды ученика для: '{request}'", chat_id, "DEBUG")
            # Простая, плоская логика для ученика
            if request == "профиль":
                _out(bot, chat_id, "Выберите действие", keyboards.Student.profile)
            elif request == "заявки":
                _log("📧 Запуск процесса отправки заявки", chat_id, "SUCCESS")
                _start_application_flow(chat_id)
                _handle_application_flow("", chat_id)  # Запускаем первый шаг
            elif request == "мои учителя":
                _show_my_teachers(chat_id)
            elif request == "задания":
                _out(bot, chat_id, "Выберите действие с заданиями", keyboards.Student.task)
            elif request in ("получить задания", "отправить решение"):
                _show_student_assignments(bot, chat_id)
            elif request.startswith("✍️ ответить #"):
                # Извлекаем ID задания из кнопки
                assignment_id = request.split("#")[1]
                _log(f"🔍 Обработка команды '✍️ ответить #{assignment_id}'", chat_id, "DEBUG")
                _start_submit_answer_flow(chat_id, assignment_id)
                _handle_submit_answer_flow(request, chat_id)  # Инициируем первый шаг flow
            elif request.startswith("🎯 оценка #"):
                # Извлекаем ID задания из кнопки
                assignment_id = request.split("#")[1]
                _show_assignment_grade(bot, chat_id, assignment_id)
            elif request == "сгенерировать задание":
                _out(bot, chat_id, "Укажите тему, по которой сгенерировать одно задание (без решения)")
            elif request == "тест-викторина":
                _log("📝 Запуск тест-викторины", chat_id, "SUCCESS")
                _start_quiz_flow(chat_id)
                _handle_quiz_flow("", chat_id)
            elif request == "ai помощник":
                _out(bot, chat_id, "Раздел AI Помощник", keyboards.Student.ai_helper)
            elif request in ("практика", "проверить решение"):
                _out(bot, chat_id, "Функция AI помощника в упрощенной версии пока недоступна", keyboards.Student.ai_helper)
            elif request == "редактировать профиль":
                _start_edit_profile_flow(chat_id)
            elif request == "удалить профиль":
                _start_delete_flow(chat_id)
                _handle_delete_flow("", chat_id)
            else:
                _out(bot, chat_id, "Неизвестная команда")
            return

        # Гость / неизвестная роль
        _log(f"👻 Обработка команды гостя: {request}", chat_id, "WARNING")
        if request == "зарегистрироваться как ученик":
            _log("📝 Запуск регистрации ученика", chat_id, "SUCCESS")
            _start_registration_flow(chat_id, "ученик")
            _handle_registration_flow("", chat_id)  # Запускаем первый шаг
        elif request == "зарегистрироваться как учитель":
            _log("📝 Запуск регистрации учителя", chat_id, "SUCCESS")
            _start_registration_flow(chat_id, "учитель")
            _handle_registration_flow("", chat_id)  # Запускаем первый шаг
        else:
            _log(f"❓ Неизвестная команда гостя: {request}", chat_id, "WARNING")
            _out(bot, chat_id, "Неизвестная команда. Для начала работы зарегистрируйтесь.", keyboards.Guest.main)
    except Exception as e:
        _log(f"💥 КРИТИЧЕСКАЯ ОШИБКА обработки сообщения: {e}", chat_id, "ERROR")
        print(f"Ошибка обработки сообщения: {e}")
        try:
            bot.send_message(msg.chat.id, "Произошла внутренняя ошибка обработки сообщения")
        except Exception as inner_e:
            _log(f"💥 Не удалось отправить уведомление об ошибке: {inner_e}", chat_id, "ERROR")
            print(f"Не удалось отправить уведомление об ошибке: {inner_e}")

if __name__ == "__main__":
    _log("🚀 === ЗАПУСК БОТА ===", level="SUCCESS")
    _log(f"⚙️ Polling настройки: timeout={POLLING_TIMEOUT}, none_stop={POLLING_NONE_STOP}")
    _log("🤖 Бот готов к получению сообщений...", level="SUCCESS")
    try:
        bot.polling(none_stop=POLLING_NONE_STOP, timeout=POLLING_TIMEOUT)
    except Exception as e:
        _log(f"💥 КРИТИЧЕСКАЯ ОШИБКА polling: {e}", level="ERROR")
        raise
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
                return True
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
                return True
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
                # Выполнить поиск с регистронезависимым сравнением города
                filter_dict = {
                    "city": data.get("city"),
                    "school": data.get("school"),
                    "grade": data.get("class_number"),
                    "role": "ученик"  # Ищем только учеников
                }
                results = database.Manager.search_records_case_insensitive(database.Tables.Users, filter_dict)
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
        results = database.Manager.search_records_case_insensitive(database.Tables.Users, filter_dict)
        
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
        ACTIVE_FLOWS[chat_id] = {
            "type": FLOW_EDIT_PROFILE, 
            "step": "show_profile", 
            "data": {}
        }
        _log("✏️ Запущен процесс редактирования профиля", chat_id, "SUCCESS")
        _show_profile_for_editing(chat_id)
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
• прикрепить класс - найти и прикрепить учеников
• ваши учащиеся - список прикреплённых учеников
• отправить задание - работа с заданиями
• проверить задания - проверка решений
• ai помощник - AI инструменты для учителя
• удалить профиль - удаление аккаунта

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

✅ **Система заявок активна!** Найдите учителей в вашей школе и отправьте заявку.
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

        # 4) Ветвление по роли пользователя
        _log("🎭 Обработка команд по роли пользователя...", chat_id, "DEBUG")
        role = database.find_my_role(chat_id)

        if role == "учитель":
            _log(f"👩‍🏫 Обработка команды учителя: {request}", chat_id, "SUCCESS")
            # Простая, плоская логика для учителя
            if request == "профиль":
                _out(bot, chat_id, "Выберите действие", keyboards.Teacher.profile)
            elif request == "ваши учащиеся":
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
                _out(bot, chat_id, "Функция работы с заданиями в упрощенной версии пока недоступна", keyboards.Student.main)
            elif request == "сгенерировать задание":
                _out(bot, chat_id, "Укажите тему, по которой сгенерировать одно задание (без решения)")
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
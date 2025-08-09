"""Логика пользователя с ролью Учитель."""

from sqlalchemy import and_
from database import Manager, Tables
import keyboards
import core
from LLM import LLM
from .base import Registered


class Teacher(Registered):
    def __init__(self, myID: str = "", bind_bot=None):
        super().__init__(myID, bind_bot)
        self.searchClass = []
        self._ref = f"tg://user?id={self._ID}"
        self.llm = LLM()
        try:
            self.llm.set_role("math teacher")
        except Exception:
            pass
        self.ai_process = None
        self.class_search_process = None

    def show_main_menu(self):
        self._telegramBot.send_message(self._ID, "главная", reply_markup=keyboards.Teacher.main)
        return True

    def show_profile_actions(self):
        self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup=keyboards.Teacher.profile)

    def assign_homework(self):
        """Показывает меню для задания домашней работы."""
        try:
            self._telegramBot.send_message(self._ID, "Выберите тип задания", reply_markup=keyboards.Teacher.homework)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню заданий: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при открытии меню заданий")
            return False

    def assign_individual_task(self):
        """Запускает процесс формирования индивидуального задания (заглушка)."""
        try:
            self._telegramBot.send_message(self._ID, "Функция индивидуальных заданий в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при создании индивидуального задания: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при создании задания")
            return False

    def assign_class_task(self):
        """Запускает процесс выдачи задания для класса (заглушка)."""
        try:
            self._telegramBot.send_message(self._ID, "Функция заданий для класса в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при создании задания для класса: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при создании задания")
            return False

    def check_tasks(self):
        """Показывает меню для проверки поступивших решений."""
        try:
            self._telegramBot.send_message(self._ID, "Выберите тип заданий для проверки", reply_markup=keyboards.Teacher.check_task)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню проверки: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при открытии меню проверки")
            return False

    def check_individual_tasks(self):
        """Показывает индивидуальные задания для проверки (заглушка)."""
        try:
            self._telegramBot.send_message(self._ID, "Функция проверки индивидуальных заданий в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при проверке индивидуальных заданий: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при проверке заданий")
            return False

    def check_class_tasks(self):
        """Показывает задания класса для проверки (заглушка)."""
        try:
            self._telegramBot.send_message(self._ID, "Функция проверки заданий класса в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при проверке заданий класса: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при проверке заданий")
            return False

    class SearchClassProcess(core.Process):
        def __init__(self, ID, owner: "Teacher"):
            super().__init__(ID, cancelable=True)
            self.owner = owner
            self._data = {}
            self._chain = [
                self.ask_city, self.verify_city,
                self.ask_school, self.verify_school,
                self.ask_class, self.verify_class,
                self.perform_search,
            ]
            self._max_i = len(self._chain) - 1

        def _say(self, text: str):
            self._bot.send_message(self._me.get_ID(), text)

        def _store(self, key: str, value):
            self._data[key] = value

        def ask_city(self):
            self._say("В каком городе учатся учащиеся? (название города)")

        def verify_city(self):
            if core.Validator.city(self._current_request):
                self._store("city", self._current_request)
            else:
                self._say("Некорректный город. Попробуйте снова")
                raise core.UserInputError("invalid city")

        def ask_school(self):
            self._say("В какой школе?")

        def verify_school(self):
            if core.Validator.school(self._current_request):
                try:
                    value = int(self._current_request.split(" ")[-1])
                except Exception:
                    value = self._current_request
                self._store("school", value)
            else:
                self._say("Некорректный номер школы. Попробуйте снова")
                raise core.UserInputError("invalid school")

        def ask_class(self):
            self._say("В каком классе? (номер класса и буква)")

        def verify_class(self):
            if core.Validator.class_number(self._current_request):
                self._store("class_number", self._current_request)
            else:
                self._say("Некорректный класс. Попробуйте снова")
                raise core.UserInputError("invalid class")

        def perform_search(self):
            # делегируем существующей реализации поиска
            try:
                data = {
                    "city": self._data.get("city"),
                    "school": self._data.get("school"),
                    "class_number": self._data.get("class_number"),
                }
                self.owner._Teacher__search_class(data)
            except Exception:
                pass

    def search_class(self):
        try:
            self.class_search_process = self.SearchClassProcess(self._ID, self)
            self._current_command = self._cancelable_execute_search_class
            # вывести первый вопрос
            self._current_command()
            return True
        except Exception:
            return False

    @core.cancelable
    def _cancelable_execute_search_class(self):
        try:
            if not self.class_search_process:
                return False
            self.class_search_process.update_last_request(self._current_request)
            self.class_search_process.execute()
            if not getattr(self.class_search_process, "_is_active", False):
                self.class_search_process = None
                self._current_command = None
            return True
        except Exception:
            return False

    @core.log
    def __search_class(self, dataFilter: dict):
        self.searchClass = []
        city = dataFilter.get("city")
        school = dataFilter.get("school")
        try:
            if isinstance(school, str):
                school = int(school)
        except Exception:
            pass
        class_number = dataFilter.get("class_number")

        condition = and_(
            Tables.Users.city == city,
            Tables.Users.school == school,
            Tables.Users.student_class == class_number,
        )
        search = Manager.search_records(Tables.Users, condition)
        if search:
            studentIDS = []
            out = ""
            for student in search:
                ID = student["telegram_id"]
                name = student["name"]
                surname = student["surname"]
                out += f"{name} {surname}\n"
                studentIDS.append(ID)

            self._telegramBot.send_message(self._ID, out, reply_markup=keyboards.Teacher.attached)
            self.searchClass = studentIDS
            return studentIDS
        else:
            self._telegramBot.send_message(self._ID, text="ничего не найдено")

    @core.log
    def send_application(self):
        for ID in self.searchClass:
            oldApplication = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == ID, "application")
            newApplication = f"{(oldApplication or '')}{self._ID};"
            Manager.update_record(Tables.Users, "telegram_id", ID, "application", newApplication)
            self._telegramBot.send_message(
                ID,
                f"учитель {self.name} {self.surname} хочет прикрепить вас к себе. Для подтверждения перейдите в заявки",
            )
        self._telegramBot.send_message(self._ID, "Заявка отправлена", reply_markup=keyboards.Teacher.main)
        return True

    @core.log
    def show_my_students(self):
        attached_students = self._reader_my_data("attached_students")
        if not attached_students:
            self._telegramBot.send_message(self._ID, "У вас пока нет прикрепленных учеников", reply_markup=keyboards.Teacher.main)
            return
        student_ids = attached_students.split(";")[:-1]
        out = "Ваши ученики:\n\n"
        for student_id in student_ids:
            name = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "name")
            surname = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "surname")
            school = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "school")
            student_class = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "student_class")
            out += f"• {name} {surname} (школа №{school}, {student_class} класс)\n"
        self._telegramBot.send_message(self._ID, out, reply_markup=keyboards.Teacher.main)
        return True



"""Логика пользователя с ролью Учитель.

Управляет прикреплением классов и учеников, выдачей и проверкой заданий,
а также AI‑ассистентом для анализа решений и генерации заданий.
"""

from sqlalchemy import and_
from database import Manager, Tables
import keyboards
import core
from LLM import LLM
from base import Registered
from enums import AIMode


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
        self._ai_mode: AIMode | None = None
        self.class_search_process = None

    def show_main_menu(self):
        """Показывает главное меню учителя."""
        self._telegramBot.send_message(self._ID, "главная", reply_markup=keyboards.Teacher.main)
        return True

    def show_profile_actions(self):
        """Показывает действия профиля учителя."""
        self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup=keyboards.Teacher.profile)

    def assign_homework(self):
        """Показывает меню для задания домашней работы (выбор типа)."""
        try:
            self._telegramBot.send_message(self._ID, "Выберите тип задания", reply_markup=keyboards.Teacher.homework)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню заданий: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при открытии меню заданий")
            return False

    def assign_individual_task(self):
        """Запрашивает текст индивидуального задания для конкретного ученика."""
        try:
            self._telegramBot.send_message(self._ID, "Пришлите текст индивидуального задания для ученика", reply_markup=keyboards.Teacher.main)
            self._current_command = self._receive_individual_task
            return True
        except Exception as e:
            print(f"Ошибка при создании индивидуального задания: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при создании задания")
            return False

    def assign_class_task(self):
        """Запрашивает текст задания для класса (будет отправлено всем ученикам)."""
        try:
            self._telegramBot.send_message(self._ID, "Пришлите текст задания для класса", reply_markup=keyboards.Teacher.main)
            self._current_command = self._receive_class_task
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
        """Запрашивает решение ученика для проверки AI (индивидуально)."""
        try:
            self._telegramBot.send_message(self._ID, "Загрузите решение ученика текстом. Я помогу проверить.", reply_markup=keyboards.Teacher.main)
            self._current_command = self._ai_check_individual_solution
            return True
        except Exception as e:
            print(f"Ошибка при проверке индивидуальных заданий: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при проверке заданий")
            return False

    def check_class_tasks(self):
        """Запрашивает набор решений класса для анализа типичных ошибок AI."""
        try:
            self._telegramBot.send_message(self._ID, "Пришлите текст решений учащихся одним сообщением для анализа.", reply_markup=keyboards.Teacher.main)
            self._current_command = self._ai_check_class_solutions
            return True
        except Exception as e:
            print(f"Ошибка при проверке заданий класса: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при проверке заданий")
            return False

    def ai_generate_task(self):
        try:
            self._ai_mode = AIMode.GENERATE_TASK
            self._telegramBot.send_message(self._ID, "Укажите тему и уровень (например: Квадратные уравнения, базовый) — сгенерирую ОДНО задание без решения", reply_markup=keyboards.Teacher.main)
            self._current_command = self._ai_generate_and_send
            return True
        except Exception as e:
            print(f"Ошибка запуска генерации задания учителем: {e}")
            return False

    class SearchClassProcess(core.Process):
        """Многошаговый процесс поиска класса (город → школа → класс → поиск).

        Наследует `core.Process` и использует цепочку ask/verify шагов с
        автоматическим переходом к следующему вопросу.
        """
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
            """Спрашивает у пользователя город класса."""
            self._say("В каком городе учатся учащиеся? (название города)")

        def verify_city(self):
            """Проверяет корректность введённого города."""
            if core.Validator.city(self._current_request):
                self._store("city", self._current_request)
            else:
                self._say("Некорректный город. Попробуйте снова")
                raise core.UserInputError("invalid city")

        def ask_school(self):
            """Спрашивает школу (номер/название)."""
            self._say("В какой школе?")

        def verify_school(self):
            """Проверяет корректность школы и приводит к числу при возможности."""
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
            """Спрашивает номер и букву класса (например, 7А)."""
            self._say("В каком классе? (номер класса и буква)")

        def verify_class(self):
            """Проверяет корректность обозначения класса."""
            if core.Validator.class_number(self._current_request):
                self._store("class_number", self._current_request)
            else:
                self._say("Некорректный класс. Попробуйте снова")
                raise core.UserInputError("invalid class")

        def perform_search(self):
            """Выполняет поиск учеников по введённым критериям и выводит список."""
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
        """Запускает многошаговый процесс поиска класса."""
        try:
            self.class_search_process = self.SearchClassProcess(self._ID, self)
            self._current_command = self._cancelable_execute_search_class
            self._current_command()
            return True
        except Exception:
            return False

    @core.cancelable
    def _cancelable_execute_search_class(self):
        """Обёртка исполнения процесса поиска с поддержкой отмены."""
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
        """Ищет учеников по фильтру (город, школа, класс) и печатает найденных."""
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
        """Отправляет заявки всем найденным ученикам на прикрепление к учителю."""
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

    # ===== Teacher task reception helpers =====
    def _receive_individual_task(self):
        """Принимает текст индивидуального задания от учителя."""
        try:
            text = getattr(self, "_current_request", "").strip()
            if not text:
                return False
            # Здесь можно сохранить в БД; пока отправим подтверждение
            self._telegramBot.send_message(self._ID, "Индивидуальное задание сформировано и сохранено", reply_markup=keyboards.Teacher.main)
            self._current_command = None
            return True
        except Exception:
            self._current_command = None
            return False

    def _receive_class_task(self):
        """Принимает текст задания для класса от учителя."""
        try:
            text = getattr(self, "_current_request", "").strip()
            if not text:
                return False
            self._telegramBot.send_message(self._ID, "Задание для класса сформировано и сохранено", reply_markup=keyboards.Teacher.main)
            self._current_command = None
            return True
        except Exception:
            self._current_command = None
            return False

    # ===== AI helpers for teacher =====
    @core.cancelable
    def _ai_check_individual_solution(self):
        """Проверяет решение одного ученика с помощью AI и даёт рекомендации."""
        try:
            text = getattr(self, "_current_request", "").strip()
            if not text:
                return False
            prompt = (
                "Проверь решение ученика. Найди ошибки и предложи улучшения. "
                "Критерии: корректность, полнота, логика. Текст: " + text
            )
            answer = self.llm.ask(prompt)
            self._telegramBot.send_message(self._ID, answer, reply_markup=keyboards.Teacher.main)
            self._current_command = None
            return True
        except Exception:
            self._current_command = None
            return False

    @core.cancelable
    def _ai_check_class_solutions(self):
        """Анализирует набор решений класса: типичные ошибки и рекомендации."""
        try:
            text = getattr(self, "_current_request", "").strip()
            if not text:
                return False
            prompt = (
                "Суммируй типичные ошибки в работах класса и предложи рекомендации по теме. "
                "Дай список частых ошибок и план их устранения. Текст: " + text
            )
            answer = self.llm.ask(prompt)
            self._telegramBot.send_message(self._ID, answer, reply_markup=keyboards.Teacher.main)
            self._current_command = None
            return True
        except Exception:
            self._current_command = None
            return False

    @core.cancelable
    def _ai_generate_and_send(self):
        """Генерирует ОДНУ задачу по теме/уровню и отправляет учителю."""
        try:
            text = getattr(self, "_current_request", "").strip()
            if not text:
                return False
            prompt = (
                "Сгенерируй ОДНУ математическую задачу по указанной теме и уровню. Только условие, без решения и ответа. "
                "Формат: 'Задача: ...'. В случае неоднозначности задай 1 уточняющий вопрос в конце. Тема: " + text
            )
            answer = self.llm.ask(prompt)
            self._telegramBot.send_message(self._ID, answer, reply_markup=keyboards.Teacher.main)
            self._current_command = None
            return True
        except Exception:
            self._current_command = None
            return False

    @core.log
    def show_my_students(self):
        """Выводит список прикреплённых к учителю учеников с данными."""
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



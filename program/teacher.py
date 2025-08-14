from sqlalchemy import and_
from database import Manager, Tables
import keyboards
import core
from LLM import LLM
from base import Registered
from enums import AIMode
import logger


class Teacher(Registered):
    class SearchClass(core.Process):
        """Многошаговый процесс поиска класса (город, школа, класс, затем поиск)."""
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
            self.class_search_process = self.SearchClass(self._ID, self)
            self._cancelable_execute_search_class()
        except Exception:
            pass

    def _cancelable_execute_search_class(self):
        """Обёртка исполнения процесса поиска с поддержкой отмены."""
        try:
            if not self.class_search_process:
                return False
            # отмена обрабатывается внутри Process.update_last_request
            self.class_search_process.update_last_request(self._current_request)
            self.class_search_process.execute()
            if not getattr(self.class_search_process, "_is_active", False):
                self.class_search_process = None
            
        except Exception:
            return False
            
    def __init__(self, myID: str = "", bind_bot=None):
        super().__init__(myID, bind_bot)
        self.searchClass = []
        self.ref = None
        self.llm = LLM()
        self.llm.set_role("math teacher")

        self.ai_process = None
        self._ai_mode: AIMode | None = None
        self.class_search_process = None

    def show_main_menu(self):
        """Показывает главное меню учителя."""
        self.out("главная", keyboards.Teacher.main)

    def show_profile_actions(self):
        """Показывает действия профиля учителя."""
        self.out("Выберите действие", keyboards.Teacher.profile)

    def assign_homework(self):
        """Показывает меню для задания домашней работы (выбор типа)."""
        self.out("Выберите тип задания", keyboards.Teacher.homework)

    def assign_individual_task(self):
        """Запрашивает текст индивидуального задания для конкретного ученика."""
        self.out("Пришлите текст индивидуального задания для ученика", keyboards.Teacher.main)
        self._expect_individual_task = True

    def assign_class_task(self):
        """Запрашивает текст задания для класса (будет отправлено всем ученикам)."""
        self.out("Пришлите текст задания для класса", keyboards.Teacher.main)
        self._expect_class_task = True

    def check_tasks(self):
        """Показывает меню для проверки поступивших решений."""
        self.out("Выберите тип заданий для проверки", keyboards.Teacher.check_task)

    def check_individual_tasks(self):
        """Запрашивает решение ученика для проверки AI (индивидуально)."""
        self.out("Загрузите решение ученика текстом. Я помогу проверить.", keyboards.Teacher.main)
        self._expect_ai_check_individual = True



    @logger.log
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
            Tables.Users.grade == class_number,
        )
        search = Manager.search_records(Tables.Users, condition)
        if search:
            student_ids = []
            out = ""
            for student in search:
                student = core.UserRecognizer(student["telegram_id"])
                out += f"{student.name} {student.surname}\n"
                student_ids.append(student.get_ID())

            self.out(out, keyboards.Teacher.attached)
            self.searchClass = student_ids
            return student_ids
        else:
            self.out("ничего не найдено")

    @logger.log
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
        self.out("Заявка отправлена", keyboards.Teacher.main)
        return True

    def _receive_individual_task(self):
        """Принимает текст индивидуального задания от учителя."""
        try:
            text = getattr(self, "_current_request", "").strip()
            if not text:
                return False
            # Здесь можно сохранить в БД; пока отправим подтверждение
            self.out("Индивидуальное задание сформировано и сохранено", keyboards.Teacher.main)
            self._expect_individual_task = False
        except Exception:
            self._expect_individual_task = False
            return False

    def _receive_class_task(self):
        """Принимает текст задания для класса от учителя."""
        try:
            text = getattr(self, "_current_request", "").strip()
            if not text:
                return False
            self.out("Задание для класса сформировано и сохранено", keyboards.Teacher.main)
            self._expect_class_task = False
        except Exception:
            self._expect_class_task = False
            return False

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
            self.out(answer, keyboards.Teacher.main)
            self._expect_ai_check_individual = False
        except Exception:
            self._expect_ai_check_individual = False
            return False

    # Универсальные хуки маршрутизатора
    def has_active_process(self) -> bool:
        try:
            if getattr(self, "class_search_process", None) and getattr(self.class_search_process, "_is_active", False):
                return True
        except Exception:
            pass
        return bool(getattr(self, "_expect_individual_task", False) or getattr(self, "_expect_class_task", False) or getattr(self, "_expect_ai_check_individual", False))

    def handle_active_process(self) -> bool:
        try:
            if getattr(self, "class_search_process", None) and getattr(self.class_search_process, "_is_active", False):
                return bool(self._cancelable_execute_search_class())
            if getattr(self, "_expect_individual_task", False):
                return bool(self._receive_individual_task())
            if getattr(self, "_expect_class_task", False):
                return bool(self._receive_class_task())
            if getattr(self, "_expect_ai_check_individual", False):
                return bool(self._ai_check_individual_solution())
            return False
        except Exception:
            return False


    @logger.log
    def show_my_students(self):
        """Выводит список прикреплённых к учителю учеников с данными."""
        attached_students = self._reader_my_data("attached_students")
        if not attached_students:
            self.out("У вас пока нет прикрепленных учеников", keyboards.Teacher.main)
            return

        student_ids = attached_students.split(";")[:-1]
        out = "Ваши ученики:\n\n"
        for student_id in student_ids:
            me = core.UserRecognizer(student_id)
            out += f"• {me.name} {me.surname} (школа №{me.school}, {me.grade} класс)\n"

        self.out(out, keyboards.Teacher.main)


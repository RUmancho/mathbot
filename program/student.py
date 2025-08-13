"""Логика пользователя с ролью Ученик.

Отвечает за взаимодействия в меню ученика, работу AI‑помощника для
объяснений, практики, проверки решений, а также генерацию задания.
"""

from database import Manager, Tables
import keyboards
from LLM import LLM
from base import Registered
import core
from enums import AIMode


class Student(Registered):
    def __init__(self, myID: str = "", bind_bot=None):
        super().__init__(myID, bind_bot)
        self.llm = LLM()
        try:
            self.llm.set_role("math teacher")
        except Exception:
            pass
        self.ai_process = None
        self._ai_mode: AIMode | None = None  # режим работы AI помощника

    def show_main_menu(self):
        """Показывает главное меню ученика."""
        self._telegramBot.send_message(self._ID, "главная", reply_markup=keyboards.Student.main)
        return True

    def recognize_user(self):
        """Загружает профиль ученика (город, школа, класс)."""
        super().recognize_user()
        self.city = self._reader_my_data("city")
        self.school = self._reader_my_data("school")
        self.class_ = self._reader_my_data("student_class")

    def show_applications(self):
        """Выводит список входящих заявок от учителей."""
        teachersIDS = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "application")
        if not teachersIDS:
            self._telegramBot.send_message(self._ID, "Заявок нет", reply_markup=keyboards.Student.main)
            return
        teachersIDS = teachersIDS.split(";")[:-1]
        name_surname_ref_teacher = []
        for ID in teachersIDS:
            data_filter = lambda column: Manager.get_cell(Tables.Users, Tables.Users.telegram_id == ID, column)
            name = data_filter("name")
            surname = data_filter("surname")
            ref = data_filter("ref")
            name_surname_ref_teacher.append([f"{name} {surname}, {ref}"])
        keyboard = keyboards.create_keyboard(*name_surname_ref_teacher)
        self._telegramBot.send_message(self._ID, "Выберите учителя", reply_markup=keyboard)
        return True

    def show_profile_actions(self):
        """Показывает действия профиля (удаление/редактирование)."""
        self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup=keyboards.Student.profile)

    def show_my_teachers(self):
        """Показывает прикреплённых к ученику учителей."""
        my_teachers = self._reader_my_data("my_teachers")
        if not my_teachers:
            self._telegramBot.send_message(self._ID, "У вас пока нет прикрепленных учителей", reply_markup=keyboards.Student.main)
            return
        teacher_ids = my_teachers.split(";")[:-1]
        out = "Ваши учителя:\n\n"
        for teacher_id in teacher_ids:
            name = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == teacher_id, "name")
            surname = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == teacher_id, "surname")
            out += f"• {name} {surname}\n"
        self._telegramBot.send_message(self._ID, out, reply_markup=keyboards.Student.main)
        return True

    def show_tasks(self):
        """Показывает меню работы с заданиями ученика."""
        self._telegramBot.send_message(self._ID, "Выберите действие с заданиями", reply_markup=keyboards.Student.task)
        return True

    def get_tasks(self):
        """Заглушка: получение заданий (можно расширить сохранением в БД)."""
        self._telegramBot.send_message(self._ID, "Функция получения заданий в разработке", reply_markup=keyboards.Student.main)
        return True

    def submit_solution(self):
        """Заглушка: отправка решения на проверку (можно связать с БД)."""
        self._telegramBot.send_message(self._ID, "Функция отправки решений в разработке", reply_markup=keyboards.Student.main)
        return True

    # ====== AI Helper (Student) ======
    def show_ai_helper_menu(self):
        """Открывает раздел AI‑помощника для ученика."""
        try:
            self._telegramBot.send_message(self._ID, "Раздел AI Помощник", reply_markup=keyboards.Student.ai_helper)
            self._current_command = None
            return True
        except Exception as e:
            print(f"Ошибка показа меню AI помощника студента: {e}")
            return False

    def ai_help_with_problem(self):
        """Включает режим решения одной задачи с пошаговым объяснением."""
        try:
            self._ai_mode = AIMode.HELP_PROBLEM
            self._telegramBot.send_message(self._ID, "Пришлите условие задачи одним сообщением")
            self._current_command = self._ai_receive_and_answer
            return True
        except Exception as e:
            print(f"Ошибка запуска режима помощи с задачей: {e}")
            return False

    def ai_explain_theory(self):
        """Включает режим объяснения теории по указанной теме."""
        try:
            self._ai_mode = AIMode.EXPLAIN
            self._telegramBot.send_message(self._ID, "Какую тему объяснить?")
            self._current_command = self._ai_receive_and_answer
            return True
        except Exception as e:
            print(f"Ошибка запуска объяснения теории: {e}")
            return False

    def ai_tips(self):
        """Просит AI дать практические советы по теме."""
        try:
            self._ai_mode = AIMode.TIPS
            self._telegramBot.send_message(self._ID, "По какой теме дать советы?")
            self._current_command = self._ai_receive_and_answer
            return True
        except Exception as e:
            print(f"Ошибка запуска советов AI: {e}")
            return False

    def ai_study_plan(self):
        """Просит AI составить краткий план обучения по теме и сроку."""
        try:
            self._ai_mode = AIMode.PLAN
            self._telegramBot.send_message(self._ID, "Укажите тему и срок (например: Квадратные уравнения за 2 недели)")
            self._current_command = self._ai_receive_and_answer
            return True
        except Exception as e:
            print(f"Ошибка запуска планирования обучения: {e}")
            return False

    def ai_check_solution(self):
        """Просит AI проанализировать решение задачи и указать ошибки."""
        try:
            self._ai_mode = AIMode.CHECK_SOLUTION
            self._telegramBot.send_message(self._ID, "Пришлите условие задачи и ваше решение одним сообщением")
            self._current_command = self._ai_receive_and_answer
            return True
        except Exception as e:
            print(f"Ошибка запуска проверки решения: {e}")
            return False

    def ai_practice(self):
        """Запрашивает у AI набор тренировочных задач по теме (с ответами)."""
        try:
            self._ai_mode = AIMode.PRACTICE
            self._telegramBot.send_message(self._ID, "Укажите тему, по которой нужны тренировки")
            self._current_command = self._ai_receive_and_answer
            return True
        except Exception as e:
            print(f"Ошибка запуска практики: {e}")
            return False

    def ai_generate_task(self):
        """Генерирует ОДНУ задачу по теме без решения и ответа."""
        try:
            self._ai_mode = AIMode.GENERATE_TASK
            self._telegramBot.send_message(self._ID, "Укажите тему, по которой сгенерировать одно задание (без решения)")
            self._current_command = self._ai_receive_and_answer
            return True
        except Exception as e:
            print(f"Ошибка запуска генерации задания: {e}")
            return False

    @staticmethod
    def _build_prompt(mode: AIMode | None, text: str) -> str:
        """Создаёт промпт к LLM на основе выбранного режима AI.

        Для более сложных режимов включает структуру и формат ожидаемого вывода.
        """
        try:
            if mode == AIMode.HELP_PROBLEM:
                return f"Реши пошагово задачу, объясняя ход решения на русском языке: {text}"
            if mode == AIMode.EXPLAIN:
                return f"Подробно объясни тему на русском языке с примерами: {text}"
            if mode == AIMode.TIPS:
                return f"Дай краткие практические советы по теме: {text}"
            if mode == AIMode.PLAN:
                return f"Составь краткий, понятный план обучения по теме с разбивкой по дням/неделям: {text}"
            if mode == AIMode.CHECK_SOLUTION:
                return (
                    "Проанализируй решение задачи. Укажи ошибки, если есть, и покажи корректное решение. "
                    f"Текст: {text}"
                )
            if mode == AIMode.PRACTICE:
                return (
                    "Сгенерируй 5 практических задач по теме с ответами в конце. Формат: Задача 1, ... Ответы:. "
                    f"Тема: {text}"
                )
            if mode == AIMode.GENERATE_TASK:
                return (
                    "Сгенерируй ОДНУ математическую задачу по теме с четкой формулировкой. "
                    "Только условие без решения и без ответа. Формат: 'Задача: ...'. "
                    f"Тема: {text}"
                )
            return text
        except Exception as e:
            print(f"Ошибка формирования промпта AI: {e}")
            return text

    @core.cancelable
    def _ai_receive_and_answer(self):
        """Получает ввод пользователя, отправляет промпт LLM и возвращает ответ.

        Оборачивается декоратором cancelable: слово «отмена» корректно завершает
        текущий режим и очищает состояние.
        """
        try:
            user_text = getattr(self, "_current_request", "").strip()
            if not user_text:
                return False
            prompt = self._build_prompt(self._ai_mode, user_text)
            answer = self.llm.ask(prompt)
            self._telegramBot.send_message(self._ID, answer, reply_markup=keyboards.Student.ai_helper)
            # Завершаем режим
            self._ai_mode = None
            self._current_command = None
            return True
        except Exception as e:
            print(f"Ошибка ответа AI помощника студента: {e}")
            try:
                self._telegramBot.send_message(self._ID, "Произошла ошибка при обработке запроса AI")
            except Exception:
                pass
            self._ai_mode = None
            self._current_command = None
            return False



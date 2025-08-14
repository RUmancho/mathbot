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
        self.out("главная", keyboards.Student.main)
        

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
            self.out("Заявок нет", keyboards.Student.main)
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
        self.out("Выберите учителя", keyboard)
        

    def show_profile_actions(self):
        """Показывает действия профиля (удаление/редактирование)."""
        self.out("Выберите действие", keyboards.Student.profile)

    def show_my_teachers(self):
        """Показывает прикреплённых к ученику учителей."""
        my_teachers = self._reader_my_data("my_teachers")
        if not my_teachers:
            self.out("У вас пока нет прикрепленных учителей", keyboards.Student.main)
            return
        teacher_ids = my_teachers.split(";")[:-1]
        out = "Ваши учителя:\n\n"
        for teacher_id in teacher_ids:
            name = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == teacher_id, "name")
            surname = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == teacher_id, "surname")
            out += f"• {name} {surname}\n"

        self.out(out, keyboards.Student.main)
        

    def show_tasks(self):
        """Показывает меню работы с заданиями ученика."""
        self.out("Выберите действие с заданиями", keyboards.Student.task)
        

    def get_tasks(self):
        """Заглушка: получение заданий (можно расширить сохранением в БД)."""
        self.out("Функция получения заданий в разработке", keyboards.Student.main)
        

    def submit_solution(self):
        """Заглушка: отправка решения на проверку (можно связать с БД)."""
        self.out("Функция отправки решений в разработке", keyboards.Student.main)
        

    def show_ai_helper_menu(self):
        """Открывает раздел AI‑помощника для ученика."""
        try:
            self.out("Раздел AI Помощник", keyboards.Student.ai_helper)
            self._current_command = None
            
        except Exception as e:
            print(f"Ошибка показа меню AI помощника студента: {e}")
            

    def ai_help_with_problem(self):
        """Включает режим решения одной задачи с пошаговым объяснением."""
        try:
            self._ai_mode = AIMode.HELP_PROBLEM
            self.out("Пришлите условие задачи одним сообщением")
            self._current_command = self._ai_receive_and_answer
            
        except Exception as e:
            print(f"Ошибка запуска режима помощи с задачей: {e}")
            

    def ai_explain_theory(self):
        """Включает режим объяснения теории по указанной теме."""
        try:
            self._ai_mode = AIMode.EXPLAIN
            self.out("Какую тему объяснить?")
            self._current_command = self._ai_receive_and_answer
            
        except Exception as e:
            print(f"Ошибка запуска объяснения теории: {e}")
            

    def ai_tips(self):
        """Просит AI дать практические советы по теме."""
        try:
            self._ai_mode = AIMode.TIPS
            self.out("По какой теме дать советы?")
            self._current_command = self._ai_receive_and_answer
            return True
        except Exception as e:
            print(f"Ошибка запуска советов AI: {e}")
            return False

    def ai_practice(self):
        """Запрашивает у AI набор тренировочных задач по теме (с ответами)."""
        try:
            self._ai_mode = AIMode.PRACTICE
            self._telegramBot.send_message(self._ID, "Укажите тему, по которой нужны тренировки")
            self._current_command = self._ai_receive_and_answer
            
        except Exception as e:
            print(f"Ошибка запуска практики: {e}")
            

    def ai_generate_task(self):
        """Генерирует ОДНУ задачу по теме без решения и ответа."""
        try:
            self._ai_mode = AIMode.GENERATE_TASK
            self.out("Укажите тему, по которой сгенерировать одно задание (без решения)")
            self._current_command = self._ai_receive_and_answer
            
        except Exception as e:
            print(f"Ошибка запуска генерации задания: {e}")
            

    

    @core.cancelable
    def _ai_receive_and_answer(self):
        """Получает ввод пользователя, отправляет промпт LLM и возвращает ответ.

        Оборачивается декоратором cancelable: слово «отмена» корректно завершает
        текущий режим и очищает состояние.
        """
        try:
            user_text = getattr(self, "_current_request", "").strip()
            if not user_text:
                return
            answer = self.llm.respond(self._ai_mode, user_text)
            self.out(answer, keyboards.Student.ai_helper)
            # Завершаем режим
            self._ai_mode = None
            self._current_command = None
            
        except Exception as e:
            print(f"Ошибка ответа AI помощника студента: {e}")
            try:
                self.out("Произошла ошибка при обработке запроса AI")
            except Exception:
                pass
            self._ai_mode = None
            self._current_command = None
            

    
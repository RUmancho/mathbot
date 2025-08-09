"""Логика пользователя с ролью Ученик."""

from database import Manager, Tables
import keyboards
from LLM import LLM
from base import Registered


class Student(Registered):
    def __init__(self, myID: str = "", bind_bot=None):
        super().__init__(myID, bind_bot)
        self.llm = LLM()
        try:
            self.llm.set_role("math teacher")
        except Exception:
            pass
        self.ai_process = None

    def show_main_menu(self):
        self._telegramBot.send_message(self._ID, "главная", reply_markup=keyboards.Student.main)
        return True

    def recognize_user(self):
        super().recognize_user()
        self.city = self._reader_my_data("city")
        self.school = self._reader_my_data("school")
        self.class_ = self._reader_my_data("student_class")

    def show_applications(self):
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
        self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup=keyboards.Student.profile)

    def show_my_teachers(self):
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
        self._telegramBot.send_message(self._ID, "Выберите действие с заданиями", reply_markup=keyboards.Student.task)
        return True

    def get_tasks(self):
        self._telegramBot.send_message(self._ID, "Функция получения заданий в разработке", reply_markup=keyboards.Student.main)
        return True

    def submit_solution(self):
        self._telegramBot.send_message(self._ID, "Функция отправки решений в разработке", reply_markup=keyboards.Student.main)
        return True



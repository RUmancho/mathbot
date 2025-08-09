"""Логика пользователя с ролью Учитель."""

from sqlalchemy import and_
from database import Manager, Tables
import keyboards
import buttons as btn
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

    def show_main_menu(self):
        self._telegramBot.send_message(self._ID, "главная", reply_markup=keyboards.Teacher.main)
        return True

    def show_profile_actions(self):
        self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup=keyboards.Teacher.profile)

    def search_class(self):
        self.searchClass = btn.Teacher.search_class()
        self.searchClass.set_ID(self._ID)
        self.searchClass.run()

        @core.cancelable
        def _cancelable_execute_search_class():
            if not self.searchClass:
                return False
            if self._current_request:
                self.searchClass.request(self._current_request)
                self.searchClass.run()
            if getattr(self.searchClass, "registration_finished", False):
                data = self.searchClass.collection()
                if data:
                    self.__search_class(data)
                self._current_command = None
            return True

        self._current_command = _cancelable_execute_search_class
        return True

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



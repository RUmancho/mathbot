import database
import config
import keyboards
import core
from base import User


class Guest(User):
    START_MESSAGE = "Здравствуйте, этот бот даст теорию по математике, для его полного использования нужно зарегестрироваться"

    def __init__(self, myID: str = "", bind_bot=None):
        super().__init__(myID, bind_bot)
        self.current_registration = None
        self.reg_process = None
        self.in_registration = False

    class _BaseRegistration(core.Process):
        def __init__(self, ID):
            super().__init__(ID, cancelable=True)
            self._data: dict = {}
            self.completed: bool = False

        def _store(self, key: str, value):
            self._data[key] = value

    class TeacherRegistration(_BaseRegistration):
        def __init__(self, ID):
            super().__init__(ID)
            self._chain = [
                self.ask_name, self.verify_name,
                self.ask_surname, self.verify_surname,
                self.ask_password, self.verify_password,
            ]
            self._max_i = len(self._chain) - 1

        def ask_name(self):
            self.out("Введите ваше настоящее имя")

        def verify_name(self):
            if core.Validator.name(self._current_request):
                self._store("name", self._current_request)
            else:
                self.out("Некорректное имя. Попробуйте снова")
                raise core.UserInputError("invalid name")

        def ask_surname(self):
            self.out("Введите вашу настоящую фамилию")

        def verify_surname(self):
            if core.Validator.surname(self._current_request):
                self._store("surname", self._current_request)
            else:
                self.out("Некорректная фамилия. Попробуйте снова")
                raise core.UserInputError("invalid surname")

        def ask_password(self):
            self.out(f"Придумайте пароль, содержащий {config.PASSWORD_LENGTH} цифры")

        def verify_password(self):
            if core.Validator.create_password(self._current_request):
                self._store("password", self._current_request)
                record = database.Tables.Users(
                    telegram_id=self._info.get_ID(),
                    role="учитель",
                    name=self._data.get("name"),
                    surname=self._data.get("surname"),
                    password=self._data.get("password"),
                    username=self._bot.get_chat(self._info.get_ID())
                )
                if database.Manager.write(record):
                    self.out("Вы зарегистрированы как учитель")
                    self.completed = True
                else:
                    self.out("Не удалось сохранить профиль. Попробуйте позже")
            else:
                self.out("Некорректный пароль. Попробуйте снова")
                raise core.UserInputError("invalid password")

    class StudentRegistration(_BaseRegistration):
        def __init__(self, ID):
            super().__init__(ID)
            self._chain = [
                self.ask_name, self.verify_name,
                self.ask_surname, self.verify_surname,
                self.ask_password, self.verify_password,
                self.ask_city, self.verify_city,
                self.ask_school, self.verify_school,
                self.ask_class, self.verify_class,
            ]
            self._max_i = len(self._chain) - 1

        def ask_name(self):
            self.out("Введите ваше настоящее имя")

        def verify_name(self):
            if core.Validator.name(self._current_request):
                self._store("name", self._current_request)
            else:
                self.out("Некорректное имя. Попробуйте снова")
                raise core.UserInputError("invalid name")

        def ask_surname(self):
            self.out("Введите вашу настоящую фамилию")

        def verify_surname(self):
            if core.Validator.surname(self._current_request):
                self._store("surname", self._current_request)
            else:
                self.out("Некорректная фамилия. Попробуйте снова")
                raise core.UserInputError("invalid surname")

        def ask_password(self):
            self.out(f"Придумайте пароль, содержащий {config.PASSWORD_LENGTH} цифры")

        def verify_password(self):
            if core.Validator.create_password(self._current_request):
                self._store("password", self._current_request)
            else:
                self.out("Некорректный пароль. Попробуйте снова")
                raise core.UserInputError("invalid password")

        def ask_city(self):
            self.out("В каком городе вы учитесь?")

        def verify_city(self):
            if core.Validator.city(self._current_request):
                self._store("city", self._current_request)
            else:
                self.out("Некорректный город. Попробуйте снова")
                raise core.UserInputError("invalid city")

        def ask_school(self):
            self.out("В какой школе вы учитесь?")

        def verify_school(self):
            if core.Validator.school(self._current_request):
                self._store("school", int(self._current_request.split(" ")[-1]))
            else:
                self.out("Некорректный номер школы. Попробуйте снова")
                raise core.UserInputError("invalid school")

        def ask_class(self):
            self.out("В каком классе вы учитесь? (например, 9а)")

        def verify_class(self):
            if core.Validator.class_number(self._current_request):
                self._store("student_class", self._current_request)
                record = database.Tables.Users(
                    telegram_id=self._info.get_ID(),
                    username=self._bot.get_chat(self._info.get_ID()),
                    role="ученик",
                    name=self._data.get("name"),
                    surname=self._data.get("surname"),
                    password=self._data.get("password"),
                    city=self._data.get("city"),
                    school=self._data.get("school"),
                    grade=self._data.get("student_class"),
                )
                if database.Manager.write(record):
                    self.out("Вы зарегистрированы как ученик")
                    self.completed = True
                else:
                    self.out("Не удалось сохранить профиль. Попробуйте позже")
            else:
                self.out("Некорректное значение класса. Попробуйте снова")
                raise core.UserInputError("invalid class")

    def teacher_registration(self):
        self.reg_process = self.TeacherRegistration(self._ID)
        self.in_registration = True
        self._current_command = self._cancelable_registration_execute
        return True

    def student_registration(self):
        self.reg_process = self.StudentRegistration(self._ID)
        self.in_registration = True
        self._current_command = self._cancelable_registration_execute
        return True

    def cancel_current_action(self):
        try:
            if self.reg_process:
                self.reg_process.stop()
            self.reg_process = None
            self.in_registration = False
        except Exception:
            pass


    def _cancelable_registration_execute(self):
        try:
            if not self.reg_process:
                return False
            # процесс сам обработает отмену в update_last_request (core.Process)
            self.reg_process.update_last_request(self._current_request)
            self.reg_process.execute()
            if not getattr(self.reg_process, "_is_active", False):
                self.reg_process = None
                self.in_registration = False
                self._current_command = None
            return True
        except Exception:
            return False

    def getting_started(self):
        self.out(self.START_MESSAGE, keyboards.Guest.main)
        # Сброс команды, чтобы приветствие не повторялось при каждом сообщении
        self._current_command = None
        return True

    def show_main_menu(self):
        self.out("главное меню", keyboards.Guest.main)
        # Сброс команды после показа меню
        self._current_command = None
        return True


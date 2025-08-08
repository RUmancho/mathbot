"""Модуль с моделями пользователей бота (гость, ученик, учитель).

Содержит классы высокого уровня, инкапсулирующие логику работы с
ботом в зависимости от роли пользователя, а также общую обвязку
для выполнения многошаговых процессов (регистрация, поиск класса,
удаление профиля и др.). Документация приведена на русском языке.
"""

from database import Manager, Tables
from core import Button
from sqlalchemy import and_
import buttons as btn
import keyboards
import core
from LLM import LLM

def find_my_role(ID):
    return Manager.get_cell(Tables.Users, Tables.Users.telegram_id == ID, "role")

class User:
    """Агрегатор активного пользователя.

    Отвечает за хранение ID/бота, делегирование текущего запроса и
    выполнение команд конкретной реализации роли (`Unregistered`, `Student`, `Teacher`).
    """
    RUN_BOT_COMMADS = ["/start"]
    SHOW_MAIN_MENU = ["/меню", "/главная", "/menu", "/main", "/home"]

    def __init__(self, ID, bind_bot = None):
        print("создание пользователя")
        self.info = core.UserRecognizer(ID) 
        self._ID = ID
        self._telegramBot = bind_bot
        self._current_request = None
        self._current_command = None
        self._role_changed = False
        # active role-specific instance (Teacher/Student/Unregistered)
        self.instance = None


    def set_role(self, user_class, ID):
        """Создаёт/переиспользует экземпляр роли и помечает смену роли.

        Возвращает активный экземпляр роли для дальнейшей работы.
        """
        if not isinstance(self.instance, user_class) or self.instance.get_ID() != ID:
            self.instance = user_class(ID, self._telegramBot)
            self._role_changed = True
        else:
            # keep same instance; just ensure bot and id are up-to-date
            self.instance._telegramBot = self._telegramBot
            self.instance.set_ID(ID)
            self._role_changed = False
        return self.instance

    def get_user(self):
        """Возвращает текущий экземпляр активной роли пользователя."""
        return self.instance

    def reset_role_change_flag(self):
        """Сбрасывает флаг смены роли для текущего сообщения."""
        self._role_changed = False


    def get_ID(self) -> str:
        return self._ID

    def set_ID(self, ID):
        if type(ID) != str:
            raise TypeError("ID is not str")
        self._ID = ID

    def unsupported_command_warning(self):
        self.text_out("Неизвестная команда")

    def text_out(self, text: str, markup = None):
        self._telegramBot.send_message(self._ID, text = text, reply_markup=markup)

    def update_last_request(self, request):
        """Сохраняет последний текстовый запрос и делегирует его активной роли."""
        self._current_request = request
        # делегирование активной роли (если поддерживается)
        try:
            self.instance.update_last_request(request)
        except Exception:
            pass

    def command_executor(self):
        """Вызывает исполнение команды для активной роли.

        Если роль переопределяет `command_executor`, будет вызван он,
        иначе — напрямую будет выполнена функция из `_current_command` роли.
        """
        instance_exec = getattr(self.instance.__class__, "command_executor", None)
        base_exec = getattr(User, "command_executor")

        # If the subclass overrides command_executor (e.g., Unregistered), call it
        if callable(instance_exec) and instance_exec is not base_exec:
            return self.instance.command_executor()

        # Otherwise, directly execute the instance's current command
        func = getattr(self.instance, "_current_command", None)
        if callable(func):
            return func()

    # Provide a unified current_command property for role instances
    @property
    def current_command(self):
        return self._current_command

    @current_command.setter
    def current_command(self, func):
        self._current_command = func



class Registered(User):
    """Базовый класс для зарегистрированных пользователей.

    Содержит общие вспомогательные методы и процесс удаления профиля.
    """
    class DeleteProfile(core.Process):
        """Многошаговый процесс удаления профиля с подтверждением паролем."""
        def __init__(self, ID, cancelable = True):
            super().__init__(ID, cancelable)
            self._chain = [self.ask_for_password, self.password_entry_verification]

        def ask_for_password(self):
            """Запрашивает пароль у пользователя."""
            self._bot.send_message(self._me.get_ID(), "Введите ваш пароль для удаления профиля")

        def password_entry_verification(self):
            """Проверяет введённый пароль и удаляет профиль при успехе."""
            if self._current_request == self._me.password:
                self._successful_profile_deletion_message()
                self._delete_account()
            else:
                self._password_entry_error_message()
                raise core.UserInputError("password entry error")

        def _delete_account(self):
            """Удаляет запись пользователя из базы данных."""
            Manager.delete_record(Tables.Users, "telegram_id", self._me.get_ID())

        def _password_entry_error_message(self):
            """Сообщает о неверном пароле."""
            self._bot.send_message(self._me.get_ID(), "Неверный пароль, повторите попытку")
        
        def _successful_profile_deletion_message(self):
            """Сообщает об успешном удалении профиля."""
            self._bot.send_message(self._me.get_ID(), "Профиль удалён")

            
    def __init__(self, ID: str = "", telegramBot = None):
        super().__init__(ID, telegramBot)
        # common user fields
        self.name = None
        self.surname = None
        self.password = None
        self.role = None
        self.recognize_user()
        # save deep-link reference for convenience
        try:
            Manager.update_record(Tables.Users, "telegram_id", self._ID, "ref", f"tg://user?id={self._ID}")
        except Exception:
            pass

        self.delete_profile_process = self.DeleteProfile(ID)

    def delete_account(self):
        """Запускает процесс удаления профиля."""
        self._current_command = self.delete_profile_process.execute

    # helpers for subclasses
    def recognize_user(self):
        """Обновляет базовые поля профиля из базы данных."""
        self.name = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "name")
        self.surname = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "surname")
        self.password = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "password")
        self.role = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "role")

    def _reader_my_data(self, column: str):
        """Возвращает значение столбца `column` из записи текущего пользователя."""
        return Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, column)


 
    


class Teacher(Registered):
    """Реализация логики для роли Учитель."""
    def __init__(self, myID: str = "", bind_bot = None):
        super().__init__(myID, bind_bot)
        self.searchClass = []
        self._ref = f"tg://user?id={self._ID}"
        self.llm = LLM()  # Инициализация LLM для учителя
        # Button instance will be prepared on demand in search_class
    
    def search_class(self):
        """Начинает многошаговый процесс поиска класса по городу/школе/классу."""
        self.searchClass = btn.Teacher.search_class()
        self.searchClass.set_ID(self._ID)
        self.searchClass.run()
        # bind executor to process subsequent inputs until completion
        self._current_command = self._execute_search_class
        return True

    def _execute_search_class(self):
        """Передаёт ввод пользователя в форму и выполняет поиск после завершения ввода."""
        try:
            if not self.searchClass:
                return False
            if self._current_request:
                self.searchClass.request(self._current_request)
                self.searchClass.run()
            if getattr(self.searchClass, "registration_finished", False):
                data = self.searchClass.collection()
                if data:
                    self.__search_class(data)
                # clear command after finishing
                self._current_command = None
            return True
        except Exception:
            return False

    @core.log
    def __search_class(self, dataFilter: dict): 
        """Выполняет поиск учеников по указанным фильтрам и выводит список найденных."""
        self.searchClass = []
        try:
            city = dataFilter["city"]
            school = int(dataFilter["school"]) if isinstance(dataFilter["school"], str) else dataFilter["school"]
            class_number = dataFilter["class_number"]
        except Exception:
            city = dataFilter.get("city")
            school = dataFilter.get("school")
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
        """Отправляет заявки на прикрепление всем найденным ученикам."""
        for ID in self.searchClass:
            oldApplication = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == ID, "application")
            newApplication = f"{(oldApplication or '')}{self._ID};"
            Manager.update_record(Tables.Users, "telegram_id", ID, "application", newApplication)
            self._telegramBot.send_message(
                ID,
                f"учитель {self.name} {self.surname} хочет прикрепить вас к себе. Для подтверждения перейдите в заявки",
            )

        self._telegramBot.send_message(self._ID, "Заявка отправлена", reply_markup = keyboards.Teacher.main)
        return True

    @core.log
    def show_my_students(self):
        """Показывает список прикрепленных к учителю учеников.""" 
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

    def show_profile_actions(self):
        """Показывает доступные действия профиля учителя."""
        self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup = keyboards.Teacher.profile)

    def show_main_menu(self):
        """Открывает главное меню учителя."""
        self._telegramBot.send_message(self._ID, "главная", reply_markup = keyboards.Teacher.main)
        return True

    def assign_homework(self):
        """Показывает меню для задания домашней работы."""
        try:
            self._telegramBot.send_message(self._ID, "Выберите тип задания", reply_markup=keyboards.Teacher.homework)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню заданий: {e}")
            self.text_out("Произошла ошибка при открытии меню заданий")
            return False

    def assign_individual_task(self):
        """Запускает процесс формирования индивидуального задания (заглушка)."""
        try:
            # Здесь можно добавить логику для создания индивидуального задания
            self._telegramBot.send_message(self._ID, "Функция индивидуальных заданий в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при создании индивидуального задания: {e}")
            self.text_out("Произошла ошибка при создании задания")
            return False

    def assign_class_task(self):
        """Запускает процесс выдачи задания для класса (заглушка)."""
        try:
            # Здесь можно добавить логику для создания задания для класса
            self._telegramBot.send_message(self._ID, "Функция заданий для класса в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при создании задания для класса: {e}")
            self.text_out("Произошла ошибка при создании задания")
            return False

    def check_tasks(self):
        """Показывает меню для проверки поступивших решений."""
        try:
            self._telegramBot.send_message(self._ID, "Выберите тип заданий для проверки", reply_markup=keyboards.Teacher.check_task)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню проверки: {e}")
            self.text_out("Произошла ошибка при открытии меню проверки")
            return False

    def check_individual_tasks(self):
        """Показывает индивидуальные задания для проверки (заглушка)."""
        try:
            # Здесь можно добавить логику для показа индивидуальных заданий
            self._telegramBot.send_message(self._ID, "Функция проверки индивидуальных заданий в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при проверке индивидуальных заданий: {e}")
            self.text_out("Произошла ошибка при проверке заданий")
            return False

    def check_class_tasks(self):
        """Показывает задания класса для проверки (заглушка)."""
        try:
            # Здесь можно добавить логику для показа заданий класса
            self._telegramBot.send_message(self._ID, "Функция проверки заданий класса в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при проверке заданий класса: {e}")
            self.text_out("Произошла ошибка при проверке заданий")
            return False


class Student(Registered):
    """Реализация логики для роли Ученик."""
    def __init__(self, myID: str = "", bind_bot = None):
        super().__init__(myID, bind_bot)
        self.llm = LLM()  # Инициализация LLM для студента

    # removed duplicate show_main_menu; keep unified implementation below

    def recognize_user(self):
        """Дополняет базовую информацию полями города/школы/класса."""
        super().recognize_user()
        self.city = self._reader_my_data("city")
        self.school = self._reader_my_data("school")
        self.class_ = self._reader_my_data("student_class")

    def __cancel_application(self, teacherID):
        data_filter = lambda column: Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, column)  
        old = data_filter("application")
        new = old.replace(f"{teacherID};", "")
        Manager.update_record(Tables.Users, "telegram_id", self._ID, "application", new)

        notification = f"{self.name} {self.surname} из школы №{self.school} класса {self.class_} отклонил заявку"
        self._telegramBot.send_message(teacherID, notification)
        self._telegramBot.send_message(self._ID, "Заявка отклонена", reply_markup=keyboards.Student.main)
        return True

    def __accept_application(self, teacherID):
        data_filter = lambda column:  Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, column)  
        old = data_filter("application")
        new = old.replace(f"{teacherID};", "")
        Manager.update_record(Tables.Users, "telegram_id", self._ID, "application", new)

        old = data_filter("my_teachers")
        if old == None:
            new = f"{teacherID};"
        else:
            new = f"{old}{teacherID};"
        Manager.update_record(Tables.Users, "telegram_id", self._ID, "my_teachers", new)

        old = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == teacherID, "attached_students") 
        if old == None:
            new = f"{self._ID};"
        else:
            new = f"{old}{self._ID};"
        Manager.update_record(Tables.Users, "telegram_id", teacherID, "attached_students", new)

        notification = f"{self.name} {self.surname} из школы №{self.school} класса {self.class_} принял заявку"
        self._telegramBot.send_message(teacherID, notification)
        self._telegramBot.send_message(self._ID, "Заявка принята", reply_markup=keyboards.Student.main) 
        return True

    def show_applications(self):
        """Показывает входящие заявки от учителей и предлагает действия."""
        buttons = []
        subButton = []

        teachersIDS = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self._ID, "application")
        if not teachersIDS:
            self._telegramBot.send_message(self._ID, "Заявок нет", reply_markup=keyboards.Student.main)
            return
        
        teachersIDS = teachersIDS.split(";")[:-1]

        name_surname_ref_teacher = []
        for ID in teachersIDS:
            data_filter = lambda column:  Manager.get_cell(Tables.Users, Tables.Users.telegram_id == ID, column)  
            name = data_filter("name")
            surname = data_filter("surname")
            ref = data_filter("ref")

            general = [self._ID, self.name, self.surname, self.school, self.class_, ID, self._telegramBot]
            cancel = lambda: Student.__cancel_application(*general)
            accept = lambda: Student.__accept_application(*general)
            subButton.append(Button("отклонить заявку", cancel))
            subButton.append(Button("принять заявку", accept))

            buttons.append(Button(f"{name} {surname}, {ref}", lambda: self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup=keyboards.Student.application)))

            name_surname_ref_teacher.append([f"{name} {surname}, {ref}"])

        keyboard = keyboards.create_keyboard(*name_surname_ref_teacher)
        self._telegramBot.send_message(self._ID, "Выберите учителя", reply_markup = keyboard)
        return True

    def show_profile_actions(self):
        """Показывает доступные действия профиля ученика."""
        self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup = keyboards.Student.profile)

    def show_main_menu(self):
        self._telegramBot.send_message(self._ID, "главная", reply_markup = keyboards.Student.main)
        return True

    def show_my_teachers(self):
        """Показывает список учителей, прикреплённых к ученику."""
        try:
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
        except Exception as e:
            print(f"Ошибка при показе учителей: {e}")
            self._telegramBot.send_message(self._ID, "Произошла ошибка при получении списка учителей", reply_markup=keyboards.Student.main)
            return False

    def show_tasks(self):
        """Показывает меню для работы с заданиями (получение/отправка/практика)."""
        try:
            self._telegramBot.send_message(self._ID, "Выберите действие с заданиями", reply_markup=keyboards.Student.task)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню заданий: {e}")
            self.text_out("Произошла ошибка при открытии меню заданий")
            return False

    def get_tasks(self):
        """Получает доступные задания (заглушка)."""
        try:
            # Здесь можно добавить логику для получения заданий
            self._telegramBot.send_message(self._ID, "Функция получения заданий в разработке", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при получении заданий: {e}")
            self.text_out("Произошла ошибка при получении заданий")
            return False

    def submit_solution(self):
        """Запускает процесс отправки решения (заглушка)."""
        try:
            # Здесь можно добавить логику для отправки решения
            self._telegramBot.send_message(self._ID, "Функция отправки решений в разработке", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при отправке решения: {e}")
            self.text_out("Произошла ошибка при отправке решения")
            return False

    
class Unregistered(User):
    """Реализация логики для незарегистрированного пользователя (гость)."""
    START_MESSAGE = "Здравствуйте, этот бот даст теорию по математике, для его полного использования нужно зарегестрироваться"

    def __init__(self, myID: str = "", bind_bot = None):
        super().__init__(myID, bind_bot)
        self.current_registration = None

    def __registration(self, enterData, role):
        """Сохраняет данные регистрации пользователя c указанной ролью."""
        user_record = Tables.Users(**enterData, telegram_id=self._ID, role=role)
        Manager.write(user_record)

    def teacher_registration(self):
        """Начинает регистрацию учителя"""
        self.current_registration = btn.Unreg.teacher_registration()
        self.current_registration.set_ID(self._ID)
        self.current_registration.run()

    def student_registration(self):
        """Начинает регистрацию ученика"""
        self.current_registration = btn.Unreg.student_registration()
        self.current_registration.set_ID(self._ID)
        self.current_registration.run()
        return True

    def _determine_role_from_data(self, data: dict) -> str:
        """Определяет роль (ученик/учитель) по заполненным полям формы регистрации."""
        return "ученик" if 'student_class' in data else "учитель"
    
    def _finish_registration(self):
        """Завершает процесс регистрации и уведомляет пользователя."""
        try:
            if self.current_registration and self.current_registration.registration_finished:
                data = self.current_registration.collection()
                if data:
                    role = self._determine_role_from_data(data)
                    self.__registration(data, role)
                    self.current_registration = None
                    self.text_out("Регистрация завершена успешно!")
                    return True
            return False
        except Exception as e:
            print(f"Ошибка при завершении регистрации: {e}")
            self.text_out("Ошибка при завершении регистрации")
            return False

    def handle_registration_input(self):
        """Обрабатывает ввод пользователя во время регистрации."""
        if self.current_registration and not self.current_registration.registration_finished:
            try:
                self.current_registration.request(self._current_request)
                self.current_registration.run()
                
                # Если регистрация завершена, завершаем процесс
                if self.current_registration.registration_finished:
                    self._finish_registration()
                    self.current_command = None
            except Exception as e:
                print(f"Ошибка при обработке ввода регистрации: {e}")
                self.text_out("Произошла ошибка при обработке ввода")

    def command_executor(self):
        """Универсальный метод для выполнения текущей команды гостя/регистрации."""
        print(f"Execute вызван с current_command: {self.current_command}")
        if self.current_command:
            # Проверяем, идет ли процесс регистрации
            if self.current_registration and not self.current_registration.registration_finished:
                print("Обрабатываем ввод регистрации")
                self.handle_registration_input()
            else:
                # Выполняем обычную команду
                print(f"Выполняем команду: {self.current_command}")
                try:
                    self.current_command()
                except Exception as e:
                    print(f"Ошибка при выполнении команды: {e}")
                    self.text_out("Произошла ошибка при выполнении команды")
        else:
            print("current_command не установлен, ничего не выполняем")
            
    def getting_started(self):
        """Приветственное сообщение и меню для гостя (первый вход)."""
        self.text_out(self.START_MESSAGE, keyboards.Guest.main)
        return True
    
    def show_main_menu(self):
        """Главное меню гостя."""
        self.text_out("главное меню", keyboards.Guest.main)
        return True


from database import Manager, Tables
from core import Button
import buttons as btn
import keyboards
import core
from LLM import LLM

def find_my_role(ID):
    return Manager.get_cell(Tables.Users, Tables.Users.telegram_id == ID, "role")

class User:
    RUN_BOT_COMMADS = ["/start"]
    SHOW_MAIN_MENU = ["главная", "меню", "/меню", "/главная"]

    def __init__(self, ID, bind_bot = None):
        self.info = core.UserRecognizer(ID)
        self._ID = ID
        self._telegramBot = bind_bot
        self._current_request = None
        self._current_command = None

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
        self._current_request = request

    def command_executor(self):
        if callable(self._current_command):
            self._current_command()



class Registered(User):
    class DeleteProfile(core.Process):
        def __init__(self, ID, cancelable = True):
            super().__init__(ID, cancelable)
            self._chain = [self.ask_for_password, self.password_entry_verification]

        def _delete_account(self):
            Manager.delete_record(Tables.Users, "telegram_id", self._me.get_ID())

        def _password_entry_error_message(self):
            self._bot.send_message(self._me.get_ID(), "Неверный пароль, повторите попытку")
        
        def _successful_profile_deletion_message(self):
            self._bot.send_message(self._me.get_ID(), "Профиль удалён")

        def ask_for_password(self):
            self._bot.send_message(self._me.get_ID(), "Введите ваш пароль для удаления профиля")

        def password_entry_verification(self):
            if self._current_request == self._me.password:
                self._successful_profile_deletion_message()
                self._delete_account()
            else:
                self._password_entry_error_message()
                raise core.UserInputError("password entry error")
            
    def __init__(self, ID: str = "", telegramBot = None):
        super().__init__(ID, telegramBot)

        self.delete_profile_process = self.DeleteProfile(ID)

    def delete_account(self):
        self._current_command = self.delete_profile_process.execute


 
    


class Teacher(Registered):
    def __init__(self, myID: str = "", bind_bot = None):
        super().__init__(myID, bind_bot)
        self.searchClass = []
        self._ref = f"tg://user?id={self._ID}"
        self.llm = LLM()  # Инициализация LLM для учителя

        self.searchClass = Button(btn.Teacher.search_class().data_input, self.__search_class)
    
    def show_main_menu(self):
        self.text_out("главное меню", keyboards.Teacher.main)
        return True

    def search_class(self):
        """Начинает поиск класса"""
        self.searchClass = btn.Teacher.search_class()
        self.searchClass.set_ID(self._ID)
        self.searchClass.run()
        return True

    @core.log
    def __search_class(self, dataFilter: dict): 
        self.searchClass = []
        search = Manager.search_records(
            Tables.Users,
            Tables.Users.city == dataFilter["city"] and
            Tables.Users.school == dataFilter["school"] and
            Tables.Users.student_class == dataFilter["class_number"]
        )
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
        """отправтить заявку на прикрепление найденным ученикам"""
        for ID in self.searchClass:
            oldApplication = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == {self._ID},"application")

            if oldApplication:
                newApplication = f"{oldApplication}{self._ID};"
            else:
                newApplication = f"{self._ID};"
            Manager.update_record(Tables.Users, "telegram_id", ID, "application", newApplication)
            self._telegramBot.send_message(ID, f"учитель {self.name} {self.name} хочет прикрепить вас к себе. Для подтверждения перейдите в заявки")

        self._telegramBot.send_message(self._ID, "Заявка отправлена", reply_markup = keyboards.Teacher.main)
        return True

    @core.log
    def show_my_students(self):
        """Показывает список прикрепленных учеников""" 
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
        self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup = keyboards.Teacher.profile)

    def show_main_menu(self):
        self._telegramBot.send_message(self._ID, "главная", reply_markup = keyboards.Teacher.main)

    def assign_homework(self):
        """Показывает меню для задания домашнего задания"""
        try:
            self._telegramBot.send_message(self._ID, "Выберите тип задания", reply_markup=keyboards.Teacher.homework)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню заданий: {e}")
            self.text_out("Произошла ошибка при открытии меню заданий")
            return False

    def assign_individual_task(self):
        """Начинает процесс задания индивидуального задания"""
        try:
            # Здесь можно добавить логику для создания индивидуального задания
            self._telegramBot.send_message(self._ID, "Функция индивидуальных заданий в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при создании индивидуального задания: {e}")
            self.text_out("Произошла ошибка при создании задания")
            return False

    def assign_class_task(self):
        """Начинает процесс задания задания для класса"""
        try:
            # Здесь можно добавить логику для создания задания для класса
            self._telegramBot.send_message(self._ID, "Функция заданий для класса в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при создании задания для класса: {e}")
            self.text_out("Произошла ошибка при создании задания")
            return False

    def check_tasks(self):
        """Показывает меню для проверки заданий"""
        try:
            self._telegramBot.send_message(self._ID, "Выберите тип заданий для проверки", reply_markup=keyboards.Teacher.check_task)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню проверки: {e}")
            self.text_out("Произошла ошибка при открытии меню проверки")
            return False

    def check_individual_tasks(self):
        """Показывает индивидуальные задания для проверки"""
        try:
            # Здесь можно добавить логику для показа индивидуальных заданий
            self._telegramBot.send_message(self._ID, "Функция проверки индивидуальных заданий в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при проверке индивидуальных заданий: {e}")
            self.text_out("Произошла ошибка при проверке заданий")
            return False

    def check_class_tasks(self):
        """Показывает задания класса для проверки"""
        try:
            # Здесь можно добавить логику для показа заданий класса
            self._telegramBot.send_message(self._ID, "Функция проверки заданий класса в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при проверке заданий класса: {e}")
            self.text_out("Произошла ошибка при проверке заданий")
            return False


class Student(Registered):
    def __init__(self, myID: str = "", bind_bot = None):
        super().__init__(myID, bind_bot)
        self.llm = LLM()  # Инициализация LLM для студента

    def show_main_menu(self):
        self.text_out("главное меню", keyboards.Student.main)
        return True

    def recognize_user(self):
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
        self._telegramBot.send_message(self._ID, "Выберите действие", reply_markup = keyboards.Student.profile)

    def show_main_menu(self):
        self._telegramBot.send_message(self._ID, "главная", reply_markup = keyboards.Student.main)

    def show_my_teachers(self):
        """Показывает список прикрепленных учителей"""
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
        """Показывает меню для работы с заданиями"""
        try:
            self._telegramBot.send_message(self._ID, "Выберите действие с заданиями", reply_markup=keyboards.Student.task)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню заданий: {e}")
            self.text_out("Произошла ошибка при открытии меню заданий")
            return False

    def get_tasks(self):
        """Получает доступные задания"""
        try:
            # Здесь можно добавить логику для получения заданий
            self._telegramBot.send_message(self._ID, "Функция получения заданий в разработке", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при получении заданий: {e}")
            self.text_out("Произошла ошибка при получении заданий")
            return False

    def submit_solution(self):
        """Начинает процесс отправки решения"""
        try:
            # Здесь можно добавить логику для отправки решения
            self._telegramBot.send_message(self._ID, "Функция отправки решений в разработке", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при отправке решения: {e}")
            self.text_out("Произошла ошибка при отправке решения")
            return False

    
class Unregistered(User):
    START_MESSAGE = "Здравствуйте, этот бот даст теорию по математике, для его полного использования нужно зарегестрироваться"

    def __init__(self, myID: str = "", bind_bot = None):
        super().__init__(myID, bind_bot)
        self.current_registration = None

    def __registration(self, enterData, role):
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
        """Определяет роль на основе данных регистрации"""
        return "ученик" if 'student_class' in data else "учитель"
    
    def _finish_registration(self):
        """Завершает процесс регистрации"""
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
        """Обрабатывает ввод во время регистрации"""
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
        """Универсальный метод для выполнения текущей команды"""
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
        """Вызывается при первом входе в бота"""
        self.text_out(self.START_MESSAGE, keyboards.Guest.main)
        return True
    
    def show_main_menu(self):
        """Вызывается при входе в главное меню"""
        self.text_out("главное меню", keyboards.Guest.main)
        return True


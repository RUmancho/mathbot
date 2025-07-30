from database import Manager, Tables
from core import Button
import buttons as btn
import keyboards
import core
from LLM import LLM

class User:
    RUN_BOT_COMMADS = ["/start"]
    SHOW_MAIN_MENU = ["главная", "меню", "/меню", "/главная"]

    def __init__(self, ID: str = "", telegramBot = None):
        self.ID = ID
        self._telegramBot = telegramBot
        self.current_request = None
        self.current_command = None

    def undo_support(self, function: callable):
        def wrapper(*args, **kwargs):
            if self.current_request == "отмена":
                function(*args, **kwargs)
        return wrapper

    def unsupported_command_warning(self):
        self.text_out("Неизвестная команда")

    def text_out(self, text: str, markup = None):
        self._telegramBot.send_message(self.ID, text = text, reply_markup=markup)

    def update_last_request(self, request):
        self.current_request = request

    @staticmethod
    def registered_users_IDS() -> list:
        search = Manager.get_column(Tables.Users.telegram_id)
        return search

    @staticmethod
    def find_my_role(ID) -> str:
        search = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == ID, "role")
        return search


class Registered(User):
    def __init__(self, ID: str = "", telegramBot = None):
        super().__init__(ID, telegramBot)

        self.btnDeleteProfile = Button(self._start_delete_profile, self._handle_password_input)

    def load_user(self):
        self.name     = self._reader_my_data("name")
        self.surname  = self._reader_my_data("surname")
        self.password = self._reader_my_data("password")
        self.role     = self._reader_my_data("role")

    def delete_account(self):
        self.btnDeleteProfile.exe()

    def _start_delete_profile(self):
        self._telegramBot.send_message(self.ID, "Введите пароль для удаления профиля", reply_markup = keyboards.Student.profile)
        return True

    def _handle_password_input(self):
        if self.current_request == self.password:
            Manager.delete_record(Tables.Users, "telegram_id", self.ID)
            self._telegramBot.send_message(self.ID, "Ваш профиль успешно удален", reply_markup = keyboards.Guest.main)
            return True
        else:
            self._telegramBot.send_message(self.ID, "Неверный пароль", reply_markup = keyboards.Student.profile)
            raise ValueError("Неверный пароль")

    def _reader_my_data(self, column: str):
        search = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self.ID, column)
        return search


class Teacher(Registered):
    def __init__(self, myID: str = "", telegramBot = None):
        super().__init__(myID, telegramBot)
        self.searchClass = []
        self.ref = f"tg://user?id={self.ID}"
        self.llm = LLM()  # Инициализация LLM для учителя

        self.searchClass = Button(btn.Teacher.pin_class().data_input, self.__search_class)
    
    def show_main_menu(self):
        self.text_out("главное меню", keyboards.Teacher.main)
        return True

    def search_class(self):
        """Начинает поиск класса"""
        self.searchClass = btn.Teacher.search_class()
        self.searchClass.set_ID(self.ID)
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

            self._telegramBot.send_message(self.ID, out, reply_markup=keyboards.Teacher.attached)
            self.searchClass = studentIDS
            return studentIDS
        else:
            self._telegramBot.send_message(self.ID, text="ничего не найдено")

    @core.log
    def send_application(self):
        """отправтить заявку на прикрепление найденным ученикам"""
        for ID in self.searchClass:
            oldApplication = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == {self.ID},"application")

            if oldApplication:
                newApplication = f"{oldApplication}{self.ID};"
            else:
                newApplication = f"{self.ID};"
            Manager.update_record(Tables.Users, "telegram_id", ID, "application", newApplication)
            self._telegramBot.send_message(ID, f"учитель {self.name} {self.name} хочет прикрепить вас к себе. Для подтверждения перейдите в заявки")

        self._telegramBot.send_message(self.ID, "Заявка отправлена", reply_markup = keyboards.Teacher.main)
        return True

    def show_my_students(self):
        """Показывает список прикрепленных учеников""" 
        try:
            attached_students = self._reader_my_data("attached_students")
            if not attached_students:
                self._telegramBot.send_message(self.ID, "У вас пока нет прикрепленных учеников", reply_markup=keyboards.Teacher.main)
                return
            
            student_ids = attached_students.split(";")[:-1]
            out = "Ваши ученики:\n\n"
            
            for student_id in student_ids:
                name = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "name")
                surname = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "surname")
                school = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "school")
                student_class = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "student_class")
                
                out += f"• {name} {surname} (школа №{school}, {student_class} класс)\n"
            
            self._telegramBot.send_message(self.ID, out, reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при показе учеников: {e}")
            self._telegramBot.send_message(self.ID, "Произошла ошибка при получении списка учеников", reply_markup=keyboards.Teacher.main)
            return False

    def show_profile_actions(self):
        self._telegramBot.send_message(self.ID, "Выберите действие", reply_markup = keyboards.Teacher.profile)

    def show_main_menu(self):
        self._telegramBot.send_message(self.ID, "главная", reply_markup = keyboards.Teacher.main)

    def assign_homework(self):
        """Показывает меню для задания домашнего задания"""
        try:
            self._telegramBot.send_message(self.ID, "Выберите тип задания", reply_markup=keyboards.Teacher.homework)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню заданий: {e}")
            self.text_out("Произошла ошибка при открытии меню заданий")
            return False

    def assign_individual_task(self):
        """Начинает процесс задания индивидуального задания"""
        try:
            # Здесь можно добавить логику для создания индивидуального задания
            self._telegramBot.send_message(self.ID, "Функция индивидуальных заданий в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при создании индивидуального задания: {e}")
            self.text_out("Произошла ошибка при создании задания")
            return False

    def assign_class_task(self):
        """Начинает процесс задания задания для класса"""
        try:
            # Здесь можно добавить логику для создания задания для класса
            self._telegramBot.send_message(self.ID, "Функция заданий для класса в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при создании задания для класса: {e}")
            self.text_out("Произошла ошибка при создании задания")
            return False

    def check_tasks(self):
        """Показывает меню для проверки заданий"""
        try:
            self._telegramBot.send_message(self.ID, "Выберите тип заданий для проверки", reply_markup=keyboards.Teacher.check_task)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню проверки: {e}")
            self.text_out("Произошла ошибка при открытии меню проверки")
            return False

    def check_individual_tasks(self):
        """Показывает индивидуальные задания для проверки"""
        try:
            # Здесь можно добавить логику для показа индивидуальных заданий
            self._telegramBot.send_message(self.ID, "Функция проверки индивидуальных заданий в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при проверке индивидуальных заданий: {e}")
            self.text_out("Произошла ошибка при проверке заданий")
            return False

    def check_class_tasks(self):
        """Показывает задания класса для проверки"""
        try:
            # Здесь можно добавить логику для показа заданий класса
            self._telegramBot.send_message(self.ID, "Функция проверки заданий класса в разработке", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при проверке заданий класса: {e}")
            self.text_out("Произошла ошибка при проверке заданий")
            return False

    def generate_individual_task(self):
        """Генерирует индивидуальное задание с помощью LLM"""
        try:
            # Получаем информацию о студенте для персонализации
            student_info = "Создай математическое задание для ученика"
            
            prompt = f"""
            Создай математическое задание для ученика. Задание должно быть:
            - Соответствовать школьной программе
            - Иметь четкую формулировку
            - Включать правильный ответ
            - Быть интересным и познавательным
            
            Формат ответа:
            ЗАДАНИЕ: [текст задания]
            ОТВЕТ: [правильный ответ]
            ОБЪЯСНЕНИЕ: [краткое объяснение решения]
            """
            
            response = self.llm.request(prompt, context=student_info)
            self._telegramBot.send_message(self.ID, f"Сгенерированное задание:\n\n{response}", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при генерации задания: {e}")
            self.text_out("Произошла ошибка при создании задания")
            return False

    def generate_class_task(self):
        """Генерирует задание для класса с помощью LLM"""
        try:
            prompt = """
            Создай математическое задание для всего класса. Задание должно быть:
            - Подходящим для групповой работы
            - Иметь несколько уровней сложности
            - Включать элементы творчества
            - Содержать четкие инструкции
            
            Формат ответа:
            ЗАДАНИЕ: [текст задания]
            КРИТЕРИИ ОЦЕНКИ: [критерии оценки]
            ВРЕМЯ: [рекомендуемое время выполнения]
            """
            
            response = self.llm.request(prompt)
            self._telegramBot.send_message(self.ID, f"Сгенерированное задание для класса:\n\n{response}", reply_markup=keyboards.Teacher.main)
            return True
        except Exception as e:
            print(f"Ошибка при генерации задания для класса: {e}")
            self.text_out("Произошла ошибка при создании задания")
            return False

    def check_solution_with_llm(self, student_solution: str, task_description: str):
        """Проверяет решение студента с помощью LLM"""
        try:
            prompt = f"""
            Проверь решение студента по математике.
            
            ЗАДАНИЕ: {task_description}
            РЕШЕНИЕ СТУДЕНТА: {student_solution}
            
            Проанализируй решение и дай оценку:
            - Правильность решения
            - Полнота ответа
            - Ошибки (если есть)
            - Рекомендации по улучшению
            - Оценка (по 5-балльной шкале)
            
            Формат ответа:
            ОЦЕНКА: [балл]
            АНАЛИЗ: [подробный анализ]
            РЕКОМЕНДАЦИИ: [рекомендации]
            """
            
            response = self.llm.request(prompt)
            return response
        except Exception as e:
            print(f"Ошибка при проверке решения: {e}")
            return "Произошла ошибка при проверке решения"

    def get_student_progress_analysis(self, student_id: str):
        """Анализирует прогресс студента с помощью LLM"""
        try:
            # Получаем данные о студенте и его работах
            student_name = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "name")
            student_surname = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == student_id, "surname")
            
            prompt = f"""
            Проанализируй прогресс ученика {student_name} {student_surname}.
            
            Создай анализ, который включает:
            - Сильные стороны ученика
            - Области для улучшения
            - Рекомендации по обучению
            - Персональный план развития
            
            Анализ должен быть мотивирующим и конструктивным.
            """
            
            response = self.llm.request(prompt)
            return response
        except Exception as e:
            print(f"Ошибка при анализе прогресса: {e}")
            return "Произошла ошибка при анализе прогресса"

    def create_personalized_explanation(self, topic: str, student_level: str):
        """Создает персонализированное объяснение темы"""
        try:
            prompt = f"""
            Создай объяснение темы "{topic}" для ученика уровня "{student_level}".
            
            Объяснение должно быть:
            - Понятным для указанного уровня
            - Содержать примеры
            - Включать практические задания
            - Быть структурированным и логичным
            
            Формат:
            ТЕОРИЯ: [объяснение]
            ПРИМЕРЫ: [примеры]
            ЗАДАНИЯ: [практические задания]
            """
            
            response = self.llm.request(prompt)
            return response
        except Exception as e:
            print(f"Ошибка при создании объяснения: {e}")
            return "Произошла ошибка при создании объяснения"


class Student(Registered):
    def __init__(self, myID: str = "", telegramBot = None):
        super().__init__(myID, telegramBot)
        self.llm = LLM()  # Инициализация LLM для студента

    def show_main_menu(self):
        self.text_out("главное меню", keyboards.Student.main)
        return True

    def load_user(self):
        super().load_user()
        self.city = self._reader_my_data("city")
        self.school = self._reader_my_data("school")
        self.class_ = self._reader_my_data("student_class")

    def __cancel_application(self, teacherID):
        data_filter = lambda column: Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self.ID, column)  
        old = data_filter("application")
        new = old.replace(f"{teacherID};", "")
        Manager.update_record(Tables.Users, "telegram_id", self.ID, "application", new)

        notification = f"{self.name} {self.surname} из школы №{self.school} класса {self.class_} отклонил заявку"
        self._telegramBot.send_message(teacherID, notification)
        self._telegramBot.send_message(self.ID, "Заявка отклонена", reply_markup=keyboards.Student.main)
        return True

    def __accept_application(self, teacherID):
        data_filter = lambda column:  Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self.ID, column)  
        old = data_filter("application")
        new = old.replace(f"{teacherID};", "")
        Manager.update_record(Tables.Users, "telegram_id", self.ID, "application", new)

        old = data_filter("my_teachers")
        if old == None:
            new = f"{teacherID};"
        else:
            new = f"{old}{teacherID};"
        Manager.update_record(Tables.Users, "telegram_id", self.ID, "my_teachers", new)

        old = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == teacherID, "attached_students") 
        if old == None:
            new = f"{self.ID};"
        else:
            new = f"{old}{self.ID};"
        Manager.update_record(Tables.Users, "telegram_id", teacherID, "attached_students", new)

        notification = f"{self.name} {self.surname} из школы №{self.school} класса {self.class_} принял заявку"
        self._telegramBot.send_message(teacherID, notification)
        self._telegramBot.send_message(self.ID, "Заявка принята", reply_markup=keyboards.Student.main) 
        return True

    def show_applications(self):
        buttons = []
        subButton = []

        teachersIDS = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == self.ID, "application")
        if not teachersIDS:
            self._telegramBot.send_message(self.ID, "Заявок нет", reply_markup=keyboards.Student.main)
            return
        
        teachersIDS = teachersIDS.split(";")[:-1]

        name_surname_ref_teacher = []
        for ID in teachersIDS:
            data_filter = lambda column:  Manager.get_cell(Tables.Users, Tables.Users.telegram_id == ID, column)  
            name = data_filter("name")
            surname = data_filter("surname")
            ref = data_filter("ref")

            general = [self.ID, self.name, self.surname, self.school, self.class_, ID, self._telegramBot]
            cancel = lambda: Student.__cancel_application(*general)
            accept = lambda: Student.__accept_application(*general)
            subButton.append(Button("отклонить заявку", cancel))
            subButton.append(Button("принять заявку", accept))

            buttons.append(Button(f"{name} {surname}, {ref}", lambda: self._telegramBot.send_message(self.ID, "Выберите действие", reply_markup=keyboards.Student.application)))

            name_surname_ref_teacher.append([f"{name} {surname}, {ref}"])

        keyboard = keyboards.create_keyboard(*name_surname_ref_teacher)
        self._telegramBot.send_message(self.ID, "Выберите учителя", reply_markup = keyboard)
        return True

    def show_profile_actions(self):
        self._telegramBot.send_message(self.ID, "Выберите действие", reply_markup = keyboards.Student.profile)

    def show_main_menu(self):
        self._telegramBot.send_message(self.ID, "главная", reply_markup = keyboards.Student.main)

    def show_my_teachers(self):
        """Показывает список прикрепленных учителей"""
        try:
            my_teachers = self._reader_my_data("my_teachers")
            if not my_teachers:
                self._telegramBot.send_message(self.ID, "У вас пока нет прикрепленных учителей", reply_markup=keyboards.Student.main)
                return
            
            teacher_ids = my_teachers.split(";")[:-1]
            out = "Ваши учителя:\n\n"
            
            for teacher_id in teacher_ids:
                name = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == teacher_id, "name")
                surname = Manager.get_cell(Tables.Users, Tables.Users.telegram_id == teacher_id, "surname")
                
                out += f"• {name} {surname}\n"
            
            self._telegramBot.send_message(self.ID, out, reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при показе учителей: {e}")
            self._telegramBot.send_message(self.ID, "Произошла ошибка при получении списка учителей", reply_markup=keyboards.Student.main)
            return False

    def show_tasks(self):
        """Показывает меню для работы с заданиями"""
        try:
            self._telegramBot.send_message(self.ID, "Выберите действие с заданиями", reply_markup=keyboards.Student.task)
            return True
        except Exception as e:
            print(f"Ошибка при показе меню заданий: {e}")
            self.text_out("Произошла ошибка при открытии меню заданий")
            return False

    def get_tasks(self):
        """Получает доступные задания"""
        try:
            # Здесь можно добавить логику для получения заданий
            self._telegramBot.send_message(self.ID, "Функция получения заданий в разработке", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при получении заданий: {e}")
            self.text_out("Произошла ошибка при получении заданий")
            return False

    def submit_solution(self):
        """Начинает процесс отправки решения"""
        try:
            # Здесь можно добавить логику для отправки решения
            self._telegramBot.send_message(self.ID, "Функция отправки решений в разработке", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при отправке решения: {e}")
            self.text_out("Произошла ошибка при отправке решения")
            return False

    def get_math_help(self, question: str):
        """Получает помощь по математике от LLM"""
        try:
            prompt = f"""
            Помоги ученику с математическим вопросом: "{question}"
            
            Твой ответ должен быть:
            - Понятным и пошаговым
            - Содержать объяснение логики
            - Включать примеры, если нужно
            - Мотивирующим для дальнейшего изучения
            
            Формат ответа:
            ОБЪЯСНЕНИЕ: [подробное объяснение]
            РЕШЕНИЕ: [пошаговое решение]
            ПОДСКАЗКА: [дополнительная подсказка]
            """
            
            response = self.llm.request(prompt)
            self._telegramBot.send_message(self.ID, f"Помощь по вашему вопросу:\n\n{response}", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при получении помощи: {e}")
            self.text_out("Произошла ошибка при получении помощи")
            return False

    def check_my_solution(self, task: str, my_solution: str):
        """Проверяет собственное решение с помощью LLM"""
        try:
            prompt = f"""
            Проверь решение ученика.
            
            ЗАДАЧА: {task}
            МОЕ РЕШЕНИЕ: {my_solution}
            
            Проанализируй:
            - Правильность решения
            - Возможные ошибки
            - Альтернативные способы решения
            - Рекомендации по улучшению
            
            Формат ответа:
            ПРАВИЛЬНОСТЬ: [да/нет с объяснением]
            АНАЛИЗ: [подробный анализ]
            РЕКОМЕНДАЦИИ: [советы по улучшению]
            """
            
            response = self.llm.request(prompt)
            self._telegramBot.send_message(self.ID, f"Анализ вашего решения:\n\n{response}", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при проверке решения: {e}")
            self.text_out("Произошла ошибка при проверке решения")
            return False

    def get_practice_tasks(self, topic: str, difficulty: str = "средний"):
        """Получает дополнительные задачи для практики"""
        try:
            prompt = f"""
            Создай 3 математические задачи по теме "{topic}" уровня сложности "{difficulty}".
            
            Задачи должны быть:
            - Соответствовать школьной программе
            - Иметь разные типы (вычислительные, логические, прикладные)
            - Включать правильные ответы
            - Быть интересными и познавательными
            
            Формат ответа:
            ЗАДАЧА 1: [текст задачи]
            ОТВЕТ 1: [ответ]
            
            ЗАДАЧА 2: [текст задачи]
            ОТВЕТ 2: [ответ]
            
            ЗАДАЧА 3: [текст задачи]
            ОТВЕТ 3: [ответ]
            """
            
            response = self.llm.request(prompt)
            self._telegramBot.send_message(self.ID, f"Задачи для практики по теме '{topic}':\n\n{response}", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при получении задач: {e}")
            self.text_out("Произошла ошибка при получении задач")
            return False

    def get_theory_explanation(self, topic: str):
        """Получает объяснение теории по теме"""
        try:
            prompt = f"""
            Объясни теорию по теме "{topic}" для школьника.
            
            Объяснение должно быть:
            - Понятным и доступным
            - Содержать основные понятия
            - Включать примеры
            - Структурированным и логичным
            
            Формат ответа:
            ОПРЕДЕЛЕНИЕ: [основные понятия]
            ТЕОРИЯ: [подробное объяснение]
            ПРИМЕРЫ: [примеры применения]
            ВАЖНО: [ключевые моменты для запоминания]
            """
            
            response = self.llm.request(prompt)
            self._telegramBot.send_message(self.ID, f"Теория по теме '{topic}':\n\n{response}", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при получении теории: {e}")
            self.text_out("Произошла ошибка при получении теории")
            return False

    def get_study_plan(self, weak_topics: list):
        """Получает персональный план обучения"""
        try:
            topics_str = ", ".join(weak_topics)
            prompt = f"""
            Создай персональный план обучения для ученика, который испытывает трудности с темами: {topics_str}
            
            План должен включать:
            - Последовательность изучения тем
            - Рекомендуемое время на каждую тему
            - Практические задания
            - Критерии успешного освоения
            - Мотивирующие элементы
            
            Формат ответа:
            ПЛАН ОБУЧЕНИЯ:
            [пошаговый план]
            
            РЕКОМЕНДАЦИИ:
            [советы по эффективному изучению]
            """
            
            response = self.llm.request(prompt)
            self._telegramBot.send_message(self.ID, f"Ваш персональный план обучения:\n\n{response}", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при создании плана обучения: {e}")
            self.text_out("Произошла ошибка при создании плана обучения")
            return False

    def get_math_tips(self):
        """Получает полезные советы по математике"""
        try:
            prompt = """
            Дай 5 полезных советов для изучения математики.
            
            Советы должны быть:
            - Практичными и применимыми
            - Мотивирующими
            - Подходящими для школьников
            - Включать конкретные техники
            
            Формат ответа:
            СОВЕТ 1: [описание]
            СОВЕТ 2: [описание]
            СОВЕТ 3: [описание]
            СОВЕТ 4: [описание]
            СОВЕТ 5: [описание]
            """
            
            response = self.llm.request(prompt)
            self._telegramBot.send_message(self.ID, f"Полезные советы по математике:\n\n{response}", reply_markup=keyboards.Student.main)
            return True
        except Exception as e:
            print(f"Ошибка при получении советов: {e}")
            self.text_out("Произошла ошибка при получении советов")
            return False

class Unregistered(User):
    START_MESSAGE = "Здравствуйте, этот бот даст теорию по математике, для его полного использования нужно зарегестрироваться"

    def __init__(self, myID: str = "", telegramBot = None):
        super().__init__(myID, telegramBot)
        self.myID = myID
        self.telegramBot = telegramBot
        self.current_registration = None

    def __registration(self, enterData, role):
        user_record = Tables.Users(**enterData, telegram_id=self.myID, role=role)
        Manager.write(user_record)

    def teacher_registration(self):
        """Начинает регистрацию учителя"""
        self.current_registration = btn.Unreg.teacher_registration()
        self.current_registration.set_ID(self.ID)
        self.current_registration.run()

    def student_registration(self):
        """Начинает регистрацию ученика"""
        self.current_registration = btn.Unreg.student_registration()
        self.current_registration.set_ID(self.ID)
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
                self.current_registration.request(self.current_request)
                self.current_registration.run()
                
                # Если регистрация завершена, завершаем процесс
                if self.current_registration.registration_finished:
                    self._finish_registration()
                    self.current_command = None
            except Exception as e:
                print(f"Ошибка при обработке ввода регистрации: {e}")
                self.text_out("Произошла ошибка при обработке ввода")

    def execute(self):
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
        self.text_out(self.START_MESSAGE, keyboards.Guest.main)
        return True
    
    def show_main_menu(self):
        self.text_out("главное меню", keyboards.Guest.main)
        return True
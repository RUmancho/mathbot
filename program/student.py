import database
import keyboards
from LLM import LLM
from base import Registered
from enums import AIMode


class Student(Registered):
    def __init__(self, myID: str = "", bind_bot=None):
        super().__init__(myID, bind_bot)
        self.llm = LLM()
        self.llm.set_role("math teacher")
        self.ai_process = None
        self._ai_mode: AIMode | None = None  # режим работы AI помощника

    def show_main_menu(self):
        """Показывает главное меню ученика."""
        self.out("главная", keyboards.Student.main)

    def show_applications(self):
        """Выводит список входящих заявок от учителей."""
        teachersIDS = self.info.application
        if not teachersIDS:
            self.out("Заявок нет", keyboards.Student.main)
            return
        teachersIDS = teachersIDS.split(";")[:-1]
        name_surname_ref_teacher = []
        for ID in teachersIDS:
            teacher = database.Client(ID)

            label = f"{teacher.name} {teacher.surname}"
            if teacher.username:
                label = f"{label}, @{teacher.username}"
            else:
                label = f"{label}, (нет @username)"
            name_surname_ref_teacher.append([label])
        keyboard = keyboards.create_keyboard(*name_surname_ref_teacher)
        self.out("Выберите учителя", keyboard)
        

    def show_profile_actions(self):
        """Показывает действия профиля (удаление/редактирование)."""
        self.out("Выберите действие", keyboards.Student.profile)

    def show_my_teachers(self):
        """Показывает прикреплённых к ученику учителей."""
        my_teachers = self.info.my_teachers
        if not my_teachers:
            self.out("У вас пока нет прикрепленных учителей", keyboards.Student.main)
            return
        teacher_ids = my_teachers.split(";")[:-1]
        out = "Ваши учителя:\n\n"
        for teacher_id in teacher_ids:
            teacher = database.Client(teacher_id)
            out += f"• {teacher.name} {teacher.surname}\n"

        self.out(out, keyboards.Student.main)
        
    def show_tasks(self):
        """Показывает меню работы с заданиями ученика."""
        self.out("Выберите действие с заданиями", keyboards.Student.task)
        
    def get_tasks(self):
        """Заглушка: получение заданий (можно расширить сохранением в БД)."""
        self.out("Функция получения заданий в разработке", keyboards.Student.main)

    def show_ai_helper_menu(self):
        """Открывает раздел AI‑помощника для ученика."""
        self.out("Раздел AI Помощник", keyboards.Student.ai_helper)

    def ai_practice(self):
        """Запрашивает у AI набор тренировочных задач по теме (с ответами)."""
        self._ai_mode = AIMode.PRACTICE
        self.out("Укажите тему, по которой нужны тренировки")

    def ai_generate_task(self):
        """Генерирует ОДНУ задачу по теме без решения и ответа."""
        self._ai_mode = AIMode.GENERATE_TASK
        self.out("Укажите тему, по которой сгенерировать одно задание (без решения)")

    def _ai_receive_and_answer(self):
        """Получает ввод пользователя, отправляет промпт LLM и возвращает ответ"""
        user_text = getattr(self, "_current_request", "").strip()
        if not user_text:
            return
        answer = self.llm.respond(self._ai_mode, user_text)
        self.out(answer, keyboards.Student.ai_helper)
        self._ai_mode = None
        
    def has_active_process(self) -> bool:
        return self._ai_mode is not None

    def handle_active_process(self) -> bool:
        try:
            self._ai_receive_and_answer()
            return True
        except Exception:
            return False
            
from enum import Enum


class AIMode(Enum):
    HELP_PROBLEM = "help_problem"
    EXPLAIN = "explain"
    TIPS = "tips"
    PLAN = "plan"
    CHECK_SOLUTION = "check_solution"
    PRACTICE = "practice"
    GENERATE_TASK = "generate_task"


class StudentCommands(Enum):
    PROFILE = "профиль"
    APPLICATIONS = "заявки"
    MY_TEACHERS = "мои учителя"
    TASKS = "задания"
    GET_TASKS = "получить задания"
    SUBMIT_SOLUTION = "отправить решение"
    DELETE_PROFILE = "удалить профиль"
    AI_ASSISTANT = "ai помощник"
    AI_HELP_WITH_PROBLEM = "помощь с задачей"
    AI_EXPLAIN_THEORY = "объяснить теорию"
    AI_TIPS = "получить советы"
    AI_STUDY_PLAN = "план обучения"
    AI_CHECK_SOLUTION = "проверить решение"
    AI_PRACTICE = "практика"


class TeacherCommands(Enum):
    PROFILE = "профиль"
    ATTACH_CLASS = "прикрепить класс"
    MY_STUDENTS = "ваши учащиеся"
    SEND_TASK = "отправить задание"
    CHECK_TASKS = "проверить задания"
    SEND_INDIVIDUAL_TASK = "отправить индивидуальное задание"
    SEND_CLASS_TASK = "отправить задание классу"
    CHECK_INDIVIDUAL_TASKS = "проверить индивидуальные задания"
    CLASS_TASKS = "задания для класса"
    DELETE_PROFILE = "удалить профиль"
    AI_ASSISTANT = "ai помощник"
    AI_CREATE_EXPLANATION = "создать объяснение"
    AI_ANALYZE_STUDENT = "анализ студента"
    AI_PERSONALIZED_TASK = "персонализированное задание"
    AI_GENERATE_TASK = "сгенерировать задание"
    AI_GENERATE_FOR_CLASS = "сгенерировать для класса"
    AI_CHECK = "ai проверка"
    ANALYZE_PROGRESS = "анализ прогресса"
    ATTACH_ALL = "прикрепить всех"



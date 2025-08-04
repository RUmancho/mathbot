from config import PASSWORD_LENGTH
import keyboards
import core

class Unreg:
    @staticmethod
    def teacher_registration():
        return core.ButtonCollector(
            {
                core.Sender("name", "Введите ваше настоящее имя")                                : core.Validator.name,
                core.Sender("surname", "Введите вашу настоящую фамилию")                         : core.Validator.surname,
                core.Sender("password", f"придумайте пароль, содержащий {PASSWORD_LENGTH} цифр") : core.Validator.create_password,
            },
            "Вы зарегестировались",
            keyboards.Teacher.main,
        )

    @staticmethod
    def student_registration():
        return core.ButtonCollector(
            {
                core.Sender("name",          "Введите ваше настоящее имя")                           : core.Validator.name,
                core.Sender("surname",       "Введите вашу настоящую фамилию")                       : core.Validator.surname,
                core.Sender("password",     f"Придумайте пароль, содержащий {PASSWORD_LENGTH} цифры"): core.Validator.create_password,
                core.Sender("city",          "В каком городе вы учитесь?" )                          : core.Validator.city,
                core.Sender("school",        "В какой школе вы учитесь?")                            : core.Validator.school,
                core.Sender("student_class", "В каком классе вы учитесь?")                           : core.Validator.class_number
            },
            "Вы зарегестировались",
            keyboards.Student.main,
        )

class Teacher:
    @staticmethod
    def search_class():
        return core.ButtonCollector(
            {
                core.Sender("city",         "В каком городе учатся учащиеся? (название города)") : core.Validator.city,
                core.Sender("school",       "В какой школе?")                                    : core.Validator.school,
                core.Sender("class_number", "В каком классе? (номер класса и буква)")            : core.Validator.class_number
            },
            "поиск...",
            keyboards.Teacher.main,
        )

from resource import resource as res
from core import FileSender
import keyboards

math = {
    "алгебра": ("Выберите раздел", keyboards.algebra),
    # "геометрия": ("Выберите раздел", UI.geometry),
    "вычислительные навыки": ("Выберите нужную тему", keyboards.calculation),
    "найти значение выражения": ("Выберите тему", keyboards.expression),
    "графики": ("Выберите тему", keyboards.graphics),
    "формулы сокращенного умножения": ("Выберите тему", keyboards.AMF),
    "уравнения": ("Выберите тему", keyboards.equation),
    "неравенства": ("Выберите тему", keyboards.inequality),
    "тригонометрия": ("Выберите тему", keyboards.trigonometry),
    # "работа с формулами": (...),
}

algebra_theory = {
    "действия с обычными дробями"        : FileSender(keyboards.calculation,  res["algebra"]["calculations"]["fractions_theory"], res["algebra"]["calculations"]["fractions_image"]),
    "арифметический корень"              : FileSender(keyboards.expression,   res["algebra"]["expressions"]["square_root_theory"]),
    "квадрат суммы"                      : FileSender(keyboards.AMF,          res["algebra"]["AMF"]["square_of_sum_theory"]),
    "квадрат разности"                   : FileSender(keyboards.AMF,          res["algebra"]["AMF"]["square_of_difference_theory"]),
    "разность квадратов"                 : FileSender(keyboards.AMF,          res["algebra"]["AMF"]["difference_of_squares_theory"]),
    "куб суммы"                          : FileSender(keyboards.AMF,          res["algebra"]["AMF"]["cube_of_sum_theory"]),
    "куб разности"                       : FileSender(keyboards.AMF,          res["algebra"]["AMF"]["cube_of_difference_theory"]),
    "сумма кубов"                        : FileSender(keyboards.AMF,          res["algebra"]["AMF"]["sum_of_cubes_theory"]),
    "разность кубов"                     : FileSender(keyboards.AMF,          res["algebra"]["AMF"]["difference_of_cubes_theory"]),
    "линейные уравнения"                 : FileSender(keyboards.equation,     res["algebra"]["equations"]["linear_equations_theory"]),
    "квадратные уравнения (дескриминант)": FileSender(keyboards.equation,     res["algebra"]["equations"]["quadratic_via_discriminant_theory"]),
    "квадратные уравнения (виет)"        : FileSender(keyboards.equation,     res["algebra"]["equations"]["quadratic_via_viet_theorem_theory"]),
    "уравнения вида ax² + bx = 0"        : FileSender(keyboards.equation,     res["algebra"]["equations"]["incomplete_quadratic_type1_theory"]),
    "уравнения вида ax² + c = 0"         : FileSender(keyboards.equation,     res["algebra"]["equations"]["incomplete_quadratic_type2_theory"]),
    "линейные неравенства"               : FileSender(keyboards.inequality,   res["algebra"]["inequalities"]["linear_inequalities_theory"]),
    "основные тригонометрические функции": FileSender(keyboards.trigonometry, res["algebra"]["trigonometry"]["basic_trigonometric_functions_theory"]),
    "тригонометрические уравнения"       : FileSender(keyboards.trigonometry, res["algebra"]["trigonometry"]["trigonometric_equations_theory"])
}

def handler(request, text_out, chat_id):
    """Обрабатывает запросы к теоретическим материалам.

    Возвращает True, если запрос обслужен (теория отправлена или предложены
    подразделы), иначе False — чтобы дальнейшая логика обработала запрос.
    """
    FileSender.set_chat_id(chat_id)
    if request in math.keys():
        text_out(math[request][0], math[request][1])
        return True

    elif request in algebra_theory.keys():
        algebra_theory[request].push()
        return True
    
    return False
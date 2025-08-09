from resource import resource as res
from core import FileSender
import keyboards as kb

math = {
    "алгебра": ("Выберите раздел", kb.algebra),
    "вычислительные навыки": ("Выберите нужную тему", kb.calculation),
    "найти значение выражения": ("Выберите тему", kb.expression),
    "графики": ("Выберите тему", kb.graphics),
    "формулы сокращенного умножения": ("Выберите тему", kb.AMF),
    "уравнения": ("Выберите тему", kb.equation),
    "неравенства": ("Выберите тему", kb.inequality),
    "тригонометрия": ("Выберите тему", kb.trigonometry),
}

algebra_theory = {
    "действия с обычными дробями": FileSender(kb.calculation, res["algebra"]["calculations"]["fractions_theory"], res["algebra"]["calculations"]["fractions_image"]),
    "арифметический корень": FileSender(kb.expression, res["algebra"]["expressions"]["square_root_theory"]),
    "квадрат суммы": FileSender(kb.AMF, res["algebra"]["AMF"]["square_of_sum_theory"]),
    "квадрат разности": FileSender(kb.AMF, res["algebra"]["AMF"]["square_of_difference_theory"]),
    "разность квадратов": FileSender(kb.AMF, res["algebra"]["AMF"]["difference_of_squares_theory"]),
    "куб суммы": FileSender(kb.AMF, res["algebra"]["AMF"]["cube_of_sum_theory"]),
    "куб разности": FileSender(kb.AMF, res["algebra"]["AMF"]["cube_of_difference_theory"]),
    "сумма кубов": FileSender(kb.AMF, res["algebra"]["AMF"]["sum_of_cubes_theory"]),
    "разность кубов": FileSender(kb.AMF, res["algebra"]["AMF"]["difference_of_cubes_theory"]),
    "линейные уравнения": FileSender(kb.equation, res["algebra"]["equations"]["linear_equations_theory"]),
    "квадратные уравнения (дескриминант)": FileSender(kb.equation, res["algebra"]["equations"]["quadratic_via_discriminant_theory"]),
    "квадратные уравнения (виет)": FileSender(kb.equation, res["algebra"]["equations"]["quadratic_via_viet_theorem_theory"]),
    "уравнения вида ax² + bx = 0": FileSender(kb.equation, res["algebra"]["equations"]["incomplete_quadratic_type1_theory"]),
    "уравнения вида ax² + c = 0": FileSender(kb.equation, res["algebra"]["equations"]["incomplete_quadratic_type2_theory"]),
    "линейные неравенства": FileSender(kb.inequality, res["algebra"]["inequalities"]["linear_inequalities_theory"]),
    "основные тригонометрические функции": FileSender(kb.trigonometry, res["algebra"]["trigonometry"]["basic_trigonometric_functions_theory"]),
    "тригонометрические уравнения": FileSender(kb.trigonometry, res["algebra"]["trigonometry"]["trigonometric_equations_theory"]),
}


def handler(request, text_out, chat_id):
    FileSender.set_chat_id(chat_id)
    if request in math.keys():
        text_out(math[request][0], math[request][1])
        return True
    elif request in algebra_theory.keys():
        algebra_theory[request].push()
        return True
    elif request == "геометрия":
        text_out("пока недоступно")
    return False



from resource import resource as res
from core import ResourceChain
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
    "действия с обычными дробями"        : ResourceChain(keyboards.calculation,  res["algebra"]["calculations"]["fractions_theory"], res["algebra"]["calculations"]["fractions_image"]),
    "арифметический корень"              : ResourceChain(keyboards.expression,   res["algebra"]["expressions"]["square_root_theory"]),
    "квадрат суммы"                      : ResourceChain(keyboards.AMF,          res["algebra"]["AMF"]["square_of_sum_theory"]),
    "квадрат разности"                   : ResourceChain(keyboards.AMF,          res["algebra"]["AMF"]["square_of_difference_theory"]),
    "разность квадратов"                 : ResourceChain(keyboards.AMF,          res["algebra"]["AMF"]["difference_of_squares_theory"]),
    "куб суммы"                          : ResourceChain(keyboards.AMF,          res["algebra"]["AMF"]["cube_of_sum_theory"]),
    "куб разности"                       : ResourceChain(keyboards.AMF,          res["algebra"]["AMF"]["cube_of_difference_theory"]),
    "сумма кубов"                        : ResourceChain(keyboards.AMF,          res["algebra"]["AMF"]["sum_of_cubes_theory"]),
    "разность кубов"                     : ResourceChain(keyboards.AMF,          res["algebra"]["AMF"]["difference_of_cubes_theory"]),
    "линейные уравнения"                 : ResourceChain(keyboards.equation,     res["algebra"]["equations"]["linear_equations_theory"]),
    "квадратные уравнения (дескриминант)": ResourceChain(keyboards.equation,     res["algebra"]["equations"]["quadratic_via_discriminant_theory"]),
    "квадратные уравнения (виет)"        : ResourceChain(keyboards.equation,     res["algebra"]["equations"]["quadratic_via_viet_theorem_theory"]),
    "уравнения вида ax² + bx = 0"        : ResourceChain(keyboards.equation,     res["algebra"]["equations"]["incomplete_quadratic_type1_theory"]),
    "уравнения вида ax² + c = 0"         : ResourceChain(keyboards.equation,     res["algebra"]["equations"]["incomplete_quadratic_type2_theory"]),
    "линейные неравенства"               : ResourceChain(keyboards.inequality,   res["algebra"]["inequalities"]["linear_inequalities_theory"]),
    "основные тригонометрические функции": ResourceChain(keyboards.trigonometry, res["algebra"]["trigonometry"]["basic_trigonometric_functions_theory"]),
    "тригонометрические уравнения"       : ResourceChain(keyboards.trigonometry, res["algebra"]["trigonometry"]["trigonometric_equations_theory"])
}

def handler(request, text_out, chat_id):
    ResourceChain.set_chat_id(chat_id)
    if request in math.keys():
        text_out(math[request][0], math[request][1])
        return True

    elif request in algebra_theory.keys():
        algebra_theory[request].push()
        return True
    
    elif request == "геометрия":
        text_out("пока недоступно")
    
    return False
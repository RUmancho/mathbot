from resource import resource as res
from core import FileSender
import keyboards
from LLM import LLM
from enums import AIMode
from image_generator import get_math_image_generator
import re
import os

# Создаем экземпляр LLM для алгебры
algebra_ai_assistant = None
bot_instance = None  # Будет установлен в handler

def get_algebra_ai():
    """Получить или создать AI ассистента для алгебры."""
    global algebra_ai_assistant
    try:
        if algebra_ai_assistant is None:
            algebra_ai_assistant = LLM()
            algebra_ai_assistant.set_role("math teacher")
        return algebra_ai_assistant
    except Exception as e:
        print(f"Ошибка инициализации LLM: {e}")
        return None

def _send_processing_message(chat_id: str, mode: AIMode):
    """Отправляет сообщение о том, что AI обрабатывает запрос."""
    try:
        if bot_instance is None:
            return
        
        processing_messages = {
            AIMode.EXPLAIN: "🧠 AI анализирует тему и готовит подробное объяснение...\n⏳ Подождите 10-15 секунд",
            AIMode.HELP_PROBLEM: "🔢 AI решает задачу пошагово...\n⏳ Подождите 10-15 секунд",
            AIMode.PRACTICE: "📝 AI создает практические задачи...\n⏳ Подождите 10-15 секунд", 
            AIMode.CHECK_SOLUTION: "🔍 AI проверяет ваше решение...\n⏳ Подождите 10-15 секунд",
            AIMode.TIPS: "💡 AI готовит практические советы...\n⏳ Подождите 10-15 секунд",
            AIMode.PLAN: "📅 AI составляет план обучения...\n⏳ Подождите 10-15 секунд",
            AIMode.GENERATE_TASK: "⚡ AI генерирует задачу...\n⏳ Подождите 10-15 секунд",
            # Специфические режимы для разделов алгебры
            AIMode.COMPUTATIONAL_SKILLS: "📊 AI готовит материалы по вычислительным навыкам...\n⏳ Подождите 10-15 секунд",
            AIMode.EXPRESSION_VALUE: "🔢 AI готовит объяснение нахождения значения выражений...\n⏳ Подождите 10-15 секунд",
            AIMode.FORMULAS_WORK: "📝 AI готовит материалы по работе с формулами...\n⏳ Подождите 10-15 секунд",
            AIMode.SHORTHAND_FORMULAS: "⚡ AI готовит объяснение формул сокращённого умножения...\n⏳ Подождите 10-15 секунд",
            AIMode.EQUATIONS: "🔺 AI готовит материалы по решению уравнений...\n⏳ Подождите 10-15 секунд",
            AIMode.INEQUALITIES: "📈 AI готовит объяснение неравенств...\n⏳ Подождите 10-15 секунд",
            AIMode.GRAPHS: "📊 AI готовит материалы по графикам функций...\n⏳ Подождите 10-15 секунд",
            AIMode.TRIGONOMETRY: "🔄 AI готовит основы тригонометрии...\n⏳ Подождите 10-15 секунд",
            AIMode.PROBABILITY: "🎲 AI готовит материалы по теории вероятностей...\n⏳ Подождите 10-15 секунд",
            # Специальные режимы для геометрии
            AIMode.TRIANGLES: "📐 AI готовит материалы о треугольниках с диаграммами...\n⏳ Подождите 10-15 секунд",
            AIMode.QUADRILATERALS: "⬜ AI готовит материалы о четырёхугольниках с изображениями...\n⏳ Подождите 10-15 секунд",
            AIMode.CIRCLES: "⭕ AI готовит материалы об окружности с диаграммами...\n⏳ Подождите 10-15 секунд",
            AIMode.AREAS_VOLUMES: "📏 AI готовит формулы площадей и объёмов с визуализацией...\n⏳ Подождите 10-15 секунд",
            AIMode.COORDINATE_GEOMETRY: "📊 AI готовит материалы по координатной геометрии с графиками...\n⏳ Подождите 10-15 секунд"
        }
        
        message = processing_messages.get(mode, "🤖 AI обрабатывает ваш запрос...\n⏳ Подождите 10-15 секунд")
        
        bot_instance.send_message(chat_id, message)
        
    except Exception as e:
        print(f"Ошибка при отправке сообщения о процессе: {e}")




def _clean_latex_symbols(text: str) -> str:
    """Удаляет LaTeX символы и заменяет их на простой текст."""
    try:
        import re
        
        # Удаляем LaTeX display math delimiters: $$ ... $$
        text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)
        
        # Удаляем LaTeX inline math delimiters: $ ... $
        text = re.sub(r'\$(.*?)\$', r'`\1`', text)
        
        # Удаляем LaTeX команды \log и заменяем на простой текст
        text = re.sub(r'\\log', r'log', text)
        text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)  # Удаляем \command{content}
        text = re.sub(r'\\[a-zA-Z]+', '', text)  # Удаляем \command
        
        return text
    except Exception as e:
        print(f"Ошибка очистки LaTeX: {e}")
        return text

def _process_image_tags(text: str) -> tuple:
    """Обрабатывает теги изображений в тексте и возвращает очищенный текст и список изображений для генерации."""
    try:
        from colorama import Fore, Style
        
        # Паттерн для поиска тегов изображений
        image_pattern = r'\[IMAGE:([^\]]+)\]'
        image_tags = re.findall(image_pattern, text)
        
        print(f"{Fore.MAGENTA}🖼️ [IMAGE PROCESSOR]{Style.RESET_ALL} Найдено тегов изображений: {len(image_tags)}")
        
        # Удаляем теги изображений из текста
        clean_text = re.sub(image_pattern, '', text)
        
        # Список изображений для генерации
        images_to_generate = []
        
        for tag in image_tags:
            print(f"{Fore.MAGENTA}🏷️ [IMAGE TAG]{Style.RESET_ALL} Обработка тега: {tag}")
            images_to_generate.append(tag.strip())
        
        return clean_text, images_to_generate
        
    except Exception as e:
        from colorama import Fore, Style
        print(f"{Fore.RED}❌ [IMAGE PROCESSOR ERROR]{Style.RESET_ALL} Ошибка обработки тегов изображений: {e}")
        return text, []

def _send_generated_images(chat_id: str, image_tags: list):
    """Генерирует и отправляет изображения на основе тегов."""
    try:
        if not image_tags or bot_instance is None:
            return
            
        from colorama import Fore, Style
        print(f"{Fore.CYAN}🎨 [IMAGE SENDER]{Style.RESET_ALL} Начинаем генерацию {len(image_tags)} изображений")
        
        generator = get_math_image_generator()
        
        for tag in image_tags:
            print(f"{Fore.CYAN}🖼️ [IMAGE GEN]{Style.RESET_ALL} Генерация изображения для тега: {tag}")
            
            image_path = None
            
            # Определяем тип изображения и генерируем
            if tag == "trigonometric_circle":
                image_path = generator.generate_trigonometric_circle()
            elif tag == "trigonometric_functions":
                image_path = generator.generate_trigonometric_functions()
            elif tag == "multiple_graphs":
                image_path = generator.generate_multiple_graphs()
            elif tag.startswith("graph_"):
                # Парсим тип функции из тега
                function_type = tag.replace("graph_", "")
                image_path = generator.generate_function_graph(function_type)
            
            # === ГЕОМЕТРИЧЕСКИЕ ИЗОБРАЖЕНИЯ ===
            elif tag == "triangles_diagram":
                image_path = generator.generate_triangles_diagram()
            elif tag == "quadrilaterals_diagram":
                image_path = generator.generate_quadrilaterals_diagram()
            elif tag == "circle_diagram":
                image_path = generator.generate_circle_diagram()
            elif tag == "areas_volumes_diagram":
                image_path = generator.generate_areas_volumes_diagram()
            elif tag == "coordinate_geometry_diagram":
                image_path = generator.generate_coordinate_geometry_diagram()
            
            else:
                # Попытка определить тип по ключевым словам
                if "тригоном" in tag.lower() or "trigon" in tag.lower():
                    if "окружность" in tag.lower() or "circle" in tag.lower():
                        image_path = generator.generate_trigonometric_circle()
                    else:
                        image_path = generator.generate_trigonometric_functions()
                elif "график" in tag.lower() or "graph" in tag.lower():
                    image_path = generator.generate_multiple_graphs()
                elif "треугольник" in tag.lower() or "triangle" in tag.lower():
                    image_path = generator.generate_triangles_diagram()
                elif "четырехугольник" in tag.lower() or "quadrilateral" in tag.lower():
                    image_path = generator.generate_quadrilaterals_diagram()
                elif "окружность" in tag.lower() and "тригоном" not in tag.lower():
                    image_path = generator.generate_circle_diagram()
                elif "площад" in tag.lower() or "объ" in tag.lower() or "volume" in tag.lower():
                    image_path = generator.generate_areas_volumes_diagram()
                elif "координат" in tag.lower() or "coordinate" in tag.lower():
                    image_path = generator.generate_coordinate_geometry_diagram()
                else:
                    print(f"{Fore.YELLOW}⚠️ [IMAGE GEN]{Style.RESET_ALL} Неизвестный тег изображения: {tag}")
                    continue
            
            # Отправляем изображение
            if image_path and os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as photo:
                        bot_instance.send_photo(chat_id, photo)
                    print(f"{Fore.GREEN}✅ [IMAGE SENT]{Style.RESET_ALL} Изображение отправлено: {os.path.basename(image_path)}")
                except Exception as e:
                    print(f"{Fore.RED}❌ [IMAGE SEND ERROR]{Style.RESET_ALL} Ошибка отправки изображения {image_path}: {e}")
            else:
                print(f"{Fore.RED}❌ [IMAGE GEN ERROR]{Style.RESET_ALL} Не удалось сгенерировать изображение для тега: {tag}")
                
    except Exception as e:
        from colorama import Fore, Style
        print(f"{Fore.RED}💥 [IMAGE SENDER ERROR]{Style.RESET_ALL} Ошибка генерации/отправки изображений: {e}")

def _send_ai_response(chat_id: str, text: str, keyboard=None):
    """Отправляет AI ответ с поддержкой Markdown форматирования и изображений."""
    try:
        if bot_instance is None:
            print("Bot instance не установлен")
            return
        
        # Обрабатываем теги изображений и генерируем изображения
        text_parts, images = _process_image_tags(text)
        
        # Отправляем изображения сначала
        _send_generated_images(chat_id, images)
        
        # Очищаем LaTeX символы и конвертируем в простой Markdown
        final_text = _clean_latex_symbols(text_parts)
        from colorama import Fore, Style
        print(f"{Fore.BLUE}📝 [MARKDOWN]{Style.RESET_ALL} Отправка текста с Markdown форматированием, длина: {len(final_text)} символов")
        
        # Разбиваем длинный текст на части (Telegram лимит ~4096 символов)
        max_length = 4000
        if len(final_text) <= max_length:
            bot_instance.send_message(
                chat_id, 
                final_text, 
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            # Разбиваем на части
            parts = []
            current_part = ""
            
            for line in final_text.split('\n'):
                if len(current_part) + len(line) + 1 <= max_length:
                    current_part += line + '\n'
                else:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = line + '\n'
            
            if current_part:
                parts.append(current_part.strip())
            
            # Отправляем части
            for i, part in enumerate(parts):
                if i == len(parts) - 1:  # Последняя часть с клавиатурой
                    bot_instance.send_message(
                        chat_id, 
                        f"📄 Часть {i+1}/{len(parts)}:\n\n{part}", 
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    bot_instance.send_message(
                        chat_id, 
                        f"📄 Часть {i+1}/{len(parts)}:\n\n{part}",
                        parse_mode='Markdown'
                    )
                    
    except Exception as e:
        print(f"Ошибка при отправке AI ответа с Markdown: {e}")
        # Fallback: отправляем без форматирования
        try:
            bot_instance.send_message(chat_id, text, reply_markup=keyboard)
        except Exception as fallback_e:
            print(f"Ошибка fallback отправки: {fallback_e}")

math = {
    "алгебра": ("Выберите раздел", keyboards.algebra),
    "геометрия": ("Выберите раздел", keyboards.geometry),
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

geometry_theory = {
    "треугольники"        : FileSender(keyboards.geometry, res["geometry"]["figures"]["triangle"]),
    "четырехугольники"    : FileSender(keyboards.geometry, res["geometry"]["figures"]["quadrilaterals"]),
    "окружность"          : FileSender(keyboards.geometry, res["geometry"]["figures"]["circle"]),
    "площади и объемы"    : FileSender(keyboards.geometry, res["geometry"]["documents"]["geometry_guide"]),
    "координатная геометрия": FileSender(keyboards.geometry, res["geometry"]["documents"]["geometry_guide"])
}

# AI флоу для алгебры
ALGEBRA_AI_FLOWS = {}  # chat_id -> {"mode": AIMode, "step": str, "data": dict}

def _handle_algebra_ai_flow(request: str, chat_id: str, text_out) -> bool:
    """Обрабатывает AI сценарии для алгебры."""
    try:
        flow = ALGEBRA_AI_FLOWS.get(chat_id)
        
        if request == "🤖 ai объяснение":
            text_out("Выберите AI функцию:", keyboards.algebra_ai)
            return True
        elif request == "🤖 ai практика":
            text_out("Выберите AI функцию:", keyboards.algebra_ai)
            return True
        elif request == "🤖 объяснить тему":
            from colorama import Fore, Style
            print(f"{Fore.GREEN}🎯 [THEORY AI]{Style.RESET_ALL} Пользователь {chat_id} запустил режим объяснения темы")
            text_out("Напишите тему алгебры, которую хотите изучить (например: 'квадратные уравнения', 'логарифмы', 'производные')")
            ALGEBRA_AI_FLOWS[chat_id] = {"mode": AIMode.EXPLAIN, "step": "waiting_topic", "data": {}}
            return True
        elif request == "🤖 решить задачу":
            text_out("Напишите задачу, которую нужно решить:")
            ALGEBRA_AI_FLOWS[chat_id] = {"mode": AIMode.HELP_PROBLEM, "step": "waiting_problem", "data": {}}
            return True
        elif request == "🤖 сгенерировать задачи":
            text_out("Укажите тему для генерации задач (например: 'линейные уравнения', 'квадратичные функции'):")
            ALGEBRA_AI_FLOWS[chat_id] = {"mode": AIMode.PRACTICE, "step": "waiting_topic", "data": {}}
            return True
        elif request == "🤖 проверить решение":
            text_out("Пришлите ваше решение задачи для проверки:")
            ALGEBRA_AI_FLOWS[chat_id] = {"mode": AIMode.CHECK_SOLUTION, "step": "waiting_solution", "data": {}}
            return True
        elif request == "🤖 дать советы":
            text_out("По какой теме алгебры дать советы? (например: 'изучение функций', 'решение уравнений'):")
            ALGEBRA_AI_FLOWS[chat_id] = {"mode": AIMode.TIPS, "step": "waiting_topic", "data": {}}
            return True
        elif request == "🤖 план изучения":
            text_out("Для какой темы создать план изучения? (например: 'алгебра 9 класс', 'тригонометрия'):")
            ALGEBRA_AI_FLOWS[chat_id] = {"mode": AIMode.PLAN, "step": "waiting_topic", "data": {}}
            return True
        
        # Обработка активных AI сценариев
        if flow:
            # Проверяем навигационные команды, которые должны прерывать AI флоу
            navigation_commands = [
                "/главная", "/start", "/меню", "/menu", "/main", "/home", 
                "главная", "старт", "меню", "menu", "main", "home",
                "алгебра", "геометрия", "помощь", "help", "/help"
            ]
            if request in navigation_commands:
                ALGEBRA_AI_FLOWS.pop(chat_id, None)
                print(f"AI флоу прерван навигационной командой: {request}")
                return False  # Позволяем основной логике обработать команду
            
            if request == "отмена":
                ALGEBRA_AI_FLOWS.pop(chat_id, None)
                text_out("AI запрос отменен", keyboards.algebra)
                return True
            
            ai = get_algebra_ai()
            if ai is None:
                text_out("AI ассистент недоступен. Проверьте настройки.", keyboards.algebra)
                ALGEBRA_AI_FLOWS.pop(chat_id, None)
                return True
            
            try:
                from colorama import Fore, Style
                print(f"{Fore.CYAN}🤖 [THEORY AI]{Style.RESET_ALL} Обработка AI запроса для {chat_id}, режим: {flow['mode']}, текст: '{request[:100]}...'")
                
                # Отправляем сообщение о том, что AI обрабатывает запрос
                _send_processing_message(chat_id, flow["mode"])
                
                print(f"{Fore.YELLOW}📡 [THEORY AI]{Style.RESET_ALL} Вызов ai.respond() для {chat_id}")
                response = ai.respond(flow["mode"], request)
                print(f"{Fore.GREEN}✅ [THEORY AI]{Style.RESET_ALL} Получен ответ для {chat_id}, длина: {len(response)} символов")
                
                # Отправляем AI ответ с поддержкой Markdown форматирования
                _send_ai_response(chat_id, f"🤖 {response}", keyboards.algebra_ai)
                print(f"{Fore.GREEN}📤 [THEORY AI]{Style.RESET_ALL} Ответ отправлен пользователю {chat_id}")
                
                ALGEBRA_AI_FLOWS.pop(chat_id, None)  # Завершаем флоу
                print(f"{Fore.MAGENTA}🔚 [THEORY AI]{Style.RESET_ALL} AI флоу завершен для {chat_id}")
                return True
            except Exception as e:
                from colorama import Fore, Style
                print(f"{Fore.RED}💥 [THEORY AI ERROR]{Style.RESET_ALL} Ошибка AI ответа для {chat_id}: {e}")
                text_out("Произошла ошибка при обработке AI запроса", keyboards.algebra)
                ALGEBRA_AI_FLOWS.pop(chat_id, None)
                return True
        
        return False
    except Exception as e:
        print(f"Ошибка в AI флоу алгебры: {e}")
        ALGEBRA_AI_FLOWS.pop(chat_id, None)
        return False


def _handle_algebra_llm_topics(request: str, chat_id: str, text_out) -> bool:
    """Обрабатывает традиционные темы алгебры через LLM вместо файлов."""
    try:
        # Сопоставление команд с AI режимами
        algebra_llm_commands = {
            "вычислительные навыки": AIMode.COMPUTATIONAL_SKILLS,
            "найти значение выражения": AIMode.EXPRESSION_VALUE,
            "работа с формулами": AIMode.FORMULAS_WORK,
            "формулы сокращённого умножения": AIMode.SHORTHAND_FORMULAS,
            "уравнения": AIMode.EQUATIONS,
            "неравенства": AIMode.INEQUALITIES,
            "графики": AIMode.GRAPHS,
            "тригонометрия": AIMode.TRIGONOMETRY,
            "теория вероятностей": AIMode.PROBABILITY
        }
        
        if request not in algebra_llm_commands:
            return False
        
        ai_mode = algebra_llm_commands[request]
        
        # Получаем AI ассистента
        ai = get_algebra_ai()
        if ai is None:
            text_out("AI ассистент недоступен. Проверьте настройки.", keyboards.algebra)
            return True
        
        try:
            from colorama import Fore, Style
            print(f"{Fore.CYAN}📚 [ALGEBRA LLM]{Style.RESET_ALL} Генерация контента для темы: {request} (режим: {ai_mode})")
            
            # Отправляем сообщение о том, что AI генерирует контент
            _send_processing_message(chat_id, ai_mode)
            
            # Генерируем контент через LLM
            response = ai.respond(ai_mode, request)
            print(f"{Fore.GREEN}✅ [ALGEBRA LLM]{Style.RESET_ALL} Контент сгенерирован, длина: {len(response)} символов")
            
            # Отправляем ответ пользователю
            _send_ai_response(chat_id, f"📚 {response}", keyboards.algebra)
            print(f"{Fore.GREEN}📤 [ALGEBRA LLM]{Style.RESET_ALL} Контент отправлен пользователю {chat_id}")
            
            return True
            
        except Exception as e:
            from colorama import Fore, Style
            print(f"{Fore.RED}💥 [ALGEBRA LLM ERROR]{Style.RESET_ALL} Ошибка генерации контента для {chat_id}: {e}")
            text_out("Произошла ошибка при генерации материалов", keyboards.algebra)
            return True
            
    except Exception as e:
        print(f"Ошибка в обработчике LLM тем алгебры: {e}")
        return False

def _handle_geometry_llm_topics(request: str, chat_id: str, text_out) -> bool:
    """Обрабатывает команды геометрии через LLM с изображениями."""
    try:
        # Словарь команд геометрии, которые теперь обрабатываются через LLM
        geometry_llm_commands = {
            "треугольники": AIMode.TRIANGLES,
            "четырехугольники": AIMode.QUADRILATERALS,
            "окружность": AIMode.CIRCLES,
            "площади и объемы": AIMode.AREAS_VOLUMES,
            "координатная геометрия": AIMode.COORDINATE_GEOMETRY
        }
        
        if request not in geometry_llm_commands:
            return False
        
        ai_mode = geometry_llm_commands[request]
        
        # Получаем AI ассистента
        ai = get_algebra_ai()  # Используем тот же AI экземпляр
        if ai is None:
            text_out("AI ассистент недоступен. Проверьте настройки.", keyboards.geometry)
            return True
        
        try:
            from colorama import Fore, Style
            print(f"{Fore.MAGENTA}📐 [GEOMETRY LLM]{Style.RESET_ALL} Генерация контента для темы: {request} (режим: {ai_mode})")
            
            # Отправляем сообщение о том, что AI генерирует контент
            _send_processing_message(chat_id, ai_mode)
            
            # Генерируем контент через LLM
            response = ai.respond(ai_mode, request)
            print(f"{Fore.GREEN}✅ [GEOMETRY LLM]{Style.RESET_ALL} Контент сгенерирован, длина: {len(response)} символов")
            
            # Отправляем ответ пользователю с геометрическими изображениями
            _send_ai_response(chat_id, f"📐 {response}", keyboards.geometry)
            print(f"{Fore.GREEN}📤 [GEOMETRY LLM]{Style.RESET_ALL} Контент отправлен пользователю {chat_id}")
            
            return True
            
        except Exception as e:
            from colorama import Fore, Style
            print(f"{Fore.RED}💥 [GEOMETRY LLM ERROR]{Style.RESET_ALL} Ошибка генерации контента для {chat_id}: {e}")
            text_out("Произошла ошибка при генерации материалов", keyboards.geometry)
            return True
            
    except Exception as e:
        print(f"Ошибка в обработчике LLM тем геометрии: {e}")
        return False

def handler(request, text_out, chat_id, bot=None):
    """Обрабатывает запросы к теоретическим материалам.

    Возвращает True, если запрос обслужен (теория отправлена или предложены
    подразделы), иначе False — чтобы дальнейшая логика обработала запрос.
    """
    try:
        global bot_instance
        if bot:
            bot_instance = bot
            
        FileSender.set_chat_id(chat_id)
        
        # Обработка AI команд для алгебры
        if _handle_algebra_ai_flow(request, chat_id, text_out):
            return True
        
        # Обработка традиционных алгебра команд через LLM
        if _handle_algebra_llm_topics(request, chat_id, text_out):
            return True
        
        # Обработка геометрических команд через LLM
        if _handle_geometry_llm_topics(request, chat_id, text_out):
            return True
        
        if request in math.keys():
            text_out(math[request][0], math[request][1])
            return True

        elif request in algebra_theory.keys():
            algebra_theory[request].push()
            return True
        
        elif request in geometry_theory.keys():
            geometry_theory[request].push()
            return True
        
        return False
    except Exception as e:
        print(f"Ошибка в обработчике теории для запроса '{request}': {e}")
        return False
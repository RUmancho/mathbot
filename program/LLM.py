from openai import OpenAI
import re
from enum import Enum, auto
from enums import AIMode
import config
import datetime
import json
from colorama import Fore, Back, Style, init

# Инициализируем colorama
init(autoreset=True)

def _llm_log(message: str, level: str = "INFO", request_id: str = None):
    """Логирование событий LLM с временной меткой, цветами и эмодзи."""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        req_info = f" [Req: {request_id}]" if request_id else ""
        
        # Определяем цвет и эмодзи для уровня логирования
        if level == "INFO":
            color = Fore.CYAN
            emoji = "🤖"
        elif level == "WARNING":
            color = Fore.YELLOW
            emoji = "⚠️"
        elif level == "ERROR":
            color = Fore.RED
            emoji = "🚨"
        elif level == "SUCCESS":
            color = Fore.GREEN
            emoji = "✨"
        elif level == "DEBUG":
            color = Fore.MAGENTA
            emoji = "🔧"
        else:
            color = Fore.WHITE
            emoji = "🤖"
        
        # Форматируем и выводим сообщение
        timestamp_colored = f"{Fore.BLUE}[{timestamp}]"
        level_colored = f"{color}[{emoji} LLM-{level}]"
        req_colored = f"{Fore.YELLOW}{req_info}" if request_id else ""
        message_colored = f"{Style.BRIGHT}{message}{Style.RESET_ALL}"
        
        print(f"{timestamp_colored} {level_colored}{req_colored} {message_colored}")
    except Exception as e:
        print(f"{Fore.RED}🚨 Ошибка LLM логирования: {e}{Style.RESET_ALL}")


class ResponseType(Enum):
    """Тип запрашиваемого ответа от модели."""
    CALCULATION = auto()  # Только числовой ответ
    EXPLANATION = auto()  # Развернутое объяснение
    CONCISE = auto()      # Краткий ответ

class LLM:
    ROLES = {
        "math teacher": {
            "base": "Ты опытный учитель математики. Отвечай на русском языке, используй Markdown форматирование: **жирный текст** для важного, *курсив* для акцентов, `код` для формул. НЕ используй LaTeX ($$ или $ символы)! Пиши математические выражения простым текстом или в `обратных кавычках`.",
            "calculation": "Предоставь ТОЛЬКО итоговый численный ответ без каких-либо объяснений или дополнительного текста. Только число.",
            "explanation": "Объясни концепцию подробно с примерами, пошагово. Используй Markdown форматирование: **заголовки** для разделов, *курсив* для терминов, `формулы` в обратных кавычках. НЕ используй LaTeX ($$ или $)! Пиши формулы простым текстом. Русский язык обязательно.",
            "concise": "Дай краткий и понятный ответ на вопрос на русском языке с Markdown форматированием. НЕ используй LaTeX ($$ или $)!"
        }
    }

    def __init__(self):
        _llm_log("🚀 Инициализация LLM класса...")
        try:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.model_name = config.OPENAI_MODEL
            _llm_log(f"✅ OpenAI клиент успешно инициализирован с моделью: {self.model_name}", "SUCCESS")
        except Exception as e:
            _llm_log(f"💥 ОШИБКА инициализации OpenAI клиента: {e}", "ERROR")
            self.client = None
            self.model_name = "gpt-4o-mini"

        self.role = ""
        self.task = ""
        self.prompt = ""
        self.response_type = ResponseType.EXPLANATION  # По умолчанию объяснение
        self.request_id = None  # Уникальный ID для отслеживания запросов

    def _generate_request_id(self) -> str:
        """Генерирует уникальный ID для запроса."""
        import time
        return f"{int(time.time() * 1000)}"

    def set_role(self, role: str) -> None:
        """Устанавливает роль подсказки (поддерживается только 'math teacher')."""
        _llm_log(f"🎭 Установка роли: {role}")
        if role not in self.ROLES:
            _llm_log(f"❌ ОШИБКА: Неподдерживаемая роль: {role}", "ERROR")
            raise ValueError("Unsupported model role selected")
        self.role = self.ROLES[role]["base"]
        _llm_log(f"✅ Роль успешно установлена: {role}", "SUCCESS")

    def set_response_type(self, response_type: ResponseType) -> None:
        """Меняет тип ответа модели (влияет на формирование промпта)."""
        self.response_type = response_type

    def calculate(self, expression: str) -> str:
        """Возвращает только числовой результат выражения, без пояснений."""
        self.response_type = ResponseType.CALCULATION
        expression = self._normalize_expression(expression)
        self.task = f"Calculate: {expression}"
        self._update_prompt()
        return self.run()

    def explain(self, topic: str) -> str:
        """Пишет развернутое объяснение темы с примерами и шагами."""
        self.response_type = ResponseType.EXPLANATION
        self.task = f"Explain: {topic}"
        self._update_prompt()
        return self.run()

    def ask(self, question: str) -> str:
        """Даёт краткий ответ на вопрос."""
        self.response_type = ResponseType.CONCISE
        self.task = question
        self._update_prompt()
        return self.run()

    def _update_prompt(self):
        if self.response_type == ResponseType.CALCULATION:
            instruction = self.ROLES["math teacher"]["calculation"]
        elif self.response_type == ResponseType.EXPLANATION:
            instruction = self.ROLES["math teacher"]["explanation"]
        else:
            instruction = self.ROLES["math teacher"]["concise"]
        
        # Обновляем роль с инструкцией для лучшего контекста
        self.role = f"{self.ROLES['math teacher']['base']} {instruction}"

    def _normalize_expression(self, expr: str) -> str:
        """Нормализует текстовые описания операций в форму, понятную модели."""
        expr = expr.lower().strip()
        replacements = {
            "squared": "^2",
            "cubed": "^3",
            "to the power of": "^",
            "square root of": "sqrt",
            "divided by": "/",
            "times": "*"
        }
        for k, v in replacements.items():
            expr = expr.replace(k, v)
        return expr

    def run(self) -> str:
        self.request_id = self._generate_request_id()
        _llm_log(f"🚀 Начало выполнения запроса", request_id=self.request_id)
        
        try:
            if self.client is None:
                _llm_log("🚨 ОШИБКА: OpenAI клиент недоступен", "ERROR", self.request_id)
                return "OpenAI клиент недоступен. Проверьте API ключ."
            
            # Формируем сообщения для Chat Completions API
            messages = [
                {"role": "system", "content": self.role},
                {"role": "user", "content": self.task}
            ]
            
            _llm_log(f"🛠️ Подготовка запроса к модели {self.model_name}", request_id=self.request_id)
            _llm_log(f"🎭 Система роль: {self.role[:100]}...", request_id=self.request_id, level="DEBUG")
            _llm_log(f"📝 Пользовательское задание: {self.task[:200]}...", request_id=self.request_id, level="DEBUG")
            
            # Определяем какой параметр для токенов использовать в зависимости от модели
            # Модели, которые используют max_completion_tokens вместо max_tokens
            newer_models = [
                "gpt-4o", "gpt-4o-mini", "gpt-4o-2024", 
                "o1-preview", "o1-mini", "o1",
                "gpt-5", "gpt-5-mini",  # На случай будущих моделей
                "chatgpt-4o-latest"
            ]
            uses_max_completion_tokens = any(model_pattern in self.model_name.lower() for model_pattern in newer_models)
            
            # Подготавливаем параметры запроса
            api_params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.7
            }
            
            # Добавляем правильный параметр для токенов
            if uses_max_completion_tokens:
                api_params["max_completion_tokens"] = 1000
                token_param = "max_completion_tokens"
            else:
                api_params["max_tokens"] = 1000
                token_param = "max_tokens"
            
            # Логируем параметры запроса
            request_params = {
                "model": self.model_name,
                token_param: 1000,
                "temperature": 0.7,
                "messages_count": len(messages),
                "uses_new_api": uses_max_completion_tokens
            }
            _llm_log(f"⚙️ Параметры запроса: {json.dumps(request_params, ensure_ascii=False)}", request_id=self.request_id, level="DEBUG")
            
            start_time = datetime.datetime.now()
            _llm_log("📡 Отправка запроса к OpenAI API...", request_id=self.request_id)
            
            response = self.client.chat.completions.create(**api_params)
            
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            _llm_log(f"⚡ Ответ получен за {duration:.2f} секунд", request_id=self.request_id, level="SUCCESS")
            
            # Логируем информацию об ответе
            usage = response.usage
            if usage:
                _llm_log(f"💰 Использование токенов - Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}", request_id=self.request_id)
            
            response_text = response.choices[0].message.content
            _llm_log(f"📏 Длина ответа: {len(response_text)} символов", request_id=self.request_id)
            _llm_log(f"📄 Начало ответа: {response_text[:200]}...", request_id=self.request_id, level="DEBUG")
            
            if self.response_type == ResponseType.CALCULATION:
                _llm_log("🔢 Извлечение числового значения из ответа", request_id=self.request_id)
                extracted = self._extract_number(response_text)
                _llm_log(f"🎯 Извлеченное число: {extracted}", request_id=self.request_id)
                return extracted
                
            _llm_log("✅ Запрос успешно завершен", request_id=self.request_id, level="SUCCESS")
            return response_text
            
        except Exception as e:
            _llm_log(f"💥 КРИТИЧЕСКАЯ ОШИБКА OpenAI API: {e}", "ERROR", self.request_id)
            error_msg = f"Произошла ошибка при обращении к AI: {e}"
            _llm_log(f"🚨 Возврат ошибки пользователю: {error_msg}", "ERROR", self.request_id)
            return error_msg

    def _extract_number(self, text: str) -> str:
        """Извлекает число из текста ответа"""
        matches = re.findall(r"-?\d+\.?\d*", text)
        return matches[0] if matches else "Could not extract number"

    def respond(self, mode: AIMode | None, user_text: str) -> str:
        """Формирует промпт по режиму и возвращает ответ модели."""
        _llm_log(f"🎯 Начало обработки respond для режима: {mode}")
        _llm_log(f"💬 Пользовательский текст: {user_text[:100]}...", level="DEBUG")
        
        try:
            prompt = self._build_prompt(mode, user_text)
            _llm_log(f"📝 Сформированный промпт: {prompt[:200]}...", level="DEBUG")
            
            answer = self.ask(prompt)
            _llm_log(f"📄 Получен ответ, длина: {len(answer)} символов", level="SUCCESS")
            
            if mode == AIMode.GENERATE_TASK:
                _llm_log("🧹 Применение санитизации для генерации задач")
                sanitized = self._sanitize_generated_task(answer)
                _llm_log(f"✨ Санитизированный ответ: {sanitized[:100]}...")
                return sanitized
            
            _llm_log("📤 Возврат обычного ответа без санитизации")
            return answer
        except Exception as e:
            _llm_log(f"💥 ОШИБКА в LLM.respond: {e}", "ERROR")
            return "Произошла ошибка при обработке запроса AI"

    @staticmethod
    def _build_prompt(mode: AIMode | None, text: str) -> str:
        """Создаёт промпт к LLM на основе выбранного режима AI."""
        try:
            if mode == AIMode.HELP_PROBLEM:
                return f"Реши пошагово математическую задачу, объясняя каждый шаг на русском языке. Используй Markdown форматирование: **Шаг 1**, **Шаг 2** для заголовков, `формулы` в обратных кавычках для математических выражений. НЕ используй LaTeX ($$ или $ символы)! Пиши формулы простым текстом. Задача: {text}"
            if mode == AIMode.EXPLAIN:
                return f"Подробно объясни математическую тему на русском языке. Используй Markdown форматирование: **заголовки** для разделов, *курсив* для важных терминов, `формулы` в обратных кавычках для математических выражений. НЕ используй LaTeX ($$ или $ символы)! Пиши формулы простым текстом. Включи определения, основные формулы, примеры и практическое применение. Тема: {text}"
            if mode == AIMode.TIPS:
                return f"Дай 5-7 практических советов по изучению темы. Используй Markdown форматирование: **жирный текст** для заголовков советов, нумерованный список. НЕ используй LaTeX ($$ или $ символы)! Советы должны быть конкретными и применимыми. Тема: {text}"
            if mode == AIMode.PLAN:
                return f"Составь пошаговый план изучения темы на 2-3 недели. Используй Markdown форматирование: **Неделя 1**, **День 1** для заголовков. НЕ используй LaTeX ($$ или $ символы)! Разбей на ежедневные задачи с указанием времени. Тема: {text}"
            if mode == AIMode.CHECK_SOLUTION:
                return (
                    "Проанализируй решение математической задачи. Используй Markdown форматирование: "
                    "**Анализ решения**, **Ошибки** (если есть), **Правильное решение** для заголовков, "
                    "`формулы` в обратных кавычках для математических выражений. НЕ используй LaTeX ($$ или $ символы)! "
                    "Проверь правильность каждого шага, укажи ошибки и предложи корректное решение на русском языке. "
                    f"Решение для проверки: {text}"
                )
            if mode == AIMode.PRACTICE:
                return (
                    "Создай 3 практические задачи по указанной теме с разным уровнем сложности. "
                    "Используй Markdown форматирование: **Задача 1** (легкая), **Задача 2** (средняя), **Задача 3** (сложная) для заголовков, "
                    "`формулы` в обратных кавычках для математических выражений. НЕ используй LaTeX ($$ или $ символы)! "
                    "Затем отдельно раздел **Ответы** с нумерованным списком. "
                    f"Тема: {text}"
                )
            if mode == AIMode.GENERATE_TASK:
                return (
                    "Сгенерируй одну математическую задачу средней сложности по указанной теме. "
                    "Формат ответа: только условие задачи без решения и ответа. "
                    "Начни с 'Задача: ' и напиши только условие. "
                    f"Тема: {text}"
                )
            
            # Специфические режимы для разделов алгебры
            if mode == AIMode.COMPUTATIONAL_SKILLS:
                return (
                    "Объясни вычислительные навыки в алгебре. Включи следующие темы: "
                    "**Действия с дробями** (обыкновенные и десятичные), **работа с процентами**, "
                    "**вычисления со степенями и корнями**, **порядок действий**. "
                    "Используй Markdown форматирование и приведи 2-3 примера для каждой темы. "
                    "НЕ используй LaTeX ($$ или $ символы)!"
                )
            
            if mode == AIMode.EXPRESSION_VALUE:
                return (
                    "Объясни как находить значение алгебраических выражений. Включи: "
                    "**подстановку значений переменных**, **упрощение выражений перед подстановкой**, "
                    "**работу со скобками**, **приведение подобных слагаемых**. "
                    "Покажи пошаговые примеры вычислений. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)!"
                )
            
            if mode == AIMode.FORMULAS_WORK:
                return (
                    "Объясни работу с алгебраическими формулами. Включи: "
                    "**вывод формул из условий задач**, **преобразование формул**, "
                    "**выражение одной переменной через другие**, **применение готовых формул**. "
                    "Приведи примеры из физики и геометрии. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)!"
                )
            
            if mode == AIMode.SHORTHAND_FORMULAS:
                return (
                    "Объясни формулы сокращённого умножения. Включи все основные формулы: "
                    "**квадрат суммы и разности**, **разность квадратов**, **куб суммы и разности**, "
                    "**сумма и разность кубов**. Для каждой формулы приведи: "
                    "формулировку, запись в общем виде, 2-3 примера применения. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)!"
                )
            
            if mode == AIMode.EQUATIONS:
                return (
                    "Объясни решение алгебраических уравнений. Включи: "
                    "**линейные уравнения** (ax + b = 0), **квадратные уравнения** (через дискриминант и теорему Виета), "
                    "**неполные квадратные уравнения**, **биквадратные уравнения**, **уравнения высших степеней**. "
                    "Для каждого типа приведи алгоритм решения и примеры. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)!"
                )
            
            if mode == AIMode.INEQUALITIES:
                return (
                    "Объясни решение алгебраических неравенств. Включи: "
                    "**линейные неравенства**, **квадратные неравенства** (метод интервалов), "
                    "**системы неравенств**, **неравенства с модулем**. "
                    "Объясни как работать с числовой прямой и интервалами. "
                    "Приведи пошаговые примеры. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)!"
                )
            
            if mode == AIMode.GRAPHS:
                return (
                    "Объясни построение и анализ графиков функций. Включи: "
                    "**линейные функции** (y = kx + b), **квадратичные функции** (парабола), "
                    "**гипербола** (y = k/x), **модуль** (y = |x|), **корень** (y = √x). "
                    "Для каждой функции объясни: область определения, множество значений, "
                    "особые точки, поведение графика. Приведи примеры построения. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)! "
                    "ВАЖНО: В конце добавь [IMAGE:multiple_graphs] для сравнительного графика всех функций."
                )
            
            if mode == AIMode.TRIGONOMETRY:
                return (
                    "Объясни основы тригонометрии. Включи: "
                    "**определения синуса, косинуса, тангенса**, **тригонометрическая окружность**, "
                    "**основные тригонометрические тождества**, **формулы приведения**, "
                    "**простейшие тригонометрические уравнения**. "
                    "Объясни связь с прямоугольным треугольником. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)! "
                    "ВАЖНО: В начале объяснения добавь [IMAGE:trigonometric_circle] для тригонометрической окружности. "
                    "После объяснения функций добавь [IMAGE:trigonometric_functions] для графиков функций."
                )
            
            if mode == AIMode.PROBABILITY:
                return (
                    "Объясни основы теории вероятностей. Включи: "
                    "**определение вероятности**, **классическое определение вероятности**, "
                    "**формула вероятности** (P = m/n), **сложение и умножение вероятностей**, "
                    "**условная вероятность**, **независимые события**. "
                    "Приведи примеры с монетами, игральными костями, картами. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)!"
                )
            
            # === ГЕОМЕТРИЧЕСКИЕ РЕЖИМЫ ===
            
            if mode == AIMode.TRIANGLES:
                return (
                    "Объясни всё о треугольниках. Включи: "
                    "**классификация по сторонам** (равносторонний, равнобедренный, разносторонний), "
                    "**классификация по углам** (прямоугольный, остроугольный, тупоугольный), "
                    "**свойства треугольников**, **сумма углов треугольника**, "
                    "**теорема Пифагора**, **медианы, биссектрисы, высоты**, "
                    "**площадь треугольника** (разные способы), **периметр треугольника**. "
                    "Приведи конкретные примеры и формулы. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)! "
                    "ВАЖНО: В начале добавь [IMAGE:triangles_diagram] для визуализации типов треугольников."
                )
            
            if mode == AIMode.QUADRILATERALS:
                return (
                    "Объясни четырёхугольники и их свойства. Включи: "
                    "**квадрат** (свойства и формулы), **прямоугольник** (свойства и формулы), "
                    "**ромб** (свойства и формулы), **параллелограмм** (свойства и формулы), "
                    "**трапеция** (свойства и формулы), **произвольный четырёхугольник**, "
                    "**площади четырёхугольников**, **периметры четырёхугольников**, "
                    "**диагонали и их свойства**, **углы четырёхугольников**. "
                    "Приведи конкретные примеры вычислений. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)! "
                    "ВАЖНО: В начале добавь [IMAGE:quadrilaterals_diagram] для визуализации типов четырёхугольников."
                )
            
            if mode == AIMode.CIRCLES:
                return (
                    "Объясни окружность и круг. Включи: "
                    "**определения окружности и круга**, **центр, радиус, диаметр**, "
                    "**хорда, секущая, касательная**, **дуга и сектор**, "
                    "**длина окружности** (C = 2πr), **площадь круга** (S = πr²), "
                    "**свойства касательных**, **свойства хорд**, **углы в окружности**, "
                    "**вписанные и центральные углы**, **вписанные и описанные многоугольники**. "
                    "Приведи конкретные примеры вычислений. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)! "
                    "ВАЖНО: В начале добавь [IMAGE:circle_diagram] для визуализации элементов окружности."
                )
            
            if mode == AIMode.AREAS_VOLUMES:
                return (
                    "Объясни вычисление площадей и объёмов. Включи: "
                    "**ПЛОЩАДИ**: квадрат (S = a²), прямоугольник (S = ab), треугольник (S = ½ah), "
                    "круг (S = πr²), параллелограмм, ромб, трапеция. "
                    "**ОБЪЁМЫ**: куб (V = a³), параллелепипед (V = abc), цилиндр (V = πr²h), "
                    "конус (V = ⅓πr²h), сфера (V = ⁴⁄₃πr³), пирамида (V = ⅓Sоснh). "
                    "**Единицы измерения**, **примеры задач**, **практическое применение**. "
                    "Приведи пошаговые решения конкретных задач. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)! "
                    "ВАЖНО: В начале добавь [IMAGE:areas_volumes_diagram] для визуализации формул."
                )
            
            if mode == AIMode.COORDINATE_GEOMETRY:
                return (
                    "Объясни координатную геометрию. Включи: "
                    "**координатная плоскость** (оси x и y, координаты точек), "
                    "**расстояние между точками** (формула d = √[(x₂-x₁)² + (y₂-y₁)²]), "
                    "**середина отрезка** (формула), **уравнение прямой** (y = kx + b), "
                    "**уравнение окружности** ((x-a)² + (y-b)² = r²), "
                    "**уравнение параболы** (y = ax² + bx + c), **построение графиков**, "
                    "**пересечение прямых**, **расстояние от точки до прямой**. "
                    "Приведи конкретные примеры построения и вычислений. "
                    "Используй Markdown форматирование. НЕ используй LaTeX ($$ или $ символы)! "
                    "ВАЖНО: В начале добавь [IMAGE:coordinate_geometry_diagram] для визуализации координатной плоскости."
                )
            
            return text
        except Exception as e:
            print(f"Ошибка формирования промпта в LLM: {e}")
            return text

    @staticmethod
    def _sanitize_generated_task(raw_text: str) -> str:
        """Возвращает из ответа LLM только условие задачи.

        - Если есть строка, начинающаяся с 'Задача:', берём её и последующие строки до пустой строки.
        - Удаляем блоки, начинающиеся с 'Решение', 'Пример', 'Вид', 'Answer', 'Program', 'Программа', 'Ответ'.
        - Если 'Задача:' не найдено — берём первую содержательную строку и добавляем префикс 'Задача: '.
        - Обрезаем до 3–4 строк максимум, чтобы избежать лишнего текста.
        """
        try:
            if not isinstance(raw_text, str):
                return "Не удалось сгенерировать задачу"
            lines = [ln.strip() for ln in raw_text.strip().splitlines()]
            drop_prefixes = (
                "решение", "пример", "вид", "answer", "program", "программа", "ответ"
            )
            filtered = []
            skip = False
            for ln in lines:
                low = ln.lower()
                if any(low.startswith(pfx) for pfx in drop_prefixes):
                    skip = True
                if skip:
                    if ln == "":
                        skip = False
                    continue
                filtered.append(ln)

            start_idx = next((i for i, ln in enumerate(filtered) if ln.lower().startswith("задача:")), None)
            if start_idx is not None:
                result_block = []
                for ln in filtered[start_idx:]:
                    if ln == "":
                        break
                    result_block.append(ln)
                result_block = result_block[:4]
                return "\n".join(result_block) if result_block else filtered[start_idx]

            first = next((ln for ln in filtered if ln), "")
            if not first:
                return "Не удалось сгенерировать задачу"
            if not first.lower().startswith("задача:"):
                first = f"Задача: {first}"
            return first
        except Exception as e:
            print(f"Ошибка санитизации текста задачи в LLM: {e}")
            return "Не удалось сгенерировать задачу"

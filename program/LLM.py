"""Обёртка над локальной LLM (Ollama) для ответов и объяснений.

Поддерживает три типа ответов: вычисление, объяснение и краткий ответ.
Подключение выполняется к локальной службе Ollama.
"""

from langchain_ollama import OllamaLLM 
import re
from enum import Enum, auto
from enums import AIMode

# Константы локального подключения к Ollama
DEFAULT_MODEL = "phi"

class ResponseType(Enum):
    """Тип запрашиваемого ответа от модели."""
    CALCULATION = auto()  # Только числовой ответ
    EXPLANATION = auto()  # Развернутое объяснение
    CONCISE = auto()      # Краткий ответ

class LLM:
    """Клиент локальной LLM (Ollama) с ролью учителя математики.

    Предоставляет высокоуровневые методы:
    - calculate: получить только числовой ответ;
    - explain: подробное объяснение темы;
    - ask: краткий ответ по существу.
    """
    ROLES = {
        "math teacher": {
            "base": "You are a helpful math teacher.",
            "calculation": "Provide ONLY the final numerical answer without ANY explanations or additional text. Just the number.",
            "explanation": "Explain the concept in detail with examples, step by step.",
            "concise": "Give a brief and clear answer to the question."
        }
    }

    def __init__(self):
        """Инициализирует подключение к локальной Ollama и состояния подсказки."""
        self.model = OllamaLLM(model=DEFAULT_MODEL)

        self.role = ""
        self.task = ""
        self.prompt = ""
        self.response_type = ResponseType.EXPLANATION  # По умолчанию объяснение

    def set_role(self, role: str) -> None:
        """Устанавливает роль подсказки (поддерживается только 'math teacher')."""
        if role not in self.ROLES:
            raise ValueError("Unsupported model role selected")
        self.role = self.ROLES[role]["base"]

    def set_response_type(self, response_type: ResponseType) -> None:
        """Меняет тип ответа модели (влияет на формирование промпта)."""
        self.response_type = response_type

    def calculate(self, expression: str) -> str:
        """Возвращает только числовой результат выражения, без пояснений."""
        self.response_type = ResponseType.CALCULATION
        expression = self._normalize_expression(expression)
        self.task = f"Calculate: {expression}"
        self._update_prompt()
        return self.request()

    def explain(self, topic: str) -> str:
        """Пишет развернутое объяснение темы с примерами и шагами."""
        self.response_type = ResponseType.EXPLANATION
        self.task = f"Explain: {topic}"
        self._update_prompt()
        return self.request()

    def ask(self, question: str) -> str:
        """Даёт краткий ответ по существу на вопрос.

        Если передан уже сформированный промпт (как в AI-режимах), он будет
        использован без добавления префикса "Answer:" для сохранения точных
        инструкций.
        """
        self.response_type = ResponseType.CONCISE
        # Используем текст как есть, без жёсткого префикса, чтобы не ломать формат
        self.task = question
        self._update_prompt()
        return self.request()

    def _update_prompt(self):
        """Формирует промпт на основе типа ответа и выбранной роли."""
        if self.response_type == ResponseType.CALCULATION:
            instruction = self.ROLES["math teacher"]["calculation"]
        elif self.response_type == ResponseType.EXPLANATION:
            instruction = self.ROLES["math teacher"]["explanation"]
        else:
            instruction = self.ROLES["math teacher"]["concise"]
        
        self.prompt = f"{self.role} {instruction} {self.task}"

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

    def request(self) -> str:
        """Отправляет промпт в модель и возвращает ответ."""

        response_text = self.model.invoke(self.prompt)

        # Для расчетов извлекаем только число
        if self.response_type == ResponseType.CALCULATION:
            return self._extract_number(response_text)
            
        return response_text

    def _extract_number(self, text: str) -> str:
        """Извлекает число из текста ответа"""
        matches = re.findall(r"-?\d+\.?\d*", text)
        return matches[0] if matches else "Could not extract number"

    # ===== High-level AI helper for app modes =====
    def respond(self, mode: AIMode | None, user_text: str) -> str:
        """Формирует промпт по режиму и возвращает ответ модели.

        Для режима GENERATE_TASK дополнительно применяется санитизация,
        чтобы вернуть только условие задачи.
        """
        try:
            prompt = self._build_prompt(mode, user_text)
            answer = self.ask(prompt)
            if mode == AIMode.GENERATE_TASK:
                return self._sanitize_generated_task(answer)
            return answer
        except Exception as e:
            print(f"Ошибка LLM.respond: {e}")
            return "Произошла ошибка при обработке запроса AI"

    @staticmethod
    def _build_prompt(mode: AIMode | None, text: str) -> str:
        """Создаёт промпт к LLM на основе выбранного режима AI."""
        try:
            if mode == AIMode.HELP_PROBLEM:
                return f"Реши пошагово задачу, объясняя ход решения на русском языке: {text}"
            if mode == AIMode.EXPLAIN:
                return f"Подробно объясни тему на русском языке с примерами: {text}"
            if mode == AIMode.TIPS:
                return f"Дай краткие практические советы по теме: {text}"
            if mode == AIMode.PLAN:
                return f"Составь краткий, понятный план обучения по теме с разбивкой по дням/неделям: {text}"
            if mode == AIMode.CHECK_SOLUTION:
                return (
                    "Проанализируй решение задачи. Укажи ошибки, если есть, и покажи корректное решение. "
                    f"Текст: {text}"
                )
            if mode == AIMode.PRACTICE:
                return (
                    "Сгенерируй 5 практических задач по теме с ответами в конце. Формат: Задача 1, ... Ответы:. "
                    f"Тема: {text}"
                )
            if mode == AIMode.GENERATE_TASK:
                return (
                    "Сгенерируй ОДНУ математическую задачу по теме на русском языке. "
                    "Только условие БЕЗ решения, БЕЗ ответа, БЕЗ примеров и пояснений. "
                    "ВЫВЕДИ ТОЛЬКО ОДНУ строку в формате: 'Задача: ...' и НИЧЕГО больше. "
                    f"Тема: {text}"
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

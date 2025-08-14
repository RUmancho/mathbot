"""Обёртка над локальной LLM (Ollama) для ответов и объяснений.

Поддерживает три типа ответов: вычисление, объяснение и краткий ответ.
Подключение выполняется к локальной службе Ollama.
"""

from langchain_ollama import OllamaLLM 
import re
from enum import Enum, auto

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
        """Даёт краткий ответ по существу на вопрос."""
        self.response_type = ResponseType.CONCISE
        self.task = f"Answer: {question}"
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

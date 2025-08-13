from langchain_ollama import OllamaLLM 
import re
from enum import Enum, auto

# Константы локального подключения к Ollama
DEFAULT_MODEL = "phi"

class ResponseType(Enum):
    CALCULATION = auto()  # Только числовой ответ
    EXPLANATION = auto()  # Развернутое объяснение
    CONCISE = auto()      # Краткий ответ


class LLM:
    ROLES = {
        "math teacher": {
            "base": "You are a helpful math teacher.",
            "calculation": "Provide ONLY the final numerical answer without ANY explanations or additional text. Just the number.",
            "explanation": "Explain the concept in detail with examples, step by step.",
            "concise": "Give a brief and clear answer to the question."
        }
    }

    def __init__(self):
        self.model = OllamaLLM(model=DEFAULT_MODEL)

        self.role = ""
        self.task = ""
        self.prompt = ""
        self.response_type = ResponseType.EXPLANATION  # По умолчанию объяснение

    def set_role(self, role: str) -> None:
        if role not in self.ROLES:
            raise ValueError("Unsupported model role selected")
        self.role = self.ROLES[role]["base"]

    def set_response_type(self, response_type: ResponseType) -> None:
        self.response_type = response_type

    def calculate(self, expression: str) -> str:
        """Для математических вычислений"""
        self.response_type = ResponseType.CALCULATION
        expression = self._normalize_expression(expression)
        self.task = f"Calculate: {expression}"
        self._update_prompt()
        return self.request()

    def explain(self, topic: str) -> str:
        """Для объяснения концепций"""
        self.response_type = ResponseType.EXPLANATION
        self.task = f"Explain: {topic}"
        self._update_prompt()
        return self.request()

    def ask(self, question: str) -> str:
        """Для кратких ответов на вопросы"""
        self.response_type = ResponseType.CONCISE
        self.task = f"Answer: {question}"
        self._update_prompt()
        return self.request()

    def _update_prompt(self):
        """Формируем промпт в зависимости от типа ответа"""
        if self.response_type == ResponseType.CALCULATION:
            instruction = self.ROLES["math teacher"]["calculation"]
        elif self.response_type == ResponseType.EXPLANATION:
            instruction = self.ROLES["math teacher"]["explanation"]
        else:
            instruction = self.ROLES["math teacher"]["concise"]
        
        self.prompt = f"{self.role} {instruction} {self.task}"

    def _normalize_expression(self, expr: str) -> str:
        """Преобразуем текстовые описания в математические выражения"""
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
        # Если модель не инициализирована — сообщаем об ошибке подключению
        if self.model is None:
            return (
                "AI недоступен: не удалось установить соединение с локальной LLM. "
                "Проверьте, запущен ли Ollama (ollama serve) и доступна ли модель."
            )
        try:
            response_text = self.model.invoke(self.prompt)
        except Exception as e:
            print(f"Ошибка запроса к LLM: {e}")
            return (
                "AI недоступен: ошибка подключения к LLM. "
                "Убедитесь, что Ollama запущен и доступен."
            )
        
        # Для расчетов извлекаем только число
        if self.response_type == ResponseType.CALCULATION:
            return self._extract_number(response_text)
        return response_text

    def _extract_number(self, text: str) -> str:
        """Извлекает число из текста ответа"""
        matches = re.findall(r"-?\d+\.?\d*", text)
        return matches[0] if matches else "Could not extract number"

phi_llm = LLM()

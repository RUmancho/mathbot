from langchain_ollama import OllamaLLM 
import re

class LLM:
    ROLES = {
        "math teacher": "You are a helpful math assistant. Your task is to provide only the final numerical answer without any explanations or additional text. Just return the number."
    }

    def __init__(self):
        self.model = OllamaLLM(model="phi")
        self.role = ""
        self.task = ""
        self.prompt = ""

    def set_role(self, role: str) -> str:
        if role not in self.ROLES:
            raise ValueError("Unsupported model role selected")
        self.role = self.ROLES[role]
        self._update_prompt()
        return self.prompt

    def calculate(self, expression) -> str:
        # Преобразуем текстовое описание в математическое выражение
        expression = self._normalize_expression(expression)
        self.task = f" calculate: {expression}. Return only the number, nothing else."
        self._update_prompt()
        return self.prompt

    def _normalize_expression(self, expr: str) -> str:
        """Преобразует текстовые описания в математические выражения"""
        expr = expr.lower().strip()
        expr = expr.replace("squared", "^2")
        expr = expr.replace("cubed", "^3")
        expr = expr.replace("to the power of", "^")
        return expr

    def _extract_number(self, text: str) -> str:
        """Извлекает число из текста ответа"""
        # Ищем числа, включая десятичные и отрицательные
        matches = re.findall(r"-?\d+\.?\d*", text)
        return matches[0] if matches else text

    def _update_prompt(self):
        self.prompt = f"{self.role}{self.task}"

    def request(self) -> str:
        response = self.model.invoke(self.prompt)
        # Извлекаем только числовой ответ
        return self._extract_number(response)

# Пример использования
model = LLM()
model.set_role("math teacher")
model.calculate("10 squared")  # Теперь вернёт только "100"
compute = model.request()
print(compute)  # Выведет: 100
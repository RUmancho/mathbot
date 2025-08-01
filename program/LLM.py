from langchain_ollama import OllamaLLM 

class LLM:
    ROLES = {
        "math teacher": "You are a school math teacher. Your task is to"
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

    def how_to_solve(self, topic) -> str:
        self.task = f" explain to a student, briefly, simply and without complex terms, step by step, how to solve {topic}."
        self._update_prompt()
        return self.prompt

    def ask_a_question(self, question) -> str:
        self.task = f" answer the question: {question}"
        self._update_prompt()
        return self.prompt
    
    def calculate(self, expression) -> str:
        self.task = f" calculate the following expression: {expression}. Provide only the final numerical answer without any additional text."
        self._update_prompt()
        return self.prompt

    def _update_prompt(self):
        self.prompt = f"{self.role}{self.task}"

    def request(self) -> str:
        response = self.model.invoke(self.prompt)
        return response

# Пример использования
model = LLM()
model.set_role("math teacher")
model.calculate("10 squared")  # Лучше использовать математическое выражение
print(model.prompt) 
compute = model.request()
print(compute)
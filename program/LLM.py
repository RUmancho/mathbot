from langchain_ollama import OllamaLLM 

class LLM:
    ROLES = {
        "math teacher" : "you are a school math teacher and you need to "
    }

    def __init__(self):
        self.model = OllamaLLM(model="phi")

        self.role = ""
        self.task = ""
        self.prompt = f""

    def set_role(self, role: str) -> str:
        if role not in self.ROLES:
            raise "unsupported model role selected"
        self.role = self.ROLES[role]
        self.prompt = f"{self.role} {self.task}"
        return self.prompt

    def how_to_solve(self, topic) -> str:
        self.task = f"explain to a student, briefly, simply and without complex terms, step by step, how to solve {topic}"
        self.prompt = f"{self.role}{self.task}"
        return self.prompt

    def ask_a_question(self, question):
        self.task = f"answer the question: {question}"
        self.prompt = f"{self.role}{self.task}"
        return self.prompt
    
    def calculate(self, expression):
        self.task = f"calculate {expression}. The answer must contain only a number."
        self.prompt = f"{self.role}{self.task}"
        return self.prompt

    def request(self) -> str:
        response = self.model.invoke(self.prompt)
        return response

model = LLM()
model.set_role("math teacher")
model.calculate("what is ten squared?")
print(model.prompt) 
compute = model.request()
print(compute)
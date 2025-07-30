from typing import Optional
from utils import ChatOpenAI
from langchain.prompts import PromptTemplate
import langchain.memory
import config

class LLM:
    def __init__(self):
        """Initialize the LLM with model and memory."""
        self.model = ChatOpenAI(temperature=0.0, course_api_key=config.LLM_API_KEY)
        self.memory = langchain.memory.ConversationSummaryBufferMemory(llm=self.model)

    def clear_memory(self) -> None:
        """Clear the conversation memory."""
        self.memory.clear()

    def load_chat(self, input_text: str, output_text: str) -> None:
        self.memory.save_context({"input": input_text}, {"output": output_text})

    def request(self, question: str, context: Optional[str] = None, answer: Optional[str] = None) -> str:
        template_request = """
        {history}
        question: {question}
        context: {context}
        answer: {answer}
        """

        request_template = PromptTemplate(
            input_variables=["history", "question", "context", "answer"],
            template=template_request
        )

        history = self.memory.load_memory_variables({})['history']

        prompt = request_template.format(
            history=history,
            question=question,
            context=context or "",
            answer=answer or ""
        )
        
        response = self.model.invoke(prompt).content
        self.load_chat(question, response)

        return response
    
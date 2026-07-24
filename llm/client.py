import ollama


class LLMClient:

    def __init__(self, model="tinyllama"):
        self.model = model

    def ask(self, prompt):

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response["message"]["content"].strip()
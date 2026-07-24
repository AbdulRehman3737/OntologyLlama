from retriever.formatter import FactFormatter


class PromptBuilder:

    @staticmethod
    def build(facts, question):

        pretty = FactFormatter.pretty(facts)

        prompt = (
            "You are a biomedical assistant.\n"
            "Answer ONLY using the knowledge below.\n"
            "Do not use outside knowledge.\n"
            "If the answer is not present, reply exactly:\n"
            "I don't know based on the provided knowledge.\n\n"
            "=== KNOWLEDGE ===\n"
        )

        for key, value in pretty.items():

            prompt += f"{key}: "

            if isinstance(value, list):
                prompt += ", ".join(value)
            else:
                prompt += str(value)

            prompt += "\n"

        prompt += (
            "\n=== QUESTION ===\n"
            f"{question}\n\n"
            "=== ANSWER ===\n"
        )

        return prompt
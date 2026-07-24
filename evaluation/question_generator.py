import csv

from retriever.constants import QUESTION_TEMPLATES


class QuestionGenerator:

    def __init__(self, retriever):
        self.retriever = retriever

    def generate(self):

        questions = []
        question_id = 1
        
        diseases = self.retriever.get_all_diseases()

        for disease in diseases:

            facts = self.retriever.get_facts(disease)

            for property_name, values in facts.items():

                if property_name == "Disease":
                    continue

                template = QUESTION_TEMPLATES.get(property_name)

                if template is None:
                    continue

                question = template.format(
                    disease=disease
                )

                answer = "; ".join(values)

                questions.append({
                    "id": question_id,
                    "disease": disease,
                    "property": property_name,
                    "question": question,
                    "answer": answer
                })
                
                question_id += 1
                
        return questions

    def save_csv(self, filename):

        questions = self.generate()

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "id",
                    "disease",
                    "property",
                    "question",
                    "answer"
                ]
            )

            writer.writeheader()

            writer.writerows(questions)

        print(f"Generated {len(questions)} questions.")
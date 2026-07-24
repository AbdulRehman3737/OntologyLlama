import csv
import os

from llm.client import LLMClient


class BaseEvaluator:

    def __init__(
        self,
        questions_file,
        output_file,
        model="tinyllama"
    ):
        self.questions_file = questions_file
        self.output_file = output_file
        self.llm = LLMClient(model)

    def build_prompt(self, row):
        raise NotImplementedError()

    def completed_ids(self):

        if not os.path.exists(self.output_file):
            return set()

        completed = set()

        with open(
            self.output_file,
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:
                completed.add(row["id"])

        return completed

    def total_questions(self):

        with open(
            self.questions_file,
            newline="",
            encoding="utf-8"
        ) as file:

            return sum(1 for _ in file) - 1

    def run(self):

        completed = self.completed_ids()

        total = self.total_questions()

        file_exists = os.path.exists(self.output_file)

        with open(
            self.output_file,
            "a",
            newline="",
            encoding="utf-8"
        ) as outfile:

            writer = csv.DictWriter(
                outfile,
                fieldnames=[
                    "id",
                    "model",
                    "disease",
                    "property",
                    "question",
                    "ground_truth",
                    "prompt",
                    "llm_answer",
                ]
            )

            if not file_exists:
                writer.writeheader()

            with open(
                self.questions_file,
                newline="",
                encoding="utf-8"
            ) as infile:

                reader = csv.DictReader(infile)

                for row in reader:

                    if row["id"] in completed:
                        continue

                    prompt = self.build_prompt(row)

                    print(
                        f"[{row['id']}/{total}] {row['question']}"
                    )

                    answer = self.llm.ask(prompt)

                    writer.writerow({
                        "id": row["id"],
                        "model": self.llm.model,
                        "disease": row["disease"],
                        "property": row["property"],
                        "question": row["question"],
                        "ground_truth": row["answer"],
                        "prompt": prompt,
                        "llm_answer": answer,
                    })

                    outfile.flush()

                    print("✓ Saved")
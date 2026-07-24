from evaluation.base_evaluator import BaseEvaluator

from llm.prompt_builder import PromptBuilder

from retriever.loader import OntologyLoader
from retriever.disease import DiseaseRetriever


class OntologyEvaluator(BaseEvaluator):

    def __init__(
        self,
        questions_file,
        output_file,
        ontology_path,
        model="tinyllama"
    ):

        super().__init__(
            questions_file,
            output_file,
            model
        )

        loader = OntologyLoader(ontology_path)

        ontology = loader.load()

        self.retriever = DiseaseRetriever(ontology)

    def build_prompt(self, row):

        facts = self.retriever.get_facts(
            row["disease"]
        )

        return PromptBuilder.build(
            facts,
            row["question"]
        )
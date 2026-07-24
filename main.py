from retriever.loader import OntologyLoader
from retriever.disease import DiseaseRetriever
from retriever.loader import OntologyLoader
from evaluation.question_generator import QuestionGenerator
from evaluation.baseline import BaselineEvaluator
from evaluation.ontology_evaluator import OntologyEvaluator

loader = OntologyLoader("ontology/rare_genetic_diseases_ontology.owl")

ontology = loader.load()

print("Loaded ontology!")


loader = OntologyLoader("ontology/rare_genetic_diseases_ontology.owl")

ontology = loader.load()

retriever = DiseaseRetriever(ontology)

# Generate questions and save to CSV
# generator = QuestionGenerator(retriever)

# generator.save_csv("evaluation/questions.csv")

# Run baseline evaluation and save results to CSV
# baseline = BaselineEvaluator(
#     questions_file="evaluation/questions.csv",
#     output_file="results/baseline_answers.csv",
#     model="tinyllama"
# )

# baseline.run()



ontology = OntologyEvaluator(
    questions_file="evaluation/questions.csv",
    output_file="results/ontology_answers.csv",
    ontology_path="ontology/rare_genetic_diseases_ontology.owl"
)

ontology.run()
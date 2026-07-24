# load the ontology
from owlready2 import get_ontology


class OntologyLoader:
    def __init__(self, path):
        self.path = path
        self.ontology = None

    def load(self):
        self.ontology = get_ontology(self.path).load()
        return self.ontology
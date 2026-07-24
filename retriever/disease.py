from retriever.constants import Property


class DiseaseRetriever:

    def __init__(self, ontology):
        self.ontology = ontology

    def find(self, disease_name):

        for disease in self.ontology.Disease.instances():

            if (
                hasattr(disease, "label")
                and len(disease.label)
                and disease.label.first().lower() == disease_name.lower()
            ):
                return disease

        return None

    def format_value(self, value):

        if isinstance(value, str):
            return value

        if hasattr(value, "label") and len(value.label):
            return value.label.first()

        if hasattr(value, "name"):
            return value.name

        return str(value)

    def get_facts(self, disease_name):

        disease = self.find(disease_name)

        if disease is None:
            return None

        facts = {}

        facts["Disease"] = disease.label.first()

        for prop in disease.get_properties():

            if prop.name == "label":
                continue

            values = []

            for value in prop[disease]:
                values.append(self.format_value(value))

            # RAW ontology property name
            facts[prop.name] = values

        return facts

    def get_all_diseases(self):

        diseases = []

        for disease in self.ontology.Disease.instances():

            diseases.append(disease.label.first())

        return diseases
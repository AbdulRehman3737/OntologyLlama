from enum import Enum


class Property(str, Enum):
    CAUSATIVE_GENE = "hasCausativeGene"
    DEFICIENT_ENZYME = "hasDeficientEnzyme"
    INHERITANCE_PATTERN = "hasInheritancePattern"
    TREATMENT = "treatedWith"
    SYMPTOM = "hasSymptom"
    ACCUMULATED_METABOLITE = "accumulatesMetabolite"


PROPERTY_LABELS = {
    Property.CAUSATIVE_GENE.value: "Causative Gene",
    Property.DEFICIENT_ENZYME.value: "Deficient Enzyme",
    Property.INHERITANCE_PATTERN.value: "Inheritance Pattern",
    Property.TREATMENT.value: "Treatment",
    Property.SYMPTOM.value: "Symptoms",
    Property.ACCUMULATED_METABOLITE.value: "Accumulated Metabolite",
}


QUESTION_TEMPLATES = {
    Property.CAUSATIVE_GENE.value:
        "Which gene causes {disease}?",

    Property.DEFICIENT_ENZYME.value:
        "Which enzyme is deficient in {disease}?",

    Property.INHERITANCE_PATTERN.value:
        "What is the inheritance pattern of {disease}?",

    Property.TREATMENT.value:
        "How is {disease} treated?",

    Property.SYMPTOM.value:
        "What symptoms are associated with {disease}?",

    Property.ACCUMULATED_METABOLITE.value:
        "Which metabolite accumulates in {disease}?",
}
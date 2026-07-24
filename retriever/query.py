def print_classes(ontology):

    for cls in ontology.classes():
        print(cls.name)
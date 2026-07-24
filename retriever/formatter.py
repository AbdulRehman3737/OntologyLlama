from retriever.constants import PROPERTY_LABELS


class FactFormatter:

    @staticmethod
    def pretty(facts):

        formatted = {}

        for key, value in facts.items():

            if key == "Disease":
                formatted[key] = value
                continue

            label = PROPERTY_LABELS.get(key, key)

            formatted[label] = value

        return formatted
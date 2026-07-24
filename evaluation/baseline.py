from evaluation.base_evaluator import BaseEvaluator


class BaselineEvaluator(BaseEvaluator):

    def build_prompt(self, row):
        return row["question"]
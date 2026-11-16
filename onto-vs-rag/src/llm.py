"""Single LLM wrapper shared by every arm, so prompts and decoding are identical."""
from __future__ import annotations

import time

import ollama

MODEL = "tinyllama"
# repeat_penalty 1.0: Ollama's default (1.1) penalises tokens already in the prompt, which makes
# the model misspell entity names it must copy from the context and unfairly hurts context arms.
OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 160, "num_ctx": 2048, "repeat_penalty": 1.0}

SYSTEM = ("You are a medical genetics assistant. Answer the question briefly and directly. "
          "If you do not know the answer, say \"I don't know\".")


def build_prompt(question: str, context: str | None) -> str:
    if context is None:
        return f"Question: {question}\nAnswer:"
    return (f"{context}\n\nUsing the information above, answer the question. "
            f"If the information does not contain the answer, say \"I don't know\".\n"
            f"Question: {question}\nAnswer:")


def ask(question: str, context: str | None = None) -> dict:
    prompt = build_prompt(question, context)
    t0 = time.perf_counter()
    r = ollama.chat(model=MODEL, messages=[{"role": "system", "content": SYSTEM},
                                           {"role": "user", "content": prompt}], options=OPTIONS)
    return {
        "text": r["message"]["content"].strip(),
        "latency_s": round(time.perf_counter() - t0, 3),
        "prompt_tokens": r.get("prompt_eval_count"),
        "completion_tokens": r.get("eval_count"),
    }

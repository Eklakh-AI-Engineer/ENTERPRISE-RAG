import json

from app.generation.openrouter import OpenRouterClient


class FaithfulnessChecker:

    def __init__(self):
        self.llm = OpenRouterClient()

    def check(self, answer: str, context: str) -> dict:

        prompt = f"""
You are a strict faithfulness evaluator for an Enterprise RAG system.

Your task is to determine whether the answer is supported by the
provided context.

================ CONTEXT ================

{context}

================ ANSWER ================

{answer}

================ RULES ================

Evaluate ONLY against the supplied context.

For every factual claim in the answer:

- SUPPORTED: The context directly supports the claim.
- UNSUPPORTED: The context does not support the claim.
- CONTRADICTED: The context conflicts with the claim.

Do not use outside knowledge.

Return ONLY valid JSON in exactly this structure:

{{
    "faithful": true,
    "score": 1.0,
    "claims": [
        {{
            "claim": "example claim",
            "status": "SUPPORTED",
            "reason": "The context explicitly supports this claim."
        }}
    ]
}}

The score must be between 0.0 and 1.0.

Set "faithful" to true only when all substantive factual
claims are SUPPORTED.

Return JSON only.
"""

        response = self.llm.generate(prompt)

        try:
            return json.loads(response)

        except json.JSONDecodeError:
            return {
                "faithful": False,
                "score": 0.0,
                "claims": [],
                "error": "LLM returned invalid JSON",
                "raw_response": response,
            }
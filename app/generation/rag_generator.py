from app.generation.openrouter import OpenRouterClient


SYSTEM_PROMPT = """
You are an enterprise RAG assistant.

Answer the user's question using ONLY the supplied context.

Rules:

1. Do not use outside knowledge.
2. Do not invent facts.
3. Every factual claim must be supported by the supplied context.
4. Cite supporting evidence using [Source N].
5. Do not cite a source that does not support the claim.
6. If the context does not contain enough information, say:
   "I don't have enough information in the provided documents to answer this."
7. Keep the answer concise but complete.
"""


class RAGGenerator:

    def __init__(self):
        self.llm = OpenRouterClient()

    def generate(self, query: str, context: str) -> str:

        prompt = f"""
{SYSTEM_PROMPT}

================ CONTEXT ================

{context}

================ USER QUESTION ================

{query}

================ INSTRUCTIONS ================

Answer the user's question using only the context above.

Use [Source N] citations for factual claims.

If the answer cannot be supported by the supplied context,
explicitly state that there is insufficient information.

Answer:
"""

        return self.llm.generate(prompt)
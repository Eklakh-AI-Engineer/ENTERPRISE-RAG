from app.generation.openrouter import OpenRouterClient


SYSTEM_PROMPT = """
You are an enterprise RAG assistant.

Answer the user's question using ONLY the supplied context.

STRICT EVIDENCE RULES:

1. Do not use outside knowledge.
2. Do not invent facts.
3. Every factual claim MUST be directly supported by the supplied context.
4. Cite the specific source that directly supports each factual claim.
5. Use citations in the exact format [Source N].
6. Place the citation immediately after the claim it supports.
7. Prefer the most specific and directly relevant source over a broader source.
8. Do not cite a source merely because it is related to the topic.
9. Do not add unnecessary citations.
10. If multiple sources support one claim, cite all necessary sources.
11. Use the minimum number of sources required to fully support the answer.
12. Never cite a source that does not support the claim.
13. If the context does not contain enough information, say:
    "I don't have enough information in the provided documents to answer this."
14. Keep the answer concise but complete.

Before answering, internally determine:

- which sources directly answer the question
- which claims each source supports
- which citations are actually necessary

Do not expose this reasoning. Output only the final answer with citations.
"""


class RAGGenerator:

    def __init__(self):
        self.llm = OpenRouterClient()

    def generate(self, query: str, context: str) -> str:

        # ---------------------------------------------------------
        # Temporary RAG diagnostics
        # ---------------------------------------------------------

        print(
            f"[RAG DEBUG] Context characters: {len(context):,}"
        )

        print(
            f"[RAG DEBUG] Estimated tokens: {len(context) // 4:,}"
        )

        # ---------------------------------------------------------
        # Build generation prompt
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Generate grounded answer
        # ---------------------------------------------------------

        return self.llm.generate(prompt)
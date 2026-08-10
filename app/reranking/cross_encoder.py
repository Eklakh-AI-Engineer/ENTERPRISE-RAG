from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    """
    Cross-encoder reranker.

    Takes retrieved candidate documents and scores each document
    against the user query using a cross-encoder model.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ):
        print(
            f"Loading cross-encoder: {model_name}"
        )

        self.model = CrossEncoder(
            model_name
        )

        print("Cross-encoder loaded successfully.")

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank retrieved documents against the query.

        The original document metadata is preserved.
        """

        if not documents:
            return []

        # -----------------------------------------------------
        # Build query-document pairs
        # -----------------------------------------------------

        pairs = []

        valid_documents = []

        for document in documents:

            text = document.get(
                "text",
                "",
            ).strip()

            if not text:
                continue

            pairs.append(
                [
                    query,
                    text,
                ]
            )

            valid_documents.append(
                document
            )

        if not pairs:
            return []

        # -----------------------------------------------------
        # Cross-encoder scoring
        # -----------------------------------------------------

        scores = self.model.predict(
            pairs
        )

        # -----------------------------------------------------
        # Attach reranking scores while preserving metadata
        # -----------------------------------------------------

        ranked = []

        for document, score in zip(
            valid_documents,
            scores,
        ):

            result = document.copy()

            result["rerank_score"] = float(
                score
            )

            # Normalize source metadata so every downstream
            # component can consistently access it.

            result["source"] = (
                result.get("source")
                or result.get("document")
                or "unknown"
            )

            result["document"] = (
                result.get("source")
                or "unknown"
            )

            ranked.append(
                result
            )

        # -----------------------------------------------------
        # Highest cross-encoder score first
        # -----------------------------------------------------

        ranked.sort(
            key=lambda item: item["rerank_score"],
            reverse=True,
        )

        return ranked[:top_k]
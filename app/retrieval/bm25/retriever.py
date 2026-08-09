import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


class BM25Retriever:

    def __init__(self):
        self.chunks = []
        self.bm25 = None

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return re.findall(
            r"\b\w+\b",
            text.lower(),
        )

    def build_index(self, chunks: list[dict]):
        if not chunks:
            raise ValueError("No chunks provided.")

        self.chunks = chunks

        tokenized_corpus = [
            self.tokenize(chunk["text"])
            for chunk in chunks
        ]

        self.bm25 = BM25Okapi(tokenized_corpus)

    def load(self, metadata_path: str):
        """
        Load chunk metadata and rebuild the BM25 index.
        """

        with open(
            metadata_path,
            "r",
            encoding="utf-8",
        ) as file:
            self.chunks = json.load(file)

        if not self.chunks:
            raise ValueError(
                "No chunks found in BM25 metadata."
            )

        tokenized_corpus = [
            self.tokenize(chunk["text"])
            for chunk in self.chunks
        ]

        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:

        if self.bm25 is None:
            raise RuntimeError(
                "BM25 index has not been built."
            )

        query_tokens = self.tokenize(query)

        scores = self.bm25.get_scores(query_tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:top_k]

        results = []

        for index in ranked_indices:
            chunk = self.chunks[index].copy()
            chunk["score"] = float(scores[index])

            results.append(chunk)

        return results

    def save(
        self,
        metadata_path: str,
    ):
        Path(metadata_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            metadata_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.chunks,
                file,
                indent=2,
                ensure_ascii=False,
            )
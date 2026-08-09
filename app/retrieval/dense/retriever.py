import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class DenseRetriever:

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks = []

    def build_index(self, chunks: list[dict]):
        if not chunks:
            raise ValueError("No chunks provided.")

        self.chunks = chunks

        texts = [chunk["text"] for chunk in chunks]

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        embeddings = embeddings.astype("float32")

        dimension = embeddings.shape[1]

        # Inner product on normalized vectors = cosine similarity
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

    def load(self, index_path: str, metadata_path: str):
        """
        Load a previously built FAISS index and its chunk metadata.
        """

        self.index = faiss.read_index(index_path)

        with open(
            metadata_path,
            "r",
            encoding="utf-8",
        ) as file:
            self.chunks = json.load(file)

        if self.index.ntotal != len(self.chunks):
            raise ValueError(
                f"Index/chunk mismatch: "
                f"{self.index.ntotal} vectors vs "
                f"{len(self.chunks)} chunks."
            )

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:

        if self.index is None:
            raise RuntimeError("Index has not been built.")

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        scores, indices = self.index.search(
            query_embedding,
            min(top_k, len(self.chunks)),
        )

        results = []

        for score, index in zip(scores[0], indices[0]):
            if index < 0:
                continue

            chunk = self.chunks[index].copy()
            chunk["score"] = float(score)

            results.append(chunk)

        return results

    def save(
        self,
        index_path: str,
        metadata_path: str,
    ):
        if self.index is None:
            raise RuntimeError("Index has not been built.")

        Path(index_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        faiss.write_index(
            self.index,
            index_path,
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
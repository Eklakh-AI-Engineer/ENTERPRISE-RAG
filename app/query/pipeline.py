from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.hybrid.retriever import HybridRetriever
from app.reranking.cross_encoder import CrossEncoderReranker
from app.generation.rag_generator import RAGGenerator
from app.query.context import build_context
from app.citations.mapper import map_citations


class QueryPipeline:

    def __init__(
        self,
        retrieval_top_k: int = 10,
        rerank_top_k: int = 5,
        candidate_k: int = 10,
    ):

        self.retrieval_top_k = retrieval_top_k
        self.rerank_top_k = rerank_top_k
        self.candidate_k = candidate_k

        print("Loading dense retriever...")

        self.dense = DenseRetriever()

        self.dense.load(
            "data/processed/dense.index",
            "data/processed/dense_metadata.json",
        )

        print("Loading BM25 retriever...")

        self.bm25 = BM25Retriever()

        self.bm25.load(
            "data/processed/bm25_metadata.json",
        )

        print("Building hybrid retriever...")

        self.hybrid = HybridRetriever(
            dense_retriever=self.dense,
            bm25_retriever=self.bm25,
        )

        print("Loading reranker...")

        self.reranker = CrossEncoderReranker()

        print("Loading RAG generator...")

        self.generator = RAGGenerator()

    def run(self, query: str):

        # ---------------------------------------------------------
        # 1. Hybrid retrieval
        # ---------------------------------------------------------

        retrieved = self.hybrid.search(
            query=query,
            top_k=self.retrieval_top_k,
            candidate_k=self.candidate_k,
        )

        # ---------------------------------------------------------
        # 2. Cross-encoder reranking
        # ---------------------------------------------------------

        reranked = self.reranker.rerank(
            query=query,
            documents=retrieved,
            top_k=self.rerank_top_k,
        )

        # ---------------------------------------------------------
        # 3. Context assembly
        # ---------------------------------------------------------

        context = build_context(
            reranked,
        )

        # ---------------------------------------------------------
        # 4. RAG generation
        # ---------------------------------------------------------

        answer = self.generator.generate(
            query=query,
            context=context,
        )

        # ---------------------------------------------------------
        # 5. Citation mapping
        # ---------------------------------------------------------

        citations = map_citations(
            answer,
            reranked,
        )

        # ---------------------------------------------------------
        # 6. Return complete pipeline result
        # ---------------------------------------------------------

        return {
            "query": query,
            "answer": answer,
            "citations": citations,
            "retrieved": reranked,
            "retrieved_count": len(retrieved),
            "reranked_count": len(reranked),
        }
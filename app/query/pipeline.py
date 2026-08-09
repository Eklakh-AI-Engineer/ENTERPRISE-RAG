from app.config.settings import settings

from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.hybrid.retriever import HybridRetriever

from app.reranking.cross_encoder import CrossEncoderReranker
from app.generation.rag_generator import RAGGenerator

from app.query.context import build_context

from app.citations.mapper import map_citations

from app.evaluation.answer_evaluator import AnswerEvaluator

from app.observability.metrics import PipelineMetrics


class QueryPipeline:

    def __init__(
        self,
        retrieval_top_k: int | None = None,
        rerank_top_k: int | None = None,
        candidate_k: int | None = None,
    ):

        self.retrieval_top_k = (
            retrieval_top_k
            if retrieval_top_k is not None
            else settings.RETRIEVAL_TOP_K
        )

        self.rerank_top_k = (
            rerank_top_k
            if rerank_top_k is not None
            else settings.RERANK_TOP_K
        )

        self.candidate_k = (
            candidate_k
            if candidate_k is not None
            else settings.CANDIDATE_K
        )

        print("Loading dense retriever...")

        self.dense = DenseRetriever(
            model_name=settings.DENSE_MODEL,
        )

        self.dense.load(
            settings.DENSE_INDEX_PATH,
            settings.DENSE_METADATA_PATH,
        )

        print("Loading BM25 retriever...")

        self.bm25 = BM25Retriever()

        self.bm25.load(
            settings.BM25_METADATA_PATH,
        )

        print("Building hybrid retriever...")

        self.hybrid = HybridRetriever(
            dense_retriever=self.dense,
            bm25_retriever=self.bm25,
        )

        print("Loading reranker...")

        self.reranker = CrossEncoderReranker(
            model_name=settings.RERANKER_MODEL,
        )

        print("Loading RAG generator...")

        self.generator = RAGGenerator()

        print("Loading answer evaluator...")

        self.evaluator = AnswerEvaluator()

    def run(self, query: str):

        metrics = PipelineMetrics()

        total_start = metrics.timer()

        # ---------------------------------------------------------
        # 1. Hybrid retrieval
        # ---------------------------------------------------------

        retrieval_start = metrics.timer()

        retrieved = self.hybrid.search(
            query=query,
            top_k=self.retrieval_top_k,
            candidate_k=self.candidate_k,
        )

        metrics.retrieval_ms = metrics.elapsed_ms(
            retrieval_start
        )

        metrics.retrieved_count = len(retrieved)

        # ---------------------------------------------------------
        # 2. Cross-encoder reranking
        # ---------------------------------------------------------

        reranking_start = metrics.timer()

        reranked = self.reranker.rerank(
            query=query,
            documents=retrieved,
            top_k=self.rerank_top_k,
        )

        metrics.reranking_ms = metrics.elapsed_ms(
            reranking_start
        )

        metrics.reranked_count = len(reranked)

        # ---------------------------------------------------------
        # 3. Context assembly
        # ---------------------------------------------------------

        context = build_context(
            reranked,
        )

        # ---------------------------------------------------------
        # 4. RAG generation
        # ---------------------------------------------------------

        generation_start = metrics.timer()

        answer = self.generator.generate(
            query=query,
            context=context,
        )

        metrics.generation_ms = metrics.elapsed_ms(
            generation_start
        )

        # ---------------------------------------------------------
        # 5. Citation mapping
        # ---------------------------------------------------------

        citations = map_citations(
            answer,
            reranked,
        )

        # ---------------------------------------------------------
        # 6. Answer evaluation
        # ---------------------------------------------------------

        evaluation_start = metrics.timer()

        evaluation = self.evaluator.evaluate(
            query=query,
            answer=answer,
            context_sources=reranked,
        )

        metrics.evaluation_ms = metrics.elapsed_ms(
            evaluation_start
        )

        # ---------------------------------------------------------
        # 7. Store evaluation metrics
        # ---------------------------------------------------------

        metrics.citation_score = evaluation.get(
            "citation_score",
            0.0,
        )

        metrics.relevance_score = evaluation.get(
            "relevance_score",
            0.0,
        )

        metrics.support_score = evaluation.get(
            "support_score",
            0.0,
        )

        metrics.overall_score = evaluation.get(
            "overall_score",
            0.0,
        )

        # ---------------------------------------------------------
        # 8. Total pipeline latency
        # ---------------------------------------------------------

        metrics.total_ms = metrics.elapsed_ms(
            total_start
        )

        # ---------------------------------------------------------
        # 9. Return complete pipeline result
        # ---------------------------------------------------------

        return {
            "query": query,
            "answer": answer,
            "citations": citations,
            "retrieved": reranked,

            "retrieved_count": len(retrieved),
            "reranked_count": len(reranked),

            "evaluation": evaluation,

            "metrics": metrics.to_dict(),
        }
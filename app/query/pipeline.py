from app.config.settings import settings

from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.hybrid.retriever import HybridRetriever

from app.reranking.cross_encoder import CrossEncoderReranker
from app.generation.rag_generator import RAGGenerator

from app.query.context import build_context

from app.citations.mapper import map_citations

from app.evaluation.answer_evaluator import AnswerEvaluator
from app.evaluation.faithfulness import FaithfulnessVerifier

from app.observability.metrics import PipelineMetrics


class QueryPipeline:

    def __init__(
        self,
        retrieval_top_k: int | None = None,
        rerank_top_k: int | None = None,
        candidate_k: int | None = None,
    ):

        # =========================================================
        # Configuration
        # =========================================================

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

        # =========================================================
        # Dense Retriever
        # =========================================================

        print("Loading dense retriever...")

        self.dense = DenseRetriever(
            model_name=settings.DENSE_MODEL,
        )

        self.dense.load(
            settings.DENSE_INDEX_PATH,
            settings.DENSE_METADATA_PATH,
        )

        print("Dense retriever loaded.")

        # =========================================================
        # BM25 Retriever
        # =========================================================

        print("Loading BM25 retriever...")

        self.bm25 = BM25Retriever()

        self.bm25.load(
            settings.BM25_METADATA_PATH,
        )

        print("BM25 retriever loaded.")

        # =========================================================
        # Hybrid Retriever
        # =========================================================

        print("Building hybrid retriever...")

        self.hybrid = HybridRetriever(
            dense_retriever=self.dense,
            bm25_retriever=self.bm25,
        )

        print("Hybrid retriever ready.")

        # =========================================================
        # Cross Encoder Reranker
        # =========================================================

        print("Loading reranker...")

        self.reranker = CrossEncoderReranker(
            model_name=settings.RERANKER_MODEL,
        )

        print("Reranker loaded.")

        # =========================================================
        # RAG Generator
        # =========================================================

        print("Loading RAG generator...")

        self.generator = RAGGenerator()

        print("RAG generator loaded.")

        # =========================================================
        # Answer Evaluator
        # =========================================================

        print("Loading answer evaluator...")

        self.evaluator = AnswerEvaluator()

        print("Answer evaluator loaded.")

        # =========================================================
        # Faithfulness Verifier
        # =========================================================

        print("Loading faithfulness verifier...")

        self.faithfulness_verifier = FaithfulnessVerifier()

        print("Faithfulness verifier loaded.")

    # =============================================================
    # QUERY PIPELINE
    # =============================================================

    def run(self, query: str):

        metrics = PipelineMetrics()

        total_start = metrics.timer()

        # =========================================================
        # 1. HYBRID RETRIEVAL
        # =========================================================

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

        print(
            f"[RAG DEBUG] Retrieved documents: "
            f"{len(retrieved)}"
        )

        if not retrieved:
            raise RuntimeError(
                "No documents were retrieved for the query."
            )

        # =========================================================
        # 2. CROSS-ENCODER RERANKING
        # =========================================================

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

        print(
            f"[RAG DEBUG] Reranked documents: "
            f"{len(reranked)}"
        )

        if not reranked:
            raise RuntimeError(
                "Reranking returned no documents."
            )

        # =========================================================
        # 3. CONTEXT ASSEMBLY
        # =========================================================

        context = build_context(
            reranked,
        )

        print(
            f"[RAG DEBUG] Final context length: "
            f"{len(context):,} characters"
        )

        if not context.strip():
            raise RuntimeError(
                "RAG context is empty. "
                "Retrieved documents contain no usable text."
            )

        # =========================================================
        # 4. RAG GENERATION
        # =========================================================

        generation_start = metrics.timer()

        answer = self.generator.generate(
            query=query,
            context=context,
        )

        metrics.generation_ms = metrics.elapsed_ms(
            generation_start
        )

        print("[RAG DEBUG] Answer generated.")

        if not answer or not answer.strip():
            raise RuntimeError(
                "RAG generator returned an empty answer."
            )

        # =========================================================
        # 5. CITATION MAPPING
        # =========================================================

        citation_start = metrics.timer()

        citations = map_citations(
            answer,
            reranked,
        )

        metrics.citation_verification_ms = metrics.elapsed_ms(
            citation_start
        )

        print(
            f"[RAG DEBUG] Citations mapped: "
            f"{len(citations)}"
        )

        # =========================================================
        # 6. ANSWER EVALUATION
        # =========================================================

        evaluation_start = metrics.timer()

        evaluation = self.evaluator.evaluate(
            query=query,
            answer=answer,
            context_sources=reranked,
        )

        metrics.evaluation_ms = metrics.elapsed_ms(
            evaluation_start
        )

        # =========================================================
        # 7. FAITHFULNESS VERIFICATION
        # =========================================================

        faithfulness_start = metrics.timer()

        faithfulness = self.faithfulness_verifier.verify(
            answer=answer,
            context_sources=reranked,
        )

        metrics.faithfulness_ms = metrics.elapsed_ms(
            faithfulness_start
        )

        print(
            f"[RAG DEBUG] Faithfulness score: "
            f"{faithfulness.get('faithfulness_score', 0.0)}"
        )

        print(
            f"[RAG DEBUG] Supported claims: "
            f"{faithfulness.get('supported_claims', 0)}"
            f"/"
            f"{faithfulness.get('total_claims', 0)}"
        )

        # =========================================================
        # 8. CITATION METRICS
        # =========================================================

        metrics.citation_validity = evaluation.get(
            "citation_score",
            evaluation.get(
                "citation_validity",
                0.0,
            ),
        )

        metrics.citation_accuracy = evaluation.get(
            "citation_accuracy",
            0.0,
        )

        metrics.total_citations = evaluation.get(
            "total_citations",
            len(citations),
        )

        metrics.valid_citations = len(
            evaluation.get(
                "valid_citations",
                [],
            )
        )

        metrics.invalid_citations = len(
            evaluation.get(
                "invalid_citations",
                [],
            )
        )

        # =========================================================
        # 9. ANSWER QUALITY METRICS
        # =========================================================

        metrics.relevance_score = evaluation.get(
            "relevance_score",
            0.0,
        )

        metrics.overall_score = evaluation.get(
            "overall_score",
            0.0,
        )

        # =========================================================
        # 10. FAITHFULNESS METRICS
        # =========================================================

        metrics.faithfulness_score = faithfulness.get(
            "faithfulness_score",
            0.0,
        )

        metrics.total_claims = faithfulness.get(
            "total_claims",
            0,
        )

        metrics.supported_claims = faithfulness.get(
            "supported_claims",
            0,
        )

        metrics.unsupported_claims = faithfulness.get(
            "unsupported_claims",
            0,
        )

        # =========================================================
        # 11. TOTAL PIPELINE LATENCY
        # =========================================================

        metrics.total_ms = metrics.elapsed_ms(
            total_start
        )

        # =========================================================
        # 12. DEBUG SUMMARY
        # =========================================================

        print(
            f"[RAG DEBUG] Citation validity: "
            f"{metrics.citation_validity}"
        )

        print(
            f"[RAG DEBUG] Citation accuracy: "
            f"{metrics.citation_accuracy}"
        )

        print(
            f"[RAG DEBUG] Faithfulness: "
            f"{metrics.faithfulness_score}"
        )

        print(
            f"[RAG DEBUG] Overall score: "
            f"{metrics.overall_score}"
        )

        print(
            f"[RAG DEBUG] Total latency: "
            f"{metrics.total_ms} ms"
        )

        # =========================================================
        # 13. COMPLETE PIPELINE RESULT
        # =========================================================

        return {
            "query": query,

            "answer": answer,

            "citations": citations,

            "retrieved": reranked,

            "retrieved_count": len(retrieved),

            "reranked_count": len(reranked),

            "evaluation": evaluation,

            "faithfulness": faithfulness,

            "metrics": metrics.to_dict(),
        }
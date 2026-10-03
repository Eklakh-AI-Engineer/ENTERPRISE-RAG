from __future__ import annotations

from app.citations.mapper import map_citations
from app.evaluation.answer_evaluator import AnswerEvaluator
from app.evaluation.faithfulness import FaithfulnessVerifier
from app.generation.rag_generator import RAGGenerator
from app.indexing.embeddings import SentenceTransformerEmbeddingProvider
from app.observability.metrics import PipelineMetrics
from app.persistence.supabase_chunks import SupabaseChunkRepository
from app.query.context import build_context
from app.reranking.cross_encoder import CrossEncoderReranker


class ProductionQueryPipeline:
    """Authenticated, tenant-scoped query pipeline backed by Supabase pgvector."""

    def __init__(
        self,
        *,
        embedding_model: str,
        reranker_model: str,
        retrieval_top_k: int,
        rerank_top_k: int,
    ) -> None:
        self.retrieval_top_k = retrieval_top_k
        self.rerank_top_k = rerank_top_k
        self.embedding_provider = SentenceTransformerEmbeddingProvider(embedding_model)
        self.reranker = CrossEncoderReranker(model_name=reranker_model)
        self.generator = RAGGenerator()
        self.evaluator = AnswerEvaluator()
        self.faithfulness_verifier = FaithfulnessVerifier()

    def run(self, *, query: str, organization_id: str, client) -> dict:
        metrics = PipelineMetrics()
        total_start = metrics.timer()

        retrieval_start = metrics.timer()
        embedding = self.embedding_provider.encode([query])[0].tolist()
        chunks = SupabaseChunkRepository(
            client,
            embedding_dimension=self.embedding_provider.dimension,
        ).search_similar(
            organization_id=organization_id,
            query_embedding=embedding,
            top_k=self.retrieval_top_k,
        )
        metrics.retrieval_ms = metrics.elapsed_ms(retrieval_start)
        metrics.retrieved_count = len(chunks)

        retrieved = [
            {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "text": chunk.content,
                "page": chunk.page,
                "section": chunk.section,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "score": chunk.similarity,
                "document": "unknown",
            }
            for chunk in chunks
        ]

        if not retrieved:
            raise RuntimeError("No documents were retrieved for the authenticated organization.")

        reranking_start = metrics.timer()
        reranked = self.reranker.rerank(
            query=query,
            documents=retrieved,
            top_k=self.rerank_top_k,
        )
        metrics.reranking_ms = metrics.elapsed_ms(reranking_start)
        metrics.reranked_count = len(reranked)

        if not reranked:
            raise RuntimeError("Reranking returned no documents.")

        context = build_context(reranked)
        if not context.strip():
            raise RuntimeError("RAG context is empty.")

        generation_start = metrics.timer()
        answer = self.generator.generate(query=query, context=context)
        metrics.generation_ms = metrics.elapsed_ms(generation_start)

        if not answer or not answer.strip():
            raise RuntimeError("RAG generator returned an empty answer.")

        citation_start = metrics.timer()
        citations = map_citations(answer, reranked)
        metrics.citation_verification_ms = metrics.elapsed_ms(citation_start)

        evaluation_start = metrics.timer()
        evaluation = self.evaluator.evaluate(
            query=query,
            answer=answer,
            context_sources=reranked,
        )
        metrics.evaluation_ms = metrics.elapsed_ms(evaluation_start)

        faithfulness_start = metrics.timer()
        faithfulness = self.faithfulness_verifier.verify(
            answer=answer,
            context_sources=reranked,
        )
        metrics.faithfulness_ms = metrics.elapsed_ms(faithfulness_start)

        metrics.citation_validity = evaluation.get(
            "citation_score",
            evaluation.get("citation_validity", 0.0),
        )
        metrics.citation_accuracy = evaluation.get("citation_accuracy", 0.0)
        metrics.total_citations = evaluation.get("total_citations", len(citations))
        metrics.valid_citations = len(evaluation.get("valid_citations", []))
        metrics.invalid_citations = len(evaluation.get("invalid_citations", []))
        metrics.relevance_score = evaluation.get("relevance_score", 0.0)
        metrics.overall_score = evaluation.get("overall_score", 0.0)
        metrics.faithfulness_score = faithfulness.get("faithfulness_score", 0.0)
        metrics.total_claims = faithfulness.get("total_claims", 0)
        metrics.supported_claims = faithfulness.get("supported_claims", 0)
        metrics.unsupported_claims = faithfulness.get("unsupported_claims", 0)
        metrics.total_ms = metrics.elapsed_ms(total_start)

        return {
            "query": query,
            "answer": answer,
            "citations": citations,
            "retrieved": reranked,
            "retrieved_count": len(retrieved),
            "reranked_count": len(reranked),
            "retrieval_mode": "pgvector",
            "evaluation": evaluation,
            "faithfulness": faithfulness,
            "metrics": metrics.to_dict(),
        }

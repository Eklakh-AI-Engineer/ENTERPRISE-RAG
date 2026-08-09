def hit_at_k(results, relevant_chunks, k):
    retrieved = {
        result["chunk_id"]
        for result in results[:k]
    }

    return int(
        bool(retrieved.intersection(relevant_chunks))
    )


def recall_at_k(results, relevant_chunks, k):
    retrieved = {
        result["chunk_id"]
        for result in results[:k]
    }

    relevant = set(relevant_chunks)

    return len(
        retrieved.intersection(relevant)
    ) / len(relevant)


def reciprocal_rank(results, relevant_chunks):
    relevant = set(relevant_chunks)

    for rank, result in enumerate(
        results,
        start=1,
    ):
        if result["chunk_id"] in relevant:
            return 1.0 / rank

    return 0.0


def evaluate_results(
    results,
    relevant_chunks,
    k_values=(1, 3, 5),
):
    metrics = {}

    for k in k_values:
        metrics[f"hit@{k}"] = hit_at_k(
            results,
            relevant_chunks,
            k,
        )

        metrics[f"recall@{k}"] = recall_at_k(
            results,
            relevant_chunks,
            k,
        )

    metrics["mrr"] = reciprocal_rank(
        results,
        relevant_chunks,
    )

    return metrics
def build_context(results, max_chars=12000):
    """
    Convert retrieved/reranked results into structured context
    for the generation model.
    """

    context_parts = []
    total_chars = 0

    for i, result in enumerate(results, start=1):

        text = result.get("text", "").strip()

        if not text:
            continue

        page = result.get("page")
        chunk_id = result.get("chunk_id")
        document = result.get("document", "sample.pdf")

        source_block = (
            f"[SOURCE {i}]\n"
            f"Document: {document}\n"
            f"Page: {page}\n"
            f"Chunk: {chunk_id}\n"
            f"Content:\n{text}\n"
        )

        if total_chars + len(source_block) > max_chars:
            break

        context_parts.append(source_block)
        total_chars += len(source_block)

    return "\n" + "\n".join(context_parts)
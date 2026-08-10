def build_context(results, max_chars=12000):
    """
    Convert retrieved/reranked results into structured context
    for the generation model.

    Each result is assigned a stable [SOURCE N] number that
    corresponds to its position in the reranked evidence list.
    """

    context_parts = []
    total_chars = 0

    for i, result in enumerate(results, start=1):

        # ---------------------------------------------------------
        # Extract text
        # ---------------------------------------------------------

        text = result.get("text")

        # Defensive fallback for alternate field names.
        if not text:
            text = result.get("content")

        if not text:
            text = result.get("chunk_text")

        if not text:
            print(
                f"[RAG WARNING] Source {i} has no usable text. "
                f"Keys: {list(result.keys())}"
            )
            continue

        text = str(text).strip()

        if not text:
            continue

        # ---------------------------------------------------------
        # Metadata
        # ---------------------------------------------------------

        page = result.get("page")
        chunk_id = result.get("chunk_id")

        # Your corpus uses "source": "sample.pdf".
        # Keep "document" as a fallback for compatibility.
        document = (
            result.get("document")
            or result.get("source")
            or "unknown"
        )

        document_id = result.get("document_id")
        section = result.get("section")

        # ---------------------------------------------------------
        # Build structured evidence block
        # ---------------------------------------------------------

        source_block = (
            f"[SOURCE {i}]\n"
            f"Document: {document}\n"
            f"Document ID: {document_id}\n"
            f"Page: {page}\n"
            f"Section: {section}\n"
            f"Chunk ID: {chunk_id}\n"
            f"Content:\n"
            f"{text}\n"
        )

        # ---------------------------------------------------------
        # Respect context size
        # ---------------------------------------------------------

        remaining = max_chars - total_chars

        if remaining <= 0:
            break

        if len(source_block) > remaining:

            # Try to preserve the evidence block even if the
            # final chunk must be truncated.
            header = (
                f"[SOURCE {i}]\n"
                f"Document: {document}\n"
                f"Document ID: {document_id}\n"
                f"Page: {page}\n"
                f"Section: {section}\n"
                f"Chunk ID: {chunk_id}\n"
                f"Content:\n"
            )

            available_text = remaining - len(header)

            if available_text > 0:
                source_block = (
                    header
                    + text[:available_text]
                    + "\n"
                )
            else:
                break

        context_parts.append(source_block)
        total_chars += len(source_block)

    # -------------------------------------------------------------
    # Debug information
    # -------------------------------------------------------------

    print(
        f"[RAG DEBUG] Context sources: {len(context_parts)}"
    )

    print(
        f"[RAG DEBUG] Context characters: {total_chars:,}"
    )

    print(
        f"[RAG DEBUG] Estimated tokens: "
        f"{total_chars // 4:,}"
    )

    if not context_parts:
        print(
            "[RAG WARNING] No usable text was found in "
            "reranked results."
        )

    return "\n".join(context_parts)
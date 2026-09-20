from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3, metadata_filter: dict | None = None) -> str:
        if self.store.get_collection_size() == 0:
            return "Không tìm thấy thông tin phù hợp trong cơ sở tri thức."

        if metadata_filter:
            chunks = self.store.search_with_filter(question, top_k=top_k, metadata_filter=metadata_filter)
        else:
            chunks = self.store.search(question, top_k=top_k)

        if not chunks:
            return "Không tìm thấy thông tin phù hợp trong cơ sở tri thức."

        context_lines = []
        for idx, chunk in enumerate(chunks, 1):
            doc_id = chunk.get("metadata", {}).get("doc_id", chunk.get("id", "N/A"))
            context_lines.append(f"[{idx}] (Nguồn: {doc_id}): {chunk['content']}")

        context_text = "\n\n".join(context_lines)

        prompt = (
            f"Dựa vào thông tin ngữ cảnh bên dưới để trả lời câu hỏi. "
            f"Chỉ sử dụng thông tin được cung cấp, không tự suy đoán. "
            f"Trích dẫn số thứ tự [1], [2] tương ứng với thông tin đã sử dụng.\n\n"
            f"--- NGỮ CẢNH ---\n{context_text}\n\n"
            f"--- CÂU HỎI ---\n{question}\n\n"
            f"--- CÂU TRẢ LỜI ---"
        )

        return self.llm_fn(prompt)

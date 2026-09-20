from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).parent))

from src.agent import KnowledgeBaseAgent
from src.chunking import RecursiveChunker
from src.models import Document
from src.store import EmbeddingStore

DATA_DIR = Path("data/ChinhSachDoiTraBaoHanh")
if not DATA_DIR.exists():
    DATA_DIR = Path("data/ecommerce")

OUTPUT_BENCHMARK_FILE = Path("ket_qua_benchmark.txt")

# 5 câu hỏi đánh giá chuẩn do nhóm thống nhất (R2 chủ trì)
BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Thời hạn yêu cầu đổi trả hoặc hoàn tiền dành cho người mua là bao nhiêu ngày?",
        "filter": {"audience": "buyer"},
        "gold_answer": "Được đổi mới miễn phí trong 30 ngày đầu tại TGDĐ/CellphoneS nếu lỗi kỹ thuật NSX.",
        "target_keywords": ["30 ngày", "đổi", "hoàn tiền"],
        "expected_docs": ["doi-tra-bao-hanh-cellphones-buyer", "doi-tra-bao-hanh-tgdd-buyer", "doi-tra-bao-hanh-lazada-buyer"],
    },
    {
        "id": 2,
        "query": "Thời hạn Người bán phải phản hồi và gửi khiếu nại Trả hàng/Hoàn tiền là bao nhiêu lâu?",
        "filter": {"audience": "seller"},
        "gold_answer": "Người bán có thời hạn 2 ngày (Shopee) hoặc 48 giờ (Lazada) để xử lý và gửi khiếu nại.",
        "target_keywords": ["2 ngày", "48 giờ", "khiếu nại"],
        "expected_docs": ["doi-tra-bao-hanh-shopee-seller", "doi-tra-bao-hanh-lazada-seller", "doi-tra-bao-hanh-tiki-seller"],
    },
    {
        "id": 3,
        "query": "Thời hạn bảo hành xe máy điện và Pin LFP VinFast là bao nhiêu năm?",
        "filter": None,
        "gold_answer": "Bảo hành xe là 6 năm/không giới hạn km; thời hạn bảo hành pin LFP lên tới 8 năm.",
        "target_keywords": ["6 năm", "8 năm", "Pin LFP"],
        "expected_docs": ["doi-tra-bao-hanh-vinfast-buyer"],
    },
    {
        "id": 4,
        "query": "Các trường hợp nào thiết bị di động bị từ chối bảo hành hoặc bị trừ phí khi đổi trả?",
        "filter": None,
        "gold_answer": "Từ chối khi tự ý tháo mở sửa chữa, rơi vỡ ngập nước; bị trừ 10-20% phí nếu trả máy không lỗi hoặc mất hộp/phụ kiện.",
        "target_keywords": ["rơi vỡ", "tháo", "trừ phí"],
        "expected_docs": ["doi-tra-bao-hanh-tgdd-buyer", "doi-tra-bao-hanh-cellphones-buyer"],
    },
    {
        "id": 5,
        "query": "Người bán cần chuẩn bị những bằng chứng gì khi khiếu nại đơn hàng bị trả về không nguyên vẹn?",
        "filter": {"audience": "seller"},
        "gold_answer": "Video mở kiện hàng có sự hiện diện của shipper, quay rõ 6 mặt kiện hàng nguyên vẹn và tình trạng sản phẩm bên trong.",
        "target_keywords": ["video", "6 mặt", "shipper"],
        "expected_docs": ["doi-tra-bao-hanh-shopee-seller", "doi-tra-bao-hanh-lazada-seller", "doi-tra-bao-hanh-tiki-seller"],
    },
]


def parse_md_file(file_path: Path) -> tuple[str, dict]:
    """Tách phần YAML Frontmatter (metadata) và phần thân (content) của file Markdown."""
    content = file_path.read_text(encoding="utf-8")
    parts = content.split("---")

    if len(parts) >= 3:
        fm_raw = parts[1]
        body = "---".join(parts[2:]).strip()
        metadata = dict(re.findall(r"^(\w+):\s*(.+)$", fm_raw, re.M))
    else:
        body = content.strip()
        metadata = {}

    if "doc_id" not in metadata:
        metadata["doc_id"] = file_path.stem

    return body, metadata


def synthesize_rag_answer(prompt: str) -> str:
    """Hàm tổng hợp câu trả lời RAG dựa trên ngữ cảnh đã truy xuất và câu hỏi."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            genai_mod = __import__("google.genai", fromlist=["genai"])
            client = genai_mod.Client(api_key=api_key)
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if response.text:
                return response.text.strip()
        except Exception:
            pass

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            openai_mod = __import__("openai")
            client = openai_mod.OpenAI(api_key=openai_key)
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return res.choices[0].message.content.strip()
        except Exception:
            pass

    # Tổng hợp nội dung cục bộ kèm trích dẫn nguồn [1], [2], [3]
    parts = prompt.split("--- CÂU HỎI ---")
    context_str = parts[0] if len(parts) > 0 else prompt
    chunks = re.findall(r"\[(\d+)\] \(Nguồn: ([^\)]+)\):\s*(.*)", context_str)
    if not chunks:
        return "Không tìm thấy thông tin phù hợp trong cơ sở tri thức."

    answers = []
    for rank_str, doc_id, text in chunks[:3]:
        text_clean = text.strip().replace("\n", " ")
        snippet = text_clean[:220] + "..." if len(text_clean) > 220 else text_clean
        answers.append(f"   [{rank_str}] ({doc_id}): {snippet}")

    return "Căn cứ theo tài liệu trích dẫn:\n" + "\n".join(answers)


def main():
    print("================================================================")
    print("     RUNNING BENCHMARK EVALUATION (CHECKPOINT 5 & 6)")
    print("================================================================")
    print(f"Thu thập dữ liệu từ: {DATA_DIR}")

    md_files = sorted(DATA_DIR.glob("*.md"))
    if not md_files:
        print(f"❌ Không tìm thấy file .md nào trong {DATA_DIR}")
        return

    # Chiến lược chunking cá nhân: RecursiveChunker(chunk_size=500)
    chunker = RecursiveChunker(chunk_size=500)
    all_chunks: list[Document] = []

    for file_path in md_files:
        body, frontmatter = parse_md_file(file_path)
        chunks_text = chunker.chunk(body)

        for idx, chunk_str in enumerate(chunks_text):
            chunk_doc = Document(
                id=f"{file_path.stem}#{idx}",
                content=chunk_str,
                metadata={
                    **frontmatter,
                    "doc_id": file_path.stem,
                    "chunk_index": idx,
                },
            )
            all_chunks.append(chunk_doc)

    print(f"Đã nạp {len(md_files)} file .md -> Sinh ra tổng cộng {len(all_chunks)} chunks.")

    # Khởi tạo EmbeddingStore và nạp tất cả chunks
    store = EmbeddingStore(collection_name="benchmark_store")
    store.add_documents(all_chunks)
    print(f"Đã ingest {store.get_collection_size()} chunks vào EmbeddingStore.\n")

    agent = KnowledgeBaseAgent(store=store, llm_fn=synthesize_rag_answer)

    output_lines = []
    header_str = f"BENCHMARK RESULTS REPORT - LE CONG TAM (G16)\nData Source: {DATA_DIR} ({len(md_files)} files, {len(all_chunks)} chunks)\nStrategy: RecursiveChunker (chunk_size=500)\n"
    output_lines.append(header_str)
    print(header_str)

    total_score = 0

    for item in BENCHMARK_QUERIES:
        q_id = item["id"]
        query = item["query"]
        meta_filter = item["filter"]
        gold = item["gold_answer"]
        expected = item.get("expected_docs", [])

        q_header = f"----------------------------------------------------------------\nQuery #{q_id}: {query}\nFilter: {meta_filter}\nGold Answer: {gold}"
        print(q_header)
        output_lines.append(q_header)

        # 1. Truy xuất CÓ METADATA FILTER
        results = store.search_with_filter(query, top_k=3, metadata_filter=meta_filter)

        print("\n  [TRUY XUẤT CÓ FILTER]:")
        output_lines.append("  [TRUY XUẤT CÓ FILTER]:")
        top3_info = []
        retrieved_docs = []
        for rank, res in enumerate(results, start=1):
            doc_id = res["metadata"].get("doc_id", "unknown")
            retrieved_docs.append(doc_id)
            score = res["score"]
            preview = res["content"][:120].replace("\n", " ")
            info_str = f"    Top-{rank} [Score: {score:.4f} | Doc: {doc_id} | ID: {res['id']}]: {preview}..."
            print(info_str)
            top3_info.append(info_str)
        output_lines.extend(top3_info)

        # 2. KIỂM THỬ A/B (Nếu câu hỏi có filter, chạy thêm 1 lần KHÔNG FILTER để so sánh)
        if meta_filter:
            no_filter_results = store.search(query, top_k=3)
            print("\n  [SO SÁNH A/B - TRUY XUẤT KHÔNG FILTER]:")
            output_lines.append("  [SO SÁNH A/B - TRUY XUẤT KHÔNG FILTER]:")
            for rank, res in enumerate(no_filter_results, start=1):
                doc_id = res["metadata"].get("doc_id", "unknown")
                score = res["score"]
                preview = res["content"][:100].replace("\n", " ")
                nf_str = f"    Top-{rank} [Score: {score:.4f} | Doc: {doc_id} | ID: {res['id']}]: {preview}..."
                print(nf_str)
                output_lines.append(nf_str)

        # Chấm điểm dựa trên 2 mức: Top-1 = 2đ, Top-2/3 = 1đ, Khác = 0đ
        q_score = 0
        if retrieved_docs and retrieved_docs[0] in expected:
            q_score = 2
        elif any(d in expected for d in retrieved_docs):
            q_score = 1
        else:
            q_score = 0

        total_score += q_score
        score_str = f"  -> Đánh giá điểm truy xuất: {q_score}/2 điểm (Target Docs: {expected})"
        print(score_str)
        output_lines.append(score_str)

        # Gọi RAG Agent trả lời
        agent_ans = agent.answer(query, top_k=3, metadata_filter=meta_filter)
        ans_str = f"  => Agent Output:\n{agent_ans}\n"
        print(ans_str)
        output_lines.append(ans_str)

    summary_str = f"================================================================\nTỔNG ĐIỂM BENCHMARK RETRIEVAL: {total_score}/10 điểm\n================================================================"
    print(summary_str)
    output_lines.append(summary_str)

    # Ghi kết quả ra file ket_qua_benchmark.txt
    OUTPUT_BENCHMARK_FILE.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"\n✅ Đã xuất báo cáo benchmark chi tiết vào file: {OUTPUT_BENCHMARK_FILE.absolute()}")


if __name__ == "__main__":
    main()

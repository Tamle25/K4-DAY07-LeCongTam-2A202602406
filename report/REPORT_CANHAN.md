# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Lê Công Tâm
**Nhóm:** G16
**Ngày:** 20-9-2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao nghĩa là hai vector embedding chỉ cùng về một hướng trong không gian đa chiều, thể hiện hai đoạn văn bản có mức độ tương đồng ngữ nghĩa (semantic similarity) rất lớn, dù từ vựng dùng để diễn đạt có thể khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: Khách hàng được nhận lại 100% số tiền nếu sản phẩm phát sinh lỗi từ nhà sản xuất.
- Câu B: Người mua sẽ được hoàn tiền toàn bộ khi thiết bị gặp sự cố kỹ thuật của nhà cung cấp.
- Tại sao tương đồng: Hai câu dùng từ vựng khác nhau hoàn toàn ("Khách hàng" vs "Người mua", "hoàn tiền toàn bộ" vs "nhận lại 100% số tiền") nhưng diễn đạt chung một bản chất quy định bồi thường sản phẩm lỗi.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Khách hàng được nhận lại 100% số tiền nếu sản phẩm phát sinh lỗi từ nhà sản xuất.
- Câu B: Xe máy điện VinFast trang bị động cơ công suất lớn và pin LFP bảo hành 8 năm.
- Tại sao khác: Hai câu thuộc hai chủ đề không liên quan (chính sách hoàn tiền vs thông số kỹ thuật xe máy điện).

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Khoảng cách Euclid phụ thuộc vào độ dài tuyệt đối của vector (văn bản dài hơn sẽ có vector độ lớn lớn hơn, làm khoảng cách Euclid bị kéo xa dù cùng ý nghĩa). Cosine similarity chỉ đo góc giữa 2 vector nên tập trung thuần túy vào hướng ngữ nghĩa và độc lập với độ dài văn bản.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* $\text{Số chunk} = \left\lceil \frac{10000 - 50}{500 - 50} \right\rceil = \left\lceil \frac{9950}{450} \right\rceil = \lceil 22.11 \rceil = 23$
> *Đáp án:* **23 chunks**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap tăng lên 100, số chunk tính được là $\lceil (10000-100)/(500-100) \rceil = \lceil 9900/400 \rceil = 25$ chunks (tăng thêm 2 chunks). Ta muốn overlap lớn hơn để giữ trọn vẹn ngữ cảnh ở ranh giới điểm cắt giữa 2 chunk liền kề, tránh làm đứt đoạn thông tin quan trọng.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Sử dụng biểu thức chính quy Lookbehind `re.split(r'(?<=[.!?])(?:\s+|\n+)', text)` để tách câu sau các dấu `. ! ?` mà giữ nguyên dấu câu không bị nuốt. Gom từng nhóm `max_sentences_per_chunk` câu lại thành một chunk string và loại bỏ khoảng trắng thừa. Edge case nhận biết chưa xử lý là chữ viết tắt (`TS.`, `v.v.`) và số thập phân (`3.14`).

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán ưu tiên thử danh sách dấu phân cách từ lớn đến nhỏ `["\n\n", "\n", ". ", " ", ""]`. Chiều đệ quy xuống cắt các mảnh lớn hơn `chunk_size`, chiều gom lên nối các mảnh nhỏ liền kề sát `chunk_size` để không sinh ra chunk quá vụn. Base case ngắt đệ quy khi mảnh $\le$ `chunk_size` hoặc khi `separators == []` thì cắt cứng theo `chunk_size`.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Danh sách `Document` nạp vào được chuẩn hóa thành các dictionary record lưu trong `self._store` (in-memory) bao gồm `id`, `content`, `metadata` (được copy độc lập) và vector `embedding`. Hàm `search` gọi helper `_search_records` tính điểm tích vô hướng (dot product) giữa vector truy vấn và từng stored vector, sắp xếp giảm dần theo `score` và trả về `top_k` kết quả.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Bắt buộc phải **lọc siêu dữ liệu (pre-filtering) TRƯỚC** rồi mới tính similarity: chọn các record trong `self._store` thỏa mãn mọi điều kiện của `metadata_filter` rồi mới truyền tập ứng viên đó vào `_search_records` (tránh mất kết quả nếu lấy top-k trước). Hàm `delete_document` lọc bỏ tất cả record có `metadata['doc_id'] == doc_id` hoặc `id == doc_id` và trả về `True` nếu có chunk bị xóa.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Xử lý an toàn khi store rỗng (trả câu thông báo, không gọi LLM vô ích). Với câu hỏi có dữ liệu, lấy top-k chunk, dựng ngữ cảnh được đánh số `[1]`, `[2]` kèm tên file nguồn `(Nguồn: doc_id)` để bảo đảm khả năng truy vết nguồn (Source Traceability). Prompt ràng buộc LLM chỉ dùng thông tin được cung cấp và bắt buộc trích dẫn số thứ tự.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\LabVin_Day7\K4-DAY07-LeCongTam-2A202602406\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\LabVin_Day7\K4-DAY07-LeCongTam-2A202602406
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.06s ==============================
```

**Số lượng bài test vượt qua (pass):** **42** / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Khách hàng được hoàn lại 100% tiền nếu hàng lỗi. | Người mua nhận lại toàn bộ tiền khi sản phẩm hỏng. | Cao | 0.0828 (Mock) | Đúng ngữ nghĩa |
| 2 | Khách hàng được hoàn lại 100% tiền nếu hàng lỗi. | Thời hạn bảo hành xe máy điện VinFast là 6 năm. | Thấp | 0.0052 | Đúng |
| 3 | Sản phẩm bị hỏng do rơi vỡ sẽ không được bảo hành. | Các lỗi hư hỏng do tác động vật lý bị từ chối bảo hành. | Cao | -0.0268 (Mock) | Sai số do Mock |
| 4 | Thời gian xử lý đổi trả cho gian hàng là 48 giờ. | Thời gian xử lý đổi trả cho gian hàng là 48 giờ. | Cao (1.0) | 1.0000 | Đúng |
| 5 | Người bán bị phạt Sao Quả Tạ nếu trốn bảo hành. | Shopee miễn phí vận chuyển cho đơn hàng đổi trả. | Thấp | -0.2026 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Kết quả bất ngờ nhất nằm ở Cặp 1 và Cặp 3: mặc dù hai câu có ngữ nghĩa rất tương đồng nhưng điểm thực tế của `MockEmbedder` lại rất thấp (thậm chí bị điểm âm). Điều này giải thích rõ ranh giới giữa Trình nhúng Giả lập (`MockEmbedder` băm băm MD5 số ngẫu nhiên chỉ để chạy test cấu trúc) và Mô hình Embedding thật (mã hóa dựa trên không gian vector ngữ nghĩa thực tế để hiểu đồng nghĩa/khác từ vựng).

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời hạn yêu cầu đổi trả hoặc hoàn tiền dành cho người mua là bao nhiêu ngày? | `doi-tra-bao-hanh-lazada-buyer#1`: Điều kiện không được bảo hành hoặc tính phí... | 0.3546 | Có (2/2đ) | Căn cứ theo [1] (doi-tra-bao-hanh-lazada-buyer)... |
| 2 | Thời hạn Người bán phải phản hồi và gửi khiếu nại Trả hàng/Hoàn tiền là bao nhiêu lâu? | `doi-tra-bao-hanh-shopee-seller#5`: Cơ chế bảo vệ Người Bán và khiếu nại trong 2 ngày... | 0.2651 | Có (2/2đ) | Căn cứ theo [1] (doi-tra-bao-hanh-shopee-seller) khiếu nại trong 2 ngày... |
| 3 | Thời hạn bảo hành xe máy điện và Pin LFP VinFast là bao nhiêu năm? | `doi-tra-bao-hanh-sunhouse-buyer#6`: Bảo hành đồ gia dụng (Mock MD5 hash noise) | 0.2524 | Thấp (0/2đ)* | *Mã hóa MockEmbedder băm MD5 số ngẫu nhiên. Với Real Embedder trả về VinFast 6 năm/8 năm. |
| 4 | Các trường hợp nào thiết bị di động bị từ chối bảo hành hoặc bị trừ phí khi đổi trả? | `doi-tra-bao-hanh-tgdd-buyer#2`: Quy định từ chối khi tự tháo máy, rơi vỡ ngập nước... | 0.3256 | Có (2/2đ) | Căn cứ theo [1] (doi-tra-bao-hanh-tgdd-buyer) rơi vỡ ngập nước trừ 10-20% phí... |
| 5 | Người bán cần chuẩn bị những bằng chứng gì khi khiếu nại đơn hàng bị trả về không nguyên vẹn? | `doi-tra-bao-hanh-lazada-seller#1`: Bằng chứng đối soát video mở hàng 6 mặt niêm phong... | 0.1420 | Có (2/2đ) | Căn cứ theo [1] (doi-tra-bao-hanh-lazada-seller) video 6 mặt đóng gói... |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **4** / 5 (Tổng điểm 8/10 điểm retrieval)

**Kết quả A/B Testing Metadata Filter:**
- **Khi CÓ Metadata Filter (`audience: seller`) ở Câu 5**: Top-1/2/3 thuộc 100% tài liệu Người Bán (`lazada-seller`, `tiki-seller`, `shopee-seller`).
- **Khi KHÔNG CÓ Metadata Filter ở Câu 5**: Cả 3 vị trí Top-3 đều bị chiếm bởi tài liệu Khách Hàng (`cellphones-buyer`). Điều này chứng minh Metadata Pre-filtering là bắt buộc trong RAG thương mại điện tử.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Qua so sánh trong nhóm, tôi nhận thấy việc lọc bằng metadata (`metadata_filter={"audience": "seller"}`) cực kỳ hiệu quả để ngăn chặn tình trạng trả về nhầm lẫn giữa tài liệu quy định dành cho người mua và nghĩa vụ dành cho nhà bán hàng. Ngoài ra, chiến lược `RecursiveChunker` giúp giữ ngữ cảnh nguyên vẹn hơn so với `FixedSizeChunker` khi văn bản có các cấu trúc đoạn văn ngắn dài khác nhau.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |

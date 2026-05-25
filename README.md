# Traffic Law RAG Chatbot

Hệ thống hỏi đáp văn bản pháp luật giao thông Việt Nam sử dụng kỹ thuật RAG (Retrieval-Augmented Generation) kết hợp với FastAPI.

---

## Tổng quan

Hệ thống cho phép người dùng đặt câu hỏi bằng ngôn ngữ thông thường (tiếng Việt dân dã) về các quy định xử phạt giao thông, và nhận được câu trả lời chính xác, có trích dẫn điều khoản cụ thể từ văn bản pháp luật.

**Điểm nổi bật:**
- Tự động phiên dịch câu hỏi dân dã sang thuật ngữ pháp lý trước khi tìm kiếm
- Hybrid Search = BM25 (từ khóa) + FAISS (ngữ nghĩa) để tăng độ chính xác
- Trả lời có trích dẫn Điều, Khoản cụ thể
- REST API với FastAPI, sẵn sàng tích hợp frontend hoặc chatbot

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT                               │
│              (HTTP POST /api/v1/chat)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI (app/)                           │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │  /health    │   │  /api/v1/chat│   │  Dependencies   │  │
│  │  GET        │   │  POST        │   │  (get_rag)      │  │
│  └─────────────┘   └──────┬───────┘   └────────┬────────┘  │
└──────────────────────────-┼─────────────────────┼──────────┘
                            │                     │
┌───────────────────────────▼─────────────────────▼──────────┐
│                   TrafficLawger (src/rag.py)                │
│                                                             │
│  1. rewrite_query()   →  Phiên dịch câu hỏi sang pháp lý   │
│  2. retriever.invoke()→  Hybrid Search (BM25 + FAISS)      │
│  3. build_user_prompt()→ Xây dựng prompt với ngữ cảnh      │
│  4. llm.chat_completion()→ Sinh câu trả lời (Qwen2.5-7B)   │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┴──────────────────┐
          │                                   │
┌─────────▼──────────┐             ┌──────────▼──────────┐
│  BM25 Retriever    │             │  FAISS Vector Store  │
│  (keyword search)  │             │  (semantic search)   │
│  weight: 40%  k=3  │             │  weight: 60%  k=3    │
└────────────────────┘             └──────────────────────┘
```

---

## Luồng xử lý dữ liệu (Pipeline)

```
PDF files
   │
   ▼ scripts/run_pipeline.py
Raw Markdown  ──► Metadata extraction (LLM) ──► docs_registry.json
   │
   ▼ Text cleaner
Clean Markdown
   │
   ▼ Article parser + Chunker
Chunks JSON  (metadata: Điều, Khoản, doc_name)
   │
   ▼ HuggingFace Embeddings (multilingual-e5-base)
FAISS Index  (storage/faiss_index/)
```

---

## Cấu trúc thư mục

```
trafficChatbot_rag/
├── app/                        # FastAPI application
│   ├── main.py                 # Entrypoint, lifespan, CORS
│   ├── api/
│   │   ├── dependencies.py     # Khởi tạo RAG, dependency injection
│   │   └── routers/
│   │       └── chat.py         # POST /api/v1/chat
├── src/                        # Core RAG logic
│   ├── config.py               # Cấu hình (Pydantic Settings)
│   ├── prompt.py               # System prompt + user prompt builder
│   ├── vector_db.py            # Load FAISS index
│   ├── retriever.py            # Hybrid retriever (BM25 + FAISS)
│   └── rag.py                  # TrafficLawger: rewrite + retrieve + generate
├── scripts/
│   ├── run_pipeline.py         # Ingest: PDF → chunks → FAISS
│   └── run_rag.py              # CLI chatbot (test nhanh)
├── data/
│   ├── raw_data/               # PDF văn bản pháp luật đầu vào
│   └── processed/              # Markdown đã làm sạch
├── storage/
│   └── faiss_index/            # FAISS index (vector database)
├── .env                        # API keys (không commit lên git)
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## Cài đặt & Chạy

### 1. Cài dependencies

```bash
pip install -r requirements.txt
```

### 2. Cấu hình `.env`

Tạo file `.env` ở thư mục gốc:

```env
HUGGINGFACEHUB_API_TOKEN=hf_xxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaSy...           # Nếu dùng Gemini
OPENAI_API_KEY=sk-...              # Nếu dùng OpenAI
```

### 3. Ingest dữ liệu (chạy lần đầu)

Đặt file PDF vào `data/raw_data/`, sau đó:

```bash
python scripts/run_pipeline.py
```

Kết quả: FAISS index được tạo tại `storage/faiss_index/`

### 4. Chạy API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Truy cập tài liệu API: http://localhost:8000/docs

### 5. Test CLI (không cần server)

```bash
python scripts/run_rag.py
```

---

## API Reference

### `GET /health`

Kiểm tra trạng thái hệ thống.

**Response:**
```json
{
  "status": "ok",
  "message": "Hệ thống RAG đang chạy!"
}
```

---

### `POST /api/v1/chat`

Hỏi đáp về pháp luật giao thông.

**Request body:**
```json
{
  "query": "Vượt đèn đỏ bị phạt bao nhiêu?",
  "vehicle_type": "xe máy"
}
```

| Field | Type | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `query` | string | ✅ | Câu hỏi (1–1000 ký tự) |
| `vehicle_type` | string | ❌ | Loại phương tiện (ô tô, xe máy, ...) |

**Response:**
```json
{
  "answer": "Theo Điều 6 Khoản 4 Nghị định 100/2019...",
  "rewritten_query": "Không chấp hành hiệu lệnh của đèn tín hiệu giao thông",
  "elapsed_seconds": 3.21
}
```

| Field | Mô tả |
|-------|-------|
| `answer` | Câu trả lời có trích dẫn điều khoản |
| `rewritten_query` | Câu hỏi sau khi phiên dịch sang thuật ngữ pháp lý |
| `elapsed_seconds` | Thời gian xử lý (giây) |

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|-----------|-----------|
| API Framework | FastAPI + Uvicorn |
| Embedding Model | `intfloat/multilingual-e5-base` |
| Vector Database | FAISS (CPU) |
| Keyword Search | BM25 (`rank_bm25`) |
| LLM | Qwen/Qwen2.5-7B-Instruct (HuggingFace Inference API) |
| LLM (cấu hình thay thế) | Google Gemini 2.5 Flash |
| RAG Orchestration | LangChain |
| PDF Processing | docling, pdfplumber, pymupdf4llm |

---

## Cấu hình nâng cao (`src/config.py`)

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `vector_store_dir` | `storage/faiss_index` | Đường dẫn FAISS index |
| `embedding_model` | `intfloat/multilingual-e5-base` | Model embedding |
| `chunk_size` | `1000` | Kích thước chunk (ký tự) |
| `chunk_overlap` | `150` | Overlap giữa các chunk |
| `top_k` | `5` | Số tài liệu trả về |
| `llm_provider` | `gemini` | Provider LLM |
| `llm_model` | `gemini-2.5-flash` | Model LLM |
| `llm_temperature` | `0.1` | Temperature (thấp = ổn định) |

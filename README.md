
# LocalRAG Pro

**Local RAG system for enterprise document search — no cloud, no data leakage.**

A privacy-first Retrieval-Augmented Generation (RAG) system that runs entirely on your local machine. Upload your company documents, build a vector index, and query them in natural language — powered by [Ollama](https://ollama.com) and [LlamaIndex](https://www.llamaindex.ai).

---

## ✨ Features

- **100% Local** — All processing happens on your machine. No data sent to external APIs.
- **Multi-format support** — PDF, DOCX, XLSX, PPTX, CSV, TXT
- **OCR support** — Scans image-based PDFs using Tesseract
- **Multilingual** — Japanese and English supported out of the box
- **API Key authentication** — Optional, for multi-user or network deployments
- **Docker ready** — One command to launch with `docker-compose up`
- **REST API** — Simple Flask-based API for easy integration
- **54 unit tests** — Fully tested with pytest

---

## 🏗️ Architecture

```
Your Documents (PDF, DOCX, XLSX...)
        ↓
  build_index.py          ← Vector index builder
        ↓
  LocalRAG_Pro_index/     ← Local vector store
        ↓
  api_server.py           ← Flask REST API
        ↓
  Ollama (local LLM)      ← Response generation
        ↓
  Your Application / Browser
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- (Optional) Docker & Docker Compose
- (Optional, for OCR) Tesseract OCR + Poppler

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Pull a model via Ollama

```bash
ollama pull qwen2.5:3b-instruct
```

### 3. Build the index

Place your documents in a folder, then set `US_ADMIN_ROOT` and run:

**Windows (PowerShell):**
```powershell
$env:US_ADMIN_ROOT = "C:\path\to\your\documents"
python app\build_index.py
```

**macOS / Linux:**
```bash
export US_ADMIN_ROOT="/path/to/your/documents"
python app/build_index.py
```

### 4. Start the API server

```bash
python app/api_server.py
```

Server runs at `http://localhost:5050`

### 5. Query your documents

```bash
curl -X POST http://localhost:5050/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key points in the Q3 report?"}'
```

---

## 🐳 Docker

Ollama must be running on the host (`ollama serve`). The container reaches it via `host.docker.internal`.

**Windows (PowerShell):**
```powershell
$env:US_ADMIN_INDEX_DIR = "C:\path\to\index"
docker-compose up -d
```

**macOS / Linux:**
```bash
export US_ADMIN_INDEX_DIR=/path/to/index
docker-compose up -d
```

Check status:
```bash
curl http://localhost:5050/health
```

---

## 🔐 API Key Authentication

To enable authentication, set the `API_KEY` environment variable:

**Windows (PowerShell):**
```powershell
$env:API_KEY = "your-secret-key"
```

**macOS / Linux:**
```bash
export API_KEY="your-secret-key"
```

Then include the key in requests:

```bash
curl -X POST http://localhost:5050/query \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize the contract terms"}'
```

If `API_KEY` is not set, authentication is disabled (suitable for localhost use).

---

## 📡 API Reference

### `GET /health`
Health check. No authentication required.

```json
{
  "status": "ok",
  "engine_ready": true,
  "model": "qwen2.5:3b-instruct",
  "index_path": "/index",
  "auth_enabled": false
}
```

### `POST /query`
Query your documents. Authentication required if `API_KEY` is set.

**Request:**
```json
{
  "question": "Your question here"
}
```

**Response:**
```json
{
  "answer": "Based on the documents...",
  "sources": [
    {"file": "report.pdf", "score": 0.92}
  ]
}
```

### `GET /status`
Engine status. Authentication required if `API_KEY` is set.

---

## ⚙️ Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `US_ADMIN_ROOT` | Script parent directory | Root folder to index |
| `US_ADMIN_INDEX_DIR` | `~/Documents/LocalRAG_Pro_index/index` | Index storage location |
| `OLLAMA_MODEL` | `qwen2.5:3b-instruct` | Ollama model to use |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `API_KEY` | *(empty = no auth)* | API key for authentication |
| `CORS_ORIGINS` | `http://localhost` | Allowed CORS origins (comma-separated) |
| `MAX_QUESTION_LEN` | `1000` | Max question length in characters |
| `ENABLE_OCR` | `1` | Enable OCR for image-based PDFs |
| `OCR_LANG` | `eng+jpn` | Tesseract OCR language |
| `OCR_MIN_TEXT_CHARS` | `50` | Trigger OCR if extracted text is shorter than this |
| `OCR_CACHE` | `1` | Cache OCR results to avoid re-running |
| `CHUNK_SIZE` | `512` | Token chunk size for indexing |
| `CHUNK_OVERLAP` | `200` | Token overlap between chunks |
| `PDF_LIMIT` | *(unset)* | Limit number of PDFs (for testing) |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

54 unit tests covering:
- API validation, authentication, and error handling
- Document readers (TXT, CSV, PDF) with multi-encoding support
- Index collection logic and directory exclusion
- OCR helper configuration
- Thread safety of engine loading

Tests use mocked `llama_index` modules, so heavy dependencies are not required to run them.

---

## 📁 Project Structure

```
LocalRAG-Pro/
├── app/
│   ├── __init__.py
│   ├── api_server.py       # Flask REST API server
│   └── build_index.py      # Document indexer
├── tests/
│   ├── conftest.py         # pytest fixtures & mocks
│   ├── test_api_server.py  # API tests
│   └── test_build_index.py # Indexer tests
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── LICENSE
├── pytest.ini
├── README.md
└── requirements.txt
```

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgements

- [LlamaIndex](https://www.llamaindex.ai) — RAG framework
- [Ollama](https://ollama.com) — Local LLM runtime
- [HuggingFace](https://huggingface.co) — Embedding models (`intfloat/multilingual-e5-large`)

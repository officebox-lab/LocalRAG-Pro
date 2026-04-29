

\# LocalRAG Pro



\*\*Local RAG system for enterprise document search — no cloud, no data leakage.\*\*



A privacy-first Retrieval-Augmented Generation (RAG) system that runs entirely on your local machine. Upload your company documents, build a vector index, and query them in natural language — powered by \[Ollama](https://ollama.com) and \[LlamaIndex](https://www.llamaindex.ai).



\---



\## ✨ Features



\- \*\*100% Local\*\* — All processing happens on your machine. No data sent to external APIs.

\- \*\*Multi-format support\*\* — PDF, DOCX, XLSX, PPTX, CSV, TXT

\- \*\*OCR support\*\* — Scans image-based PDFs using Tesseract

\- \*\*Multilingual\*\* — Japanese and English supported out of the box

\- \*\*API Key authentication\*\* — Optional, for multi-user or network deployments

\- \*\*Docker ready\*\* — One command to launch with `docker-compose up`

\- \*\*REST API\*\* — Simple Flask-based API for easy integration

\- \*\*Web scraper\*\* — Collect documents from URLs automatically with `scrape.py`

\- \*\*54 unit tests\*\* — Fully tested with pytest



\---



\## 🏗️ Architecture



```

Your Documents (PDF, DOCX, XLSX...)

&#x20;       ↓

&#x20; scrape.py (optional)    ← Web scraper (URLs → docs/)

&#x20;       ↓

&#x20; build\_index.py          ← Vector index builder

&#x20;       ↓

&#x20; LocalRAG\_Pro\_index/     ← Local vector store

&#x20;       ↓

&#x20; api\_server.py           ← Flask REST API

&#x20;       ↓

&#x20; Ollama (local LLM)      ← Response generation

&#x20;       ↓

&#x20; Your Application / Browser

```



\---



\## 🚀 Quick Start



\### Prerequisites



\- Python 3.10+

\- \[Ollama](https://ollama.com) installed and running

\- (Optional) Docker \& Docker Compose

\- (Optional, for OCR) Tesseract OCR + Poppler



\### 1. Install dependencies



```bash

pip install -r requirements.txt

```



\### 2. Pull a model via Ollama



```bash

ollama pull qwen2.5:3b-instruct

```



\### 3. Build the index



Place your documents in a folder, then set `US\_ADMIN\_ROOT` and run:



\*\*Windows (PowerShell):\*\*

```powershell

$env:US\_ADMIN\_ROOT = "C:\\path\\to\\your\\documents"

python app\\build\_index.py

```



\*\*macOS / Linux:\*\*

```bash

export US\_ADMIN\_ROOT="/path/to/your/documents"

python app/build\_index.py

```



\### 4. Start the API server



```bash

python app/api\_server.py

```



Server runs at `http://localhost:5050`



\### 5. Query your documents



```bash

curl -X POST http://localhost:5050/query \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{"question": "What are the key points in the Q3 report?"}'

```



\---



\## 🕷️ Web Scraper



Collect documents from websites and add them to your index automatically.



\### 1. Add URLs to `urls.txt`



```

\# urls.txt — one URL per line, # = comment

https://www.example.com/manual

https://wiki.example.com/guide

```



\### 2. Run the scraper



```bash

python scrape.py

```



Or scrape a single URL directly:



```bash

python scrape.py --url https://example.com/page --output docs

```



\### 3. Rebuild the index



```bash

python app/build\_index.py --input docs

```



\---



\## 🐳 Docker



Ollama must be running on the host (`ollama serve`). The container reaches it via `host.docker.internal`.



\*\*Windows (PowerShell):\*\*

```powershell

$env:US\_ADMIN\_INDEX\_DIR = "C:\\path\\to\\index"

docker-compose up -d

```



\*\*macOS / Linux:\*\*

```bash

export US\_ADMIN\_INDEX\_DIR=/path/to/index

docker-compose up -d

```



Check status:

```bash

curl http://localhost:5050/health

```



\---



\## 🔐 API Key Authentication



To enable authentication, set the `API\_KEY` environment variable:



\*\*Windows (PowerShell):\*\*

```powershell

$env:API\_KEY = "your-secret-key"

```



\*\*macOS / Linux:\*\*

```bash

export API\_KEY="your-secret-key"

```



Then include the key in requests:



```bash

curl -X POST http://localhost:5050/query \\

&#x20; -H "X-API-Key: your-secret-key" \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{"question": "Summarize the contract terms"}'

```



If `API\_KEY` is not set, authentication is disabled (suitable for localhost use).



\---



\## 📡 API Reference



\### `GET /health`

Health check. No authentication required.



```json

{

&#x20; "status": "ok",

&#x20; "engine\_ready": true,

&#x20; "model": "qwen2.5:3b-instruct",

&#x20; "index\_path": "/index",

&#x20; "auth\_enabled": false

}

```



\### `POST /query`

Query your documents. Authentication required if `API\_KEY` is set.



\*\*Request:\*\*

```json

{

&#x20; "question": "Your question here"

}

```



\*\*Response:\*\*

```json

{

&#x20; "answer": "Based on the documents...",

&#x20; "sources": \[

&#x20;   {"file": "report.pdf", "score": 0.92}

&#x20; ]

}

```



\### `GET /status`

Engine status. Authentication required if `API\_KEY` is set.



\---



\## ⚙️ Configuration



| Environment Variable | Default | Description |

|---|---|---|

| `US\_ADMIN\_ROOT` | Script parent directory | Root folder to index |

| `US\_ADMIN\_INDEX\_DIR` | `\~/Documents/LocalRAG\_Pro\_index/index` | Index storage location |

| `OLLAMA\_MODEL` | `qwen2.5:3b-instruct` | Ollama model to use |

| `OLLAMA\_HOST` | `http://localhost:11434` | Ollama API endpoint |

| `API\_KEY` | \*(empty = no auth)\* | API key for authentication |

| `CORS\_ORIGINS` | `http://localhost` | Allowed CORS origins (comma-separated) |

| `MAX\_QUESTION\_LEN` | `1000` | Max question length in characters |

| `ENABLE\_OCR` | `1` | Enable OCR for image-based PDFs |

| `OCR\_LANG` | `eng+jpn` | Tesseract OCR language |

| `OCR\_MIN\_TEXT\_CHARS` | `50` | Trigger OCR if extracted text is shorter than this |

| `OCR\_CACHE` | `1` | Cache OCR results to avoid re-running |

| `CHUNK\_SIZE` | `512` | Token chunk size for indexing |

| `CHUNK\_OVERLAP` | `200` | Token overlap between chunks |

| `PDF\_LIMIT` | \*(unset)\* | Limit number of PDFs (for testing) |



\---



\## 🧪 Running Tests



```bash

pytest tests/ -v

```



54 unit tests covering:

\- API validation, authentication, and error handling

\- Document readers (TXT, CSV, PDF) with multi-encoding support

\- Index collection logic and directory exclusion

\- OCR helper configuration

\- Thread safety of engine loading



Tests use mocked `llama\_index` modules, so heavy dependencies are not required to run them.



\---



\## 📁 Project Structure



```

LocalRAG-Pro/

├── app/

│   ├── \_\_init\_\_.py

│   ├── api\_server.py       # Flask REST API server

│   └── build\_index.py      # Document indexer

├── tests/

│   ├── conftest.py         # pytest fixtures \& mocks

│   ├── test\_api\_server.py  # API tests

│   └── test\_build\_index.py # Indexer tests

├── .dockerignore

├── .gitignore

├── Dockerfile

├── docker-compose.yml

├── LICENSE

├── pytest.ini

├── README.md

├── requirements.txt

├── scrape.py               # Web scraper (URLs → docs/)

└── urls.txt                # URL list for scraper

```



\---



\## 🤝 Contributing



Pull requests are welcome. For major changes, please open an issue first.



\---



\## 📄 License



MIT License — see \[LICENSE](LICENSE) file.



\---



\## 🙏 Acknowledgements



\- \[LlamaIndex](https://www.llamaindex.ai) — RAG framework

\- \[Ollama](https://ollama.com) — Local LLM runtime

\- \[HuggingFace](https://huggingface.co) — Embedding models (`intfloat/multilingual-e5-large`)




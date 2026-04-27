# LocalRAG_Pro\app\api_server.py
# -*- coding: utf-8 -*-
#
# RAG API サーバー（Flask中継ぎ）
# 使い方: py .\app\api_server.py
#
# このサーバーを起動してから、ブラウザでHTMLを開いてください。
# ポート: http://localhost:5050
#
# APIキー認証を有効にする場合:
#   $env:API_KEY="your-secret-key"
# リクエスト時はヘッダーに追加:
#   X-API-Key: your-secret-key

import os
import sys
import threading
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

from llama_index.core import StorageContext, load_index_from_storage, Settings, PromptTemplate
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer

# Windows cp932 コンソールでの UnicodeEncodeError を防ぐ
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

app = Flask(__name__)

# 許可オリジンは環境変数で上書き可能（デフォルト: localhost のみ）
# 複数指定する場合: $env:CORS_ORIGINS="http://localhost:3000,http://192.168.1.10"
_allowed_origins = os.environ.get("CORS_ORIGINS", "http://localhost").split(",")
CORS(app, origins=[o.strip() for o in _allowed_origins])

# ========================
# Config
# ========================

_default_index   = Path.home() / "Documents" / "LocalRAG_Pro_index" / "index"
INDEX_PATH       = Path(os.environ.get("US_ADMIN_INDEX_DIR", str(_default_index)))
OLLAMA_MODEL     = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b-instruct")
MAX_QUESTION_LEN = int(os.environ.get("MAX_QUESTION_LEN", "1000"))

# 未設定の場合は認証なし（社内 localhost 運用向け）
API_KEY = os.environ.get("API_KEY", "").strip()

# ========================
# Auth helper
# ========================

def require_api_key(f):
    """API_KEY 環境変数が設定されている場合のみ認証を要求するデコレータ"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEY:
            return f(*args, **kwargs)
        provided = request.headers.get("X-API-Key", "")
        if provided != API_KEY:
            return jsonify({"error": "認証エラー: X-API-Key ヘッダーが不正です"}), 401
        return f(*args, **kwargs)
    return decorated


# ========================
# RAG Engine（起動時に1回だけロード）
# ========================

query_engine = None
_engine_lock = threading.Lock()


def load_engine() -> bool:
    global query_engine
    with _engine_lock:
        if query_engine is not None:
            return True
        try:
            print(f"[INFO] インデックス読み込み中: {INDEX_PATH}")

            Settings.embed_model = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-large")
            Settings.llm         = Ollama(model=OLLAMA_MODEL, request_timeout=600.0)

            storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_PATH))
            index           = load_index_from_storage(storage_context)

            retriever            = VectorIndexRetriever(index=index, similarity_top_k=5)
            response_synthesizer = get_response_synthesizer(
                response_mode="compact",
                llm=Settings.llm
            )

            qa_prompt = PromptTemplate(
                "あなたは社内文書サポートAIアシスタントです。\n"
                "重要：必ず日本語で回答してください。英語での回答は禁止です。\n"
                "以下のドキュメントを参照して、質問に正確かつ簡潔に答えてください。\n\n"
                "参照ドキュメント：\n"
                "---------------------\n"
                "{context_str}\n"
                "---------------------\n"
                "質問：{query_str}\n"
                "回答（日本語で）："
            )

            query_engine = RetrieverQueryEngine(
                retriever=retriever,
                response_synthesizer=response_synthesizer
            )
            query_engine.update_prompts({"response_synthesizer:text_qa_template": qa_prompt})
            print(f"[INFO] RAGエンジン準備完了 ✅ モデル: {OLLAMA_MODEL}")
            return True
        except Exception as e:
            print(f"[ERROR] RAGエンジン初期化失敗: {e}")
            return False


# ========================
# Routes
# ========================

@app.route("/health", methods=["GET"])
def health():
    """接続確認用（認証不要）"""
    return jsonify({
        "status":       "ok",
        "engine_ready": query_engine is not None,
        "model":        OLLAMA_MODEL,
        "index_path":   str(INDEX_PATH),
        "auth_enabled": bool(API_KEY),
    })


@app.route("/query", methods=["POST"])
@require_api_key
def query():
    """RAGクエリ"""
    # silent=True で Content-Type が JSON でない場合に 415 を出さず None を返す
    data     = request.get_json(silent=True)
    question = (data or {}).get("question", "").strip()

    if not question:
        return jsonify({"error": "質問が空です"}), 400

    if len(question) > MAX_QUESTION_LEN:
        return jsonify({"error": f"質問は{MAX_QUESTION_LEN}文字以内にしてください"}), 400

    if not load_engine():
        return jsonify({
            "error":  "RAGエンジンの初期化に失敗しました。Ollamaが起動しているか確認してください。",
            "answer": None
        }), 500

    try:
        print(f"[QUERY] {question}")
        response = query_engine.query(question)
        answer   = str(response).strip()

        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes[:3]:
                meta  = node.metadata or {}
                fname = meta.get("file_name", "不明")
                score = round(node.score or 0, 3)
                sources.append({"file": fname, "score": score})

        print(f"[ANSWER] {answer[:100]}...")
        return jsonify({
            "answer":  answer,
            "sources": sources
        })

    except Exception as e:
        print(f"[ERROR] クエリ失敗: {e}")
        return jsonify({
            "error":  str(e),
            "answer": "エラーが発生しました。Ollamaが起動しているか確認してください。"
        }), 500


@app.route("/status", methods=["GET"])
@require_api_key
def status():
    """エンジン状態確認"""
    return jsonify({
        "engine_ready": query_engine is not None,
        "index_exists": INDEX_PATH.exists(),
        "model":        OLLAMA_MODEL,
    })


# ========================
# Main
# ========================

if __name__ == "__main__":
    print("=" * 50)
    print("  LocalRAG Pro RAG API サーバー")
    print("=" * 50)
    print(f"  モデル      : {OLLAMA_MODEL}")
    print(f"  インデックス: {INDEX_PATH}")
    print(f"  URL         : http://localhost:5050")
    print(f"  CORS許可元  : {_allowed_origins}")
    print(f"  APIキー認証 : {'有効' if API_KEY else '無効（$env:API_KEY で設定）'}")
    print("=" * 50)
    print("  Ollamaが起動していることを確認してください")
    print("  起動コマンド: ollama serve")
    print("=" * 50)

    load_engine()

    app.run(host="0.0.0.0", port=5050, debug=False)

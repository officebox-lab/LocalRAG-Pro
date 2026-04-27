# tests/conftest.py
# -*- coding: utf-8 -*-
#
# pytest 共通設定
# llama_index など重いライブラリをまとめてモック化し、
# インストールなしでテストを実行できるようにする

import sys
import types
from unittest.mock import MagicMock


# Document はテスト内で metadata["file_name"] のように辞書アクセスされるため
# MagicMock ではなく実機能を持つ軽量スタブに差し替える
class _DocumentStub:
    def __init__(self, text="", metadata=None):
        self.text = text
        self.metadata = metadata or {}


def _make_module(name):
    """軽量なダミーモジュールを生成する。MagicMock と違い、
    `from x import Y` で属性が新しい MagicMock に化けない。"""
    mod = types.ModuleType(name)
    return mod


# llama_index 系をすべてダミーモジュールとして登録
_MOCK_MODULES = [
    "llama_index",
    "llama_index.core",
    "llama_index.core.node_parser",
    "llama_index.core.retrievers",
    "llama_index.core.query_engine",
    "llama_index.core.response_synthesizers",
    "llama_index.llms",
    "llama_index.llms.ollama",
    "llama_index.embeddings",
    "llama_index.embeddings.huggingface",
    "sentence_transformers",
    "torch",
]

for mod_name in _MOCK_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = _make_module(mod_name)

# llama_index.core の主要シンボルを設定
_li_core = sys.modules["llama_index.core"]
_li_core.Document                = _DocumentStub
_li_core.Settings                = MagicMock()
_li_core.VectorStoreIndex        = MagicMock()
_li_core.StorageContext          = MagicMock()
_li_core.PromptTemplate          = MagicMock(side_effect=lambda tmpl: tmpl)
_li_core.load_index_from_storage = MagicMock()

# サブモジュールに必要なシンボルを設定
sys.modules["llama_index.core.node_parser"].SentenceSplitter        = MagicMock()
sys.modules["llama_index.core.retrievers"].VectorIndexRetriever     = MagicMock()
sys.modules["llama_index.core.query_engine"].RetrieverQueryEngine   = MagicMock()
sys.modules["llama_index.core.response_synthesizers"].get_response_synthesizer = MagicMock()
sys.modules["llama_index.llms.ollama"].Ollama                       = MagicMock()
sys.modules["llama_index.embeddings.huggingface"].HuggingFaceEmbedding = MagicMock()

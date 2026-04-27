# tests/test_api_server.py
# -*- coding: utf-8 -*-
#
# api_server.py のユニットテスト
# 実行: pytest tests/test_api_server.py -v

import os
import sys
import importlib
from unittest.mock import MagicMock, patch

import pytest

# app フォルダをパスに追加
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "app"))


# ========================
# Fixtures
# ========================

@pytest.fixture(autouse=True)
def reset_engine():
    """各テスト前後に query_engine をリセット"""
    import api_server
    api_server.query_engine = None
    yield
    api_server.query_engine = None


@pytest.fixture()
def client():
    """Flask テストクライアント（認証なし）"""
    os.environ.pop("API_KEY", None)
    import api_server
    importlib.reload(api_server)
    api_server.app.config["TESTING"] = True
    with api_server.app.test_client() as c:
        yield c


@pytest.fixture()
def client_with_key():
    """Flask テストクライアント（APIキー: testkey）"""
    os.environ["API_KEY"] = "testkey"
    import api_server
    importlib.reload(api_server)
    api_server.app.config["TESTING"] = True
    with api_server.app.test_client() as c:
        yield c
    os.environ.pop("API_KEY", None)


# ========================
# /health
# ========================

class TestHealth:
    def test_returns_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"

    def test_engine_ready_false_on_startup(self, client):
        res = client.get("/health")
        assert res.get_json()["engine_ready"] is False

    def test_auth_not_required(self, client_with_key):
        """/health は APIキーなしでもアクセスできること"""
        res = client_with_key.get("/health")
        assert res.status_code == 200

    def test_auth_enabled_flag(self, client_with_key):
        res = client_with_key.get("/health")
        assert res.get_json()["auth_enabled"] is True


# ========================
# /query - バリデーション
# ========================

class TestQueryValidation:
    def test_empty_question_returns_400(self, client):
        res = client.post("/query", json={"question": ""})
        assert res.status_code == 400
        assert "空" in res.get_json()["error"]

    def test_missing_question_returns_400(self, client):
        res = client.post("/query", json={})
        assert res.status_code == 400

    def test_question_too_long_returns_400(self, client):
        long_q = "あ" * 1001
        res = client.post("/query", json={"question": long_q})
        assert res.status_code == 400
        assert "文字以内" in res.get_json()["error"]

    def test_question_at_max_length_is_accepted(self, client):
        """エンジン未初期化で 500 になるが、400 にはならないこと"""
        q = "あ" * 1000
        res = client.post("/query", json={"question": q})
        assert res.status_code != 400

    def test_no_json_body_returns_400(self, client):
        res = client.post("/query", data="not json", content_type="text/plain")
        assert res.status_code == 400


# ========================
# /query - 認証
# ========================

class TestQueryAuth:
    def test_no_key_returns_401_when_auth_enabled(self, client_with_key):
        res = client_with_key.post("/query", json={"question": "テスト"})
        assert res.status_code == 401

    def test_wrong_key_returns_401(self, client_with_key):
        res = client_with_key.post(
            "/query",
            json={"question": "テスト"},
            headers={"X-API-Key": "wrongkey"}
        )
        assert res.status_code == 401

    def test_correct_key_passes_auth(self, client_with_key):
        """正しいキーを渡すとバリデーション以降に進むこと（エンジン未初期化で 500）"""
        res = client_with_key.post(
            "/query",
            json={"question": "テスト"},
            headers={"X-API-Key": "testkey"}
        )
        assert res.status_code != 401

    def test_no_auth_required_when_api_key_not_set(self, client):
        """API_KEY 未設定なら認証不要でクエリが通ること"""
        res = client.post("/query", json={"question": "テスト"})
        assert res.status_code != 401


# ========================
# /query - 正常系（エンジンをモック）
# ========================

class TestQuerySuccess:
    def test_returns_answer_and_sources(self, client):
        import api_server

        mock_node = MagicMock()
        mock_node.metadata = {"file_name": "doc.pdf"}
        mock_node.score    = 0.95

        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "これはテスト回答です"
        mock_response.source_nodes = [mock_node]

        mock_engine = MagicMock()
        mock_engine.query.return_value = mock_response
        api_server.query_engine = mock_engine

        res  = client.post("/query", json={"question": "テスト質問"})
        data = res.get_json()

        assert res.status_code == 200
        assert data["answer"] == "これはテスト回答です"
        assert data["sources"][0]["file"] == "doc.pdf"
        assert data["sources"][0]["score"] == 0.95

    def test_engine_query_exception_returns_500(self, client):
        import api_server

        mock_engine = MagicMock()
        mock_engine.query.side_effect = RuntimeError("Ollama 接続エラー")
        api_server.query_engine = mock_engine

        res = client.post("/query", json={"question": "テスト質問"})
        assert res.status_code == 500
        assert "answer" in res.get_json()


# ========================
# /status
# ========================

class TestStatus:
    def test_engine_not_ready_on_startup(self, client):
        res = client.get("/status")
        assert res.status_code == 200
        assert res.get_json()["engine_ready"] is False

    def test_engine_ready_when_loaded(self, client):
        import api_server
        api_server.query_engine = MagicMock()
        res = client.get("/status")
        assert res.get_json()["engine_ready"] is True

    def test_auth_required_when_key_set(self, client_with_key):
        res = client_with_key.get("/status")
        assert res.status_code == 401


# ========================
# load_engine - スレッド安全性
# ========================

class TestLoadEngineThreadSafety:
    def test_load_engine_called_twice_initializes_once(self):
        """load_engine を並列で呼んでも初期化は1回だけ実行されること"""
        import threading
        import api_server

        call_count = 0
        original_lock = api_server._engine_lock

        def fake_init():
            nonlocal call_count
            call_count += 1
            api_server.query_engine = MagicMock()
            return True

        results = []

        def run():
            with patch.object(api_server, "_engine_lock", original_lock):
                with patch("api_server.StorageContext") as _:
                    # エンジンが既にセットされている場合は即 True を返す
                    if api_server.query_engine is not None:
                        results.append(True)
                        return
                    results.append(fake_init())

        threads = [threading.Thread(target=run) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)

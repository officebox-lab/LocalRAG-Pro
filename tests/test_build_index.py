# tests/test_build_index.py
# -*- coding: utf-8 -*-
#
# build_index.py のユニットテスト
# 実行: pytest tests/test_build_index.py -v

import csv
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# app フォルダをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from build_index import (
    _ocr_cache_enabled,
    _ocr_enabled,
    _ocr_lang,
    _ocr_min_text_chars,
    _safe_filename,
    collect_documents,
    file_metadata_fn,
    get_paths,
    read_csv,
    read_pdf_text,
    read_txt,
)


# ========================
# Fixtures
# ========================

@pytest.fixture()
def tmp_docs(tmp_path):
    """テスト用の一時ドキュメントフォルダ"""
    return tmp_path


# ========================
# _safe_filename
# ========================

class TestSafeFilename:
    def test_replaces_special_chars(self):
        assert _safe_filename("hello world!") == "hello_world_"

    def test_keeps_alphanumeric(self):
        assert _safe_filename("abc123") == "abc123"

    def test_keeps_dots_and_dashes(self):
        assert _safe_filename("file-name.txt") == "file-name.txt"

    def test_japanese_replaced(self):
        result = _safe_filename("日本語ファイル.pdf")
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" for c in result)


# ========================
# 環境変数ヘルパー
# ========================

class TestEnvHelpers:
    def test_ocr_enabled_default(self, monkeypatch):
        monkeypatch.delenv("ENABLE_OCR", raising=False)
        assert _ocr_enabled() is True

    def test_ocr_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_OCR", "0")
        assert _ocr_enabled() is False

    def test_ocr_lang_default(self, monkeypatch):
        monkeypatch.delenv("OCR_LANG", raising=False)
        assert _ocr_lang() == "eng+jpn"

    def test_ocr_lang_custom(self, monkeypatch):
        monkeypatch.setenv("OCR_LANG", "jpn")
        assert _ocr_lang() == "jpn"

    def test_ocr_min_chars_default(self, monkeypatch):
        monkeypatch.delenv("OCR_MIN_TEXT_CHARS", raising=False)
        assert _ocr_min_text_chars() == 50

    def test_ocr_min_chars_custom(self, monkeypatch):
        monkeypatch.setenv("OCR_MIN_TEXT_CHARS", "100")
        assert _ocr_min_text_chars() == 100

    def test_ocr_min_chars_invalid_falls_back(self, monkeypatch):
        monkeypatch.setenv("OCR_MIN_TEXT_CHARS", "abc")
        assert _ocr_min_text_chars() == 50

    def test_ocr_cache_enabled_default(self, monkeypatch):
        monkeypatch.delenv("OCR_CACHE", raising=False)
        assert _ocr_cache_enabled() is True

    def test_ocr_cache_disabled(self, monkeypatch):
        monkeypatch.setenv("OCR_CACHE", "0")
        assert _ocr_cache_enabled() is False


# ========================
# get_paths
# ========================

class TestGetPaths:
    def test_returns_two_paths(self):
        root, index = get_paths()
        assert isinstance(root, Path)
        assert isinstance(index, Path)

    def test_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("US_ADMIN_ROOT", str(tmp_path))
        monkeypatch.setenv("US_ADMIN_INDEX_DIR", str(tmp_path / "idx"))
        root, index = get_paths()
        assert root == tmp_path
        assert index == tmp_path / "idx"

    def test_default_index_uses_home(self, monkeypatch):
        monkeypatch.delenv("US_ADMIN_INDEX_DIR", raising=False)
        _, index = get_paths()
        assert str(Path.home()) in str(index)


# ========================
# file_metadata_fn
# ========================

class TestFileMetadataFn:
    def test_returns_required_keys(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("hello", encoding="utf-8")
        meta = file_metadata_fn(str(f))
        assert "file_path" in meta
        assert "file_name" in meta
        assert "ext" in meta
        assert meta["file_name"] == "sample.txt"
        assert meta["ext"] == ".txt"

    def test_missing_file_does_not_raise(self, tmp_path):
        meta = file_metadata_fn(str(tmp_path / "nonexistent.pdf"))
        assert meta["mtime"] is None
        assert meta["size"] is None


# ========================
# read_txt
# ========================

class TestReadTxt:
    def test_reads_utf8(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("こんにちは", encoding="utf-8")
        assert read_txt(f) == "こんにちは"

    def test_reads_utf8_sig(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("BOM付きUTF-8", encoding="utf-8-sig")
        assert read_txt(f) == "BOM付きUTF-8"

    def test_reads_cp932(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes("Shift-JIS テスト".encode("cp932"))
        result = read_txt(f)
        assert "Shift-JIS" in result

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        assert read_txt(f) == ""

    def test_nonexistent_returns_empty(self, tmp_path):
        assert read_txt(tmp_path / "no.txt") == ""


# ========================
# read_csv
# ========================

class TestReadCsv:
    def test_reads_basic_csv(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("名前,年齢\n田中,30\n鈴木,25\n", encoding="utf-8")
        result = read_csv(f)
        assert "名前" in result
        assert "田中" in result

    def test_skips_empty_rows(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("A,B\n,\nC,D\n", encoding="utf-8")
        result = read_csv(f)
        lines = [l for l in result.splitlines() if l.strip()]
        assert len(lines) == 2

    def test_pipe_separator_in_output(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("X,Y,Z\n1,2,3\n", encoding="utf-8")
        result = read_csv(f)
        assert "|" in result


# ========================
# read_pdf_text
# ========================

class TestReadPdfText:
    def test_raises_import_error_when_fitz_missing(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "fitz":
                raise ImportError("No module named 'fitz'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="PyMuPDF"):
            read_pdf_text(Path("dummy.pdf"))

    def test_doc_close_called_even_on_error(self, tmp_path):
        """ページ読み込み中に例外が発生しても doc.close() が呼ばれること"""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.load_page.side_effect = RuntimeError("page error")

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            with pytest.raises(RuntimeError):
                read_pdf_text(tmp_path / "test.pdf")

        mock_doc.close.assert_called_once()

    def test_returns_text(self, tmp_path):
        mock_page = MagicMock()
        mock_page.get_text.return_value = "PDFのテキスト内容\n"

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.load_page.return_value = mock_page

        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = read_pdf_text(tmp_path / "test.pdf")

        assert "PDFのテキスト内容" in result
        mock_doc.close.assert_called_once()


# ========================
# collect_documents
# ========================

class TestCollectDocuments:
    def test_collects_txt_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("内容A", encoding="utf-8")
        (tmp_path / "b.txt").write_text("内容B", encoding="utf-8")
        index_dir = tmp_path / "index"
        index_dir.mkdir()

        docs = collect_documents(tmp_path, exclude_dirs={str(index_dir)}, index_dir=index_dir)
        assert len(docs) == 2

    def test_excludes_index_dir(self, tmp_path):
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        (index_dir / "should_skip.txt").write_text("スキップされるべき", encoding="utf-8")
        (tmp_path / "include.txt").write_text("含まれるべき", encoding="utf-8")

        docs = collect_documents(tmp_path, exclude_dirs={str(index_dir)}, index_dir=index_dir)
        filenames = [d.metadata["file_name"] for d in docs]
        assert "include.txt" in filenames
        assert "should_skip.txt" not in filenames

    def test_excludes_venv_dir(self, tmp_path):
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "hidden.txt").write_text("除外対象", encoding="utf-8")
        (tmp_path / "visible.txt").write_text("表示対象", encoding="utf-8")
        index_dir = tmp_path / "index"
        index_dir.mkdir()

        docs = collect_documents(tmp_path, exclude_dirs={str(index_dir)}, index_dir=index_dir)
        filenames = [d.metadata["file_name"] for d in docs]
        assert "visible.txt" in filenames
        assert "hidden.txt" not in filenames

    def test_skips_unsupported_extension(self, tmp_path):
        (tmp_path / "file.py").write_text("print('hello')", encoding="utf-8")
        index_dir = tmp_path / "index"
        index_dir.mkdir()

        docs = collect_documents(tmp_path, exclude_dirs={str(index_dir)}, index_dir=index_dir)
        assert len(docs) == 0

    def test_skips_empty_files(self, tmp_path):
        (tmp_path / "empty.txt").write_text("", encoding="utf-8")
        index_dir = tmp_path / "index"
        index_dir.mkdir()

        docs = collect_documents(tmp_path, exclude_dirs={str(index_dir)}, index_dir=index_dir)
        assert len(docs) == 0

    def test_metadata_attached(self, tmp_path):
        (tmp_path / "meta_test.txt").write_text("メタデータ確認", encoding="utf-8")
        index_dir = tmp_path / "index"
        index_dir.mkdir()

        docs = collect_documents(tmp_path, exclude_dirs={str(index_dir)}, index_dir=index_dir)
        assert docs[0].metadata["file_name"] == "meta_test.txt"
        assert docs[0].metadata["ext"] == ".txt"

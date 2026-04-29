"""
scrape.py — Web scraper for LocalRAG-Pro
URLリストからテキストを取得してdocsフォルダに保存する

Usage:
    python scrape.py                        # urls.txt を使用
    python scrape.py --urls urls.txt        # URLファイル指定
    python scrape.py --output docs          # 出力先指定
    python scrape.py --url https://example.com  # 単一URL
"""

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError:
    print("[ERROR] Required packages missing. Run:")
    print("  pip install httpx beautifulsoup4")
    sys.exit(1)


DEFAULT_URLS_FILE = "urls.txt"
DEFAULT_OUTPUT_DIR = "docs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LocalRAG-Pro/1.0)"
}
DELAY_SECONDS = 1.0  # リクエスト間隔（サーバー負荷軽減）


def fetch_text(url: str) -> str | None:
    """URLからテキストを取得してクリーニングする"""
    try:
        print(f"  Fetching: {url}")
        r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # 不要タグを削除
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        # テキスト抽出・クリーニング
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        lines = [l for l in lines if len(l) > 20]  # 短すぎる行を除外
        text = "\n".join(lines)

        # タイトル取得
        title = soup.title.string.strip() if soup.title else url

        return f"Source: {url}\nTitle: {title}\n\n{text}"

    except httpx.HTTPStatusError as e:
        print(f"  [WARN] HTTP {e.response.status_code}: {url}")
        return None
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}")
        return None


def url_to_filename(url: str) -> str:
    """URLをファイル名に変換する"""
    parsed = urlparse(url)
    # ドメイン + パスをファイル名に
    name = parsed.netloc + parsed.path
    name = re.sub(r'[^\w\-]', '_', name).strip('_')
    name = re.sub(r'_+', '_', name)
    if len(name) > 80:
        # 長すぎる場合はハッシュを付加
        name = name[:60] + '_' + hashlib.md5(url.encode()).hexdigest()[:8]
    return name + ".txt"


def load_urls(filepath: str) -> list[str]:
    """URLファイルを読み込む（#コメント・空行を除外）"""
    path = Path(filepath)
    if not path.exists():
        print(f"[ERROR] URL file not found: {filepath}")
        print(f"  Create {filepath} and add one URL per line.")
        print(f"  Lines starting with # are treated as comments.")
        sys.exit(1)

    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def scrape(urls: list[str], output_dir: str):
    """URLリストをスクレイプしてdocsフォルダに保存する"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0

    print(f"\n{'='*50}")
    print(f"  Scraping {len(urls)} URL(s) → {output_dir}/")
    print(f"{'='*50}")

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}]")
        text = fetch_text(url)

        if text:
            filename = url_to_filename(url)
            filepath = out / filename
            filepath.write_text(text, encoding="utf-8")
            print(f"  Saved: {filename} ({len(text):,} chars)")
            success += 1
        else:
            failed += 1

        if i < len(urls):
            time.sleep(DELAY_SECONDS)

    print(f"\n{'='*50}")
    print(f"  Done! Success: {success}  Failed: {failed}")
    print(f"  Output: {out.resolve()}")
    print(f"\n  Next step — rebuild index:")
    print(f"  python app/build_index.py --input {output_dir}")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape URLs and save as text for LocalRAG-Pro indexing"
    )
    parser.add_argument("--urls", default=DEFAULT_URLS_FILE,
                        help=f"Path to URL list file (default: {DEFAULT_URLS_FILE})")
    parser.add_argument("--url", default=None,
                        help="Single URL to scrape (overrides --urls)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    args = parser.parse_args()

    if args.url:
        urls = [args.url]
    else:
        urls = load_urls(args.urls)

    if not urls:
        print("[ERROR] No URLs found.")
        sys.exit(1)

    scrape(urls, args.output)


if __name__ == "__main__":
    main()

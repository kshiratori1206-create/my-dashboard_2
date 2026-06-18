#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ダッシュボード用データ収集スクリプト（v2）。
- note: 公開APIから記事取得（RSSより安定。有料/無料も判定可能）
- 乃木坂46: /detail/ を含む本物の記事リンクだけを抽出（ナビメニュー除外）
各処理は try/except で隔離し、失敗しても全体は止めない。
"""
import json, datetime, traceback, re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept-Language": "ja,en;q=0.9",
}
NOTE_ID = "nmique_sable9235"
TIMEOUT = 20

result, errors = {}, {}

def safe(key, fn):
    try:
        items = fn()
        result[key] = items
        print(f"[OK] {key}: {len(items)} 件")
    except Exception as e:
        result[key] = []
        errors[key] = str(e)
        print(f"[NG] {key}: {e}")
        traceback.print_exc()

# ---------- note: 公開APIで全記事取得 ----------
def _note_contents():
    url = (f"https://note.com/api/v2/creators/{NOTE_ID}"
           f"/contents?kind=note&page=1")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data.get("data", {}).get("contents", [])

def fetch_note_articles():
    items = []
    for n in _note_contents()[:10]:
        items.append({
            "title": n.get("name", "(無題)"),
            "link":  f"https://note.com/{NOTE_ID}/n/{n.get('key','')}",
            "date":  (n.get("publishAt") or "")[:10],
        })
    return items

def fetch_note_paid():
    # price > 0 の記事だけ＝有料コンテンツ
    items = []
    for n in _note_contents():
        if n.get("price", 0) and n["price"] > 0:
            items.append({
                "title": f"💰 {n.get('name','(無題)')}（¥{n['price']}）",
                "link":  f"https://note.com/{NOTE_ID}/n/{n.get('key','')}",
                "date":  (n.get("publishAt") or "")[:10],
            })
    return items[:10]

# ---------- 乃木坂46: 本物の記事だけ抽出 ----------
def scrape_nogi(path):
    url = f"https://www.nogizaka46.com/s/n46/{path}"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items, seen = [], set()
    # 記事詳細ページへのリンク（/detail/ を含む）だけを対象にする
    for a in soup.select("a[href*='/detail/']"):
        href = a.get("href", "")
        title = a.get_text(" ", strip=True)
        title = re.sub(r"\s+", " ", title)[:60]
        if not title or len(title) < 4 or href in seen:
            continue
        seen.add(href)
        if href.startswith("/"):
            href = "https://www.nogizaka46.com" + href
        items.append({"title": title, "link": href, "date": ""})
        if len(items) >= 10:
            break
    return items

def fetch_nogi_news():     return scrape_nogi("news/list")
def fetch_nogi_schedule(): return scrape_nogi("media/list")
def fetch_nogi_blog():     return scrape_nogi("diary/blog/list")

# ---------- 実行 ----------
safe("note_articles", fetch_note_articles)
safe("note_paid",     fetch_note_paid)
safe("nogi_news",     fetch_nogi_news)
safe("nogi_schedule", fetch_nogi_schedule)
safe("nogi_blog",     fetch_nogi_blog)

result["updated_at"] = datetime.datetime.now(
    datetime.timezone(datetime.timedelta(hours=9))
).strftime("%Y-%m-%d %H:%M")
result["_errors"] = errors

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("\n=== 完了 ===")
print("成功:", [k for k in result if k not in ("updated_at","_errors") and result[k]])
print("失敗:", list(errors.keys()))

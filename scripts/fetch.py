#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ダッシュボード用データ収集スクリプト（v3）。
- note: 正しいクリエイターID(tasty_nerine3657)でAPI取得
- 乃木坂46: 正しいパスに修正＋記事抽出ロジック強化
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
NOTE_ID = "tasty_nerine3657"     # ← 正しいIDに修正
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
            "link":  n.get("noteUrl") or f"https://note.com/{NOTE_ID}/n/{n.get('key','')}",
            "date":  (n.get("publishAt") or "")[:10],
        })
    return items

def fetch_note_paid():
    items = []
    for n in _note_contents():
        price = n.get("price", 0) or 0
        if price > 0:
            items.append({
                "title": f"💰 {n.get('name','(無題)')}（¥{price}）",
                "link":  n.get("noteUrl") or f"https://note.com/{NOTE_ID}/n/{n.get('key','')}",
                "date":  (n.get("publishAt") or "")[:10],
            })
    return items[:10]

# ---------- 乃木坂46: 記事抽出（強化版） ----------
def scrape_nogi(path):
    url = f"https://www.nogizaka46.com/s/n46/{path}"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items, seen = [], set()
    # /detail/ を含むリンクを記事とみなす
    for a in soup.select("a[href*='/detail/']"):
        href = a.get("href", "")
        # リンク内のテキスト全体を取得（タイトル＋日付が入っていることが多い）
        txt = a.get_text(" ", strip=True)
        txt = re.sub(r"\s+", " ", txt).strip()
        if not txt or href in seen:
            continue
        seen.add(href)
        # 日付パターン(2026.03.05 など)があれば分離
        m = re.search(r"(20\d\d[./]\d\d?[./]\d\d?[\s\d:]*)", txt)
        date = m.group(1).strip() if m else ""
        title = txt.replace(date, "").strip(" ・-|") if date else txt
        if not title:
            title = txt
        if href.startswith("/"):
            href = "https://www.nogizaka46.com" + href
        items.append({"title": title[:70], "link": href, "date": date})
        if len(items) >= 10:
            break
    return items

def fetch_nogi_news():     return scrape_nogi("news/list")
def fetch_nogi_schedule(): return scrape_nogi("media/list")
def fetch_nogi_blog():     return scrape_nogi("diary/MEMBER/list")  # ← 修正

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

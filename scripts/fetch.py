#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ダッシュボード用データ収集スクリプト。
note RSS と乃木坂46公式サイトを取得し data.json を生成する。
取得失敗しても全体が止まらないよう、各処理を try/except で隔離している。
"""
import json, datetime, traceback
import requests
import feedparser
from bs4 import BeautifulSoup

# ブラウザを装うUA。Bot対策の緩いサイトはこれで通ることが多い。
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept-Language": "ja,en;q=0.9",
}
NOTE_ID = "nmique_sable9235"
TIMEOUT = 20

result = {}   # 最終的に data.json になる辞書
errors = {}   # どのセクションが失敗したか記録

def safe(key, fn):
    """fn() を実行し、例外が出ても全体を止めずに errors に記録する。"""
    try:
        items = fn()
        result[key] = items
        print(f"[OK] {key}: {len(items)} 件")
    except Exception as e:
        result[key] = []
        errors[key] = str(e)
        print(f"[NG] {key}: {e}")
        traceback.print_exc()

# ---------- note: 自分の記事（RSS） ----------
def fetch_note_articles():
    url = f"https://note.com/{NOTE_ID}/rss"
    # feedparser に直接URLを渡すとUAが付かないので requests で取得してから渡す
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    items = []
    for e in feed.entries[:10]:
        items.append({
            "title": e.get("title", "(無題)"),
            "link":  e.get("link", "#"),
            "date":  e.get("published", "")[:16],
        })
    return items

# ---------- note: 有料コンテンツ ----------
# RSSには有料/無料の区別が明示されないため、ここでは記事一覧を流用し
# タイトルに含まれる記号等での簡易判定に留める（将来精緻化）。
def fetch_note_paid():
    arts = fetch_note_articles()
    # 暫定: いったん全記事を表示。有料判定の改善は後続ステップで。
    return arts[:5]

# ---------- 乃木坂46: 汎用スクレイパ ----------
def scrape_nogi(path):
    url = f"https://www.nogizaka46.com/s/n46/{path}"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    # 公式サイトのリスト項目候補を幅広く拾う（構造変更に多少強くする）
    for a in soup.select("a[href*='/detail/'], li a, .m--scl"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not title or len(title) < 4:
            continue
        if href.startswith("/"):
            href = "https://www.nogizaka46.com" + href
        items.append({"title": title[:60], "link": href, "date": ""})
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

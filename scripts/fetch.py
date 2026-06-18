#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ダッシュボード用データ収集スクリプト（v4）。
追加: 自分のスキ数実績 / note注目記事 / 急上昇ハッシュタグ
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
NOTE_ID = "tasty_nerine3657"
TIMEOUT = 20

result, errors = {}, {}

def safe(key, fn):
    try:
        items = fn()
        result[key] = items
        n = len(items) if isinstance(items, list) else 1
        print(f"[OK] {key}: {n} 件")
    except Exception as e:
        result[key] = [] if key != "note_stats" else {}
        errors[key] = str(e)
        print(f"[NG] {key}: {e}")
        traceback.print_exc()

# ---------- note: 自分の全記事を取得（複数ページ対応） ----------
def _note_all_contents(max_pages=10):
    out = []
    for p in range(1, max_pages + 1):
        url = (f"https://note.com/api/v2/creators/{NOTE_ID}"
               f"/contents?kind=note&page={p}")
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        contents = r.json().get("data", {}).get("contents", [])
        if not contents:
            break
        out.extend(contents)
    return out

def fetch_note_articles():
    items = []
    for n in _note_all_contents()[:10]:
        items.append({
            "title": n.get("name", "(無題)"),
            "link":  n.get("noteUrl") or f"https://note.com/{NOTE_ID}/n/{n.get('key','')}",
            "date":  (n.get("publishAt") or "")[:10],
        })
    return items

def fetch_note_paid():
    items = []
    for n in _note_all_contents():
        price = n.get("price", 0) or 0
        if price > 0:
            items.append({
                "title": f"💰 {n.get('name','(無題)')}（¥{price}）",
                "link":  n.get("noteUrl") or f"https://note.com/{NOTE_ID}/n/{n.get('key','')}",
                "date":  (n.get("publishAt") or "")[:10],
            })
    return items[:10]

# ---------- note: スキ数の実績（集計＋記事別ランキング） ----------
def fetch_note_stats():
    arts = _note_all_contents()
    total_like = sum((a.get("likeCount", 0) or 0) for a in arts)
    total_comment = sum((a.get("commentCount", 0) or 0) for a in arts)
    # スキ数が多い順トップ5
    ranked = sorted(arts, key=lambda a: a.get("likeCount", 0) or 0, reverse=True)
    top = []
    for a in ranked[:5]:
        top.append({
            "title": f"♥{a.get('likeCount',0)} … {a.get('name','(無題)')}",
            "link":  a.get("noteUrl") or f"https://note.com/{NOTE_ID}/n/{a.get('key','')}",
            "date":  (a.get("publishAt") or "")[:10],
        })
    # 先頭にサマリ行を入れる
    summary = {
        "title": f"📊 公開{len(arts)}記事 / 総スキ {total_like} / 総コメント {total_comment}",
        "link":  "https://note.com/sitesettings/stats",
        "date":  "",
    }
    return [summary] + top

# ---------- note: 注目記事（話題の記事） ----------
def fetch_note_featured():
    url = "https://note.com/api/v2/notes"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json().get("data", {})
    notes = data.get("notes") or data.get("contents") or []
    items = []
    for n in notes[:10]:
        items.append({
            "title": n.get("name", "(無題)"),
            "link":  n.get("noteUrl") or "https://note.com/",
            "date":  (n.get("publishAt") or "")[:10],
        })
    return items

# ---------- note: 急上昇ハッシュタグ ----------
def fetch_note_hashtags():
    url = "https://note.com/api/v2/hashtags"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json().get("data", {})
    tags = data.get("hashtags") or data.get("contents") or []
    items = []
    for t in tags[:10]:
        # 構造ゆれに対応
        h = t.get("hashtag", t)
        name = h.get("name", "")
        cnt = h.get("count", "")
        nm = name.lstrip("#")
        items.append({
            "title": f"#{nm}" + (f"（{cnt}）" if cnt else ""),
            "link":  f"https://note.com/hashtags/{nm}",
            "date":  "",
        })
    return items

# ---------- 乃木坂46: ブログ（取得できる唯一の自動枠） ----------
def scrape_nogi(path):
    url = f"https://www.nogizaka46.com/s/n46/{path}"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items, seen = [], set()
    for a in soup.select("a[href*='/detail/']"):
        href = a.get("href", "")
        txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        if not txt or href in seen:
            continue
        seen.add(href)
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

def fetch_nogi_blog(): return scrape_nogi("diary/MEMBER/list")

# ---------- 実行 ----------
safe("note_articles", fetch_note_articles)
safe("note_paid",     fetch_note_paid)
safe("note_stats",    fetch_note_stats)
safe("note_featured", fetch_note_featured)
safe("note_hashtags", fetch_note_hashtags)
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

import os
import smtplib
from email.mime.text import MIMEText
import feedparser
from datetime import datetime
import dateutil.parser
import difflib
import urllib.request
import json  # ★ テック系ストック保存用に追加

# =========================
# RSS一覧（稼働確認済み・HR系拡充版）
# =========================
RSS_FEEDS = [
    # --- AI・テクノロジー ---
    ("AI・テクノロジー", "https://blogs.nvidia.com/feed/"),
    ("AI・テクノロジー", "https://gigazine.net/news/rss_2.0/"),
    ("AI・テクノロジー", "https://techcrunch.com/feed/"),
    ("AI・テクノロジー", "https://www.theverge.com/rss/index.xml"),
    ("AI・テクノロジー", "https://www.wired.com/feed/rss"),
    ("AI・テクノロジー", "https://news.yahoo.co.jp/rss/topics/it.xml"),

    # --- 経済・ビジネス（株含む） ---
    ("経済・ビジネス", "https://www3.nhk.or.jp/rss/news/cat5.xml"),
    ("経済・ビジネス", "https://news.yahoo.co.jp/rss/topics/business.xml"),
    ("経済・ビジネス", "https://jbpress.ismedia.jp/list/feed/rss"),

    # --- 採用・HR ---
    ("採用・HR", "https://hrnote.jp/feed/"),
]

# =========================
# RSS取得（User-Agent追加・エラー対策）
# =========================
def fetch_rss_articles():
    articles = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for category_hint, url in RSS_FEEDS:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as res:
                html = res.read()
            feed = feedparser.parse(html)
        except Exception as e:
            print("----------------")
            print("URL:", url)
            print("取得エラー:", e)
            continue

        print("----------------")
        print("URL:", url)
        print("取得件数:", len(feed.entries))

        if len(feed.entries) > 0:
            print("最新記事:", feed.entries[0].title)

        for entry in feed.entries[:20]:
            title = entry.title
            link = entry.link

            if hasattr(entry, "published"):
                dt = dateutil.parser.parse(entry.published)
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
            else:
                dt = datetime.now()

            articles.append({
                "title": title,
                "link": link,
                "datetime": dt,
                "category_hint": category_hint,
            })

    return articles

# =========================
# 類似タイトル判定
# =========================
def group_similar_titles(articles):
    groups = []

    for article in articles:
        added = False

        for group in groups:
            rep_title = group["rep_title"]
            ratio = difflib.SequenceMatcher(None, rep_title, article["title"]).ratio()

            if ratio > 0.6:
                group["items"].append(article)
                added = True
                break

        if not added:
            groups.append({
                "rep_title": article["title"],
                "items": [article]
            })

    return groups

# =========================
# カテゴリ分類
# =========================
def classify_category(article):
    if article.get("category_hint"):
        return article["category_hint"]

    title = article["title"]
    t = title.lower()

    ai_keywords = [
        "ai", "人工知能", "machine learning", "deep learning", "chatgpt", "openai",
        "google", "apple", "microsoft", "meta", "amazon", "nvidia", "tesla"
    ]
    if any(k in t for k in ai_keywords):
        return "AI・テクノロジー"

    business_keywords = [
        "経済", "ビジネス", "企業", "決算", "スタートアップ", "業績",
        "株", "market", "日経", "dow", "nasdaq", "為替", "円安", "円高"
    ]
    if any(k in t for k in business_keywords):
        return "経済・ビジネス"

    hr_keywords = ["採用", "面接", "人事", "hr", "候補者", "内定", "退職", "雇用", "労務"]
    if any(k in t for k in hr_keywords):
        return "採用・HR"

    return "経済・ビジネス"

# =========================
# カテゴリ別に並べ替え＋抽出件数調整
# =========================
def sort_and_pick(groups):
    categories = {
        "AI・テクノロジー": [],
        "経済・ビジネス": [],
        "採用・HR": [],
    }

    for group in groups:
        rep_title = group["rep_title"]
        items = group["items"]

        latest_dt = max(item["datetime"] for item in items)
        category = classify_category(items[0])

        categories[category].append({
            "title": rep_title,
            "link": items[0]["link"],
            "datetime": latest_dt,
            "count": len(items)
        })

    for cat in categories:
        categories[cat].sort(
            key=lambda x: (-x["datetime"].timestamp(), -x["count"], x["title"])
        )

    filtered = {
        "AI・テクノロジー": categories["AI・テクノロジー"][:10],
        "経済・ビジネス": categories["経済・ビジネス"][:10],
        "採用・HR": categories["採用・HR"][:5],
    }

    return filtered

# =========================
# 日付フォーマット
# =========================
def format_date(dt):
    youbi = ["月", "火", "水", "木", "金", "土", "日"]
    return dt.strftime(f"%m-%d（{youbi[dt.weekday()]}）")

# =========================
# メール本文生成
# =========================
def build_email(categories):
    lines = []
    lines.append("真気さん、おはようございます。今日のニュースです。\n")

    order = [
        "AI・テクノロジー",
        "経済・ビジネス",
        "採用・HR",
    ]

    for cat in order:
        lines.append(f"🔵 {cat}")
        lines.append("")

        if len(categories[cat]) == 0:
            lines.append("- 該当ニュースなし\n")
            lines.append("---\n")
            continue

        items = categories[cat]

        for item in items:
            date_str = format_date(item["datetime"])
            lines.append(f"- **{item['title']}**（{date_str}）")
            lines.append(f"  {item['link']}\n")

        lines.append("---\n")

    return "\n".join(lines)

# =========================
# テック系ネタのストック保存処理（追加機能）
# =========================
def store_tech_challenges(categories):
    STOCK_FILE = "weekly_stock.json"
    
    # 開発・API・Python・ツールに関連しそうなキーワード
    tech_keywords = ["api", "python", "streamlit", "github", "ライブラリ", "ツール", "開発", "オープンソース", "ai", "llm", "モデル"]
    
    candidates = []
    for item in categories.get("AI・テクノロジー", []):
        title_lower = item["title"].lower()
        if any(kw in title_lower for kw in tech_keywords):
            candidates.append({
                "title": item["title"],
                "link": item["link"],
                "date": item["datetime"].strftime("%Y-%m-%d")
            })
            
    if not candidates:
        return

    # 既存ストックの読み込み
    existing = []
    if os.path.exists(STOCK_FILE):
        try:
            with open(STOCK_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
            
    # 重複防止しつつ追加
    existing_links = {c["link"] for c in existing}
    added_count = 0
    for c in candidates:
        if c["link"] not in existing_links:
            existing.append(c)
            added_count += 1
            
    if added_count > 0:
        with open(STOCK_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        print(f"テック系お題候補を {added_count} 件ストックに追加しました。")

# =========================
# メール送信
# =========================
def send_mail(body, subject):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", 587))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    to = os.getenv("MAIL_TO")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)

# =========================
# メイン処理
# =========================
if __name__ == "__main__":
    articles = fetch_rss_articles()
    groups = group_similar_titles(articles)
    categories = sort_and_pick(groups)

    # ★ テック系ネタをJSONへ蓄積する処理を呼び出し
    store_tech_challenges(categories)

    today = datetime.now().strftime("%m-%d")
    body = build_email(categories)
    
    # ローカルテスト時はメール送信エラーを防ぐためコメントアウト等で調整可能です
    send_mail(body, f"今日のニュースまとめ（{today}）")

import os
import smtplib
from email.mime.text import MIMEText
import feedparser
from datetime import datetime
import dateutil.parser
import difflib

# =========================
# RSS一覧（東洋経済削除・3カテゴリ構成）
# =========================
RSS_FEEDS = [
    # --- AI・テクノロジー ---
    ("AI・テクノロジー", "https://openai.com/blog/rss/"),
    ("AI・テクノロジー", "https://ai.googleblog.com/feeds/posts/default"),
    ("AI・テクノロジー", "https://blogs.nvidia.com/feed/"),
    ("AI・テクノロジー", "https://www.itmedia.co.jp/rss/2.0/news.xml"),
    ("AI・テクノロジー", "https://japan.cnet.com/rss/index.rdf"),
    ("AI・テクノロジー", "https://gigazine.net/news/rss_2.0/"),
    ("AI・テクノロジー", "https://jp.techcrunch.com/feed/"),
    ("AI・テクノロジー", "https://techcrunch.com/feed/"),
    ("AI・テクノロジー", "https://www.theverge.com/rss/index.xml"),
    ("AI・テクノロジー", "https://www.wired.com/feed/rss"),

    # --- 経済・ビジネス（株含む） ---
    ("経済・ビジネス", "https://forbesjapan.com/feed/rss"),
    ("経済・ビジネス", "https://diamond.jp/list/feed/rss"),
    ("経済・ビジネス", "https://www3.nhk.or.jp/rss/news/cat5.xml"),
    ("経済・ビジネス", "https://feeds.reuters.com/reuters/JPbusinessNews"),
    ("経済・ビジネス", "https://www.bloomberg.co.jp/feed"),

    # --- 採用・HR ---
    ("採用・HR", "https://www.hrpro.co.jp/rss/"),
    ("採用・HR", "https://hrnote.jp/feed/"),
    ("採用・HR", "https://bizhint.jp/feed"),
]

# =========================
# RSS取得
# =========================
def fetch_rss_articles():
    articles = []

    for category_hint, url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:20]:
            title = entry.title
            link = entry.link

            if hasattr(entry, "published"):
                dt = dateutil.parser.parse(entry.published)

                # ★ タイムゾーンを削除して「naive datetime」に統一
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)

            else:
                # ★ datetime.now() は naive なのでそのまま
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
# カテゴリ分類（RSSヒント最優先＋キーワード補助）
# =========================
def classify_category(article):
    # RSSヒント最優先
    if article.get("category_hint"):
        return article["category_hint"]

    title = article["title"]
    t = title.lower()

    # AI・テクノロジー
    ai_keywords = [
        "ai", "人工知能", "machine learning", "deep learning", "chatgpt", "openai",
        "google", "apple", "microsoft", "meta", "amazon", "nvidia", "tesla"
    ]
    if any(k in t for k in ai_keywords):
        return "AI・テクノロジー"

    # 経済・ビジネス（株含む）
    business_keywords = [
        "経済", "ビジネス", "企業", "決算", "スタートアップ", "業績",
        "株", "market", "日経", "dow", "nasdaq", "為替", "円安", "円高"
    ]
    if any(k in t for k in business_keywords):
        return "経済・ビジネス"

    # 採用・HR
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

    # 抽出件数（AI10・経済10・HR5）
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
# メール本文生成（視認性改善）
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
# メール送信
# =========================
def send_mail(body, subject):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT"))
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

    today = datetime.now().strftime("%m-%d")
    body = build_email(categories)

    send_mail(body, f"今日のニュースまとめ（{today}）")

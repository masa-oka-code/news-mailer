import os
import smtplib
from email.mime.text import MIMEText
import feedparser
from datetime import datetime
import dateutil.parser
import difflib

# =========================
# RSS一覧（必要なら後で差し替えOK）
# =========================
RSS_FEEDS = [
    "https://news.yahoo.co.jp/rss/topics/it.xml",
    "https://news.yahoo.co.jp/rss/topics/business.xml",
    "https://news.yahoo.co.jp/rss/topics/economy.xml",
    "https://news.yahoo.co.jp/rss/topics/finance.xml",
    "https://news.yahoo.co.jp/rss/topics/science.xml",
    "https://news.yahoo.co.jp/rss/topics/domestic.xml",
    "https://news.yahoo.co.jp/rss/topics/world.xml",
    "https://news.yahoo.co.jp/rss/topics/local.xml",
    "https://news.yahoo.co.jp/rss/topics/sports.xml",
    "https://news.yahoo.co.jp/rss/topics/entertainment.xml",
]

# =========================
# RSS取得
# =========================
def fetch_rss_articles():
    articles = []

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:20]:  # 各媒体20件
            title = entry.title
            link = entry.link

            # pubDate を datetime に変換
            if hasattr(entry, "published"):
                dt = dateutil.parser.parse(entry.published)
            else:
                dt = datetime.now()

            articles.append({
                "title": title,
                "link": link,
                "datetime": dt,
            })

    return articles

# =========================
# 類似タイトル判定（代表タイトル方式）
# =========================
def group_similar_titles(articles):
    groups = []

    for article in articles:
        added = False

        for group in groups:
            rep_title = group["rep_title"]
            ratio = difflib.SequenceMatcher(None, rep_title, article["title"]).ratio()

            if ratio > 0.6:  # 類似判定の閾値
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
# カテゴリ分類（あなたの6カテゴリ）
# =========================
def classify_category(title):
    title_lower = title.lower()

    if "ai" in title_lower or "人工知能" in title_lower:
        return "AI・テクノロジー"

    if "google" in title_lower or "apple" in title_lower or "microsoft" in title_lower:
        return "テック企業の動向"

    if "株" in title_lower or "market" in title_lower or "日経" in title_lower:
        return "株・マーケット"

    if "副業" in title_lower or "働き方" in title_lower:
        return "副業・働き方"

    if "経済" in title_lower or "ビジネス" in title_lower:
        return "経済・ビジネス"

    return "採用・HR"

# =========================
# カテゴリ別に並べ替え
# =========================
def sort_and_pick(groups):
    categories = {
        "AI・テクノロジー": [],
        "テック企業の動向": [],
        "株・マーケット": [],
        "副業・働き方": [],
        "経済・ビジネス": [],
        "採用・HR": [],
    }

    for group in groups:
        rep_title = group["rep_title"]
        items = group["items"]

        # 最新日付を代表にする
        latest_dt = max(item["datetime"] for item in items)

        category = classify_category(rep_title)

        categories[category].append({
            "title": rep_title,
            "link": items[0]["link"],
            "datetime": latest_dt,
            "count": len(items)
        })

    # 並び替え：新しい順 → similar_count → タイトル
    for cat in categories:
        categories[cat].sort(
            key=lambda x: (-x["datetime"].timestamp(), -x["count"], x["title"])
        )

    return categories

# =========================
# 日付フォーマット（MM-DD（曜））
# =========================
def format_date(dt):
    youbi = ["月", "火", "水", "木", "金", "土", "日"]
    return dt.strftime(f"%m-%d（{youbi[dt.weekday()]}）")

# =========================
# メール本文生成（あなたの最終テンプレート）
# =========================
def build_email(categories):
    lines = []
    lines.append("真気さん、おはようございます。今日のニュースです。\n")

    order = [
        "AI・テクノロジー",
        "テック企業の動向",
        "株・マーケット",
        "副業・働き方",
        "経済・ビジネス",
        "採用・HR",
    ]

    for cat in order:
        lines.append(f"🔵 {cat}（上位5件）")
        items = categories[cat][:5]

        for item in items:
            date_str = format_date(item["datetime"])
            lines.append(f"- [{item['title']}（{date_str}）]({item['link']})")

        lines.append("")

    return "\n".join(lines)

# =========================
# メール送信（Gmail SMTP）
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

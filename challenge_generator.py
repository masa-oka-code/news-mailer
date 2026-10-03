import os
import json
from google import genai

STOCK_FILE = "weekly_stock.json"
OUTPUT_FILE = "current_challenge.json"

def generate_weekly_challenge():
    if not os.path.exists(STOCK_FILE):
        print("今週のストックデータが見つかりませんでした。")
        return

    with open(STOCK_FILE, "r", encoding="utf-8") as f:
        stock_data = json.load(f)

    if not stock_data:
        print("今週のテック系ストックデータは空です。")
        return

    # 新SDKでは環境変数 GEMINI_API_KEY が自動で読み込まれます
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("エラー: GEMINI_API_KEY が環境変数に設定されていません。")
        return
    
    # 新しいクライアント初期化方式
    client = genai.Client(api_key=api_key)

    news_text = "\n".join([f"- {item['title']} ({item['link']})" for item in stock_data])

    prompt = f"""
以下は今週収集したテック系ニュースのストック一覧です。
この中から、プログラミング初心者の非エンジニアがAI（バイブコーディング）を活用して、
自分のローカル環境で「3時間以内に実装・動作させられるミニ実装お題」を厳選して1つだけ提案してください。

【超重要な条件】
- 単なるクラウドAI（ChatGPTやNotebookLM等）の画面上で完結するような「既存ツールの焼き直し（単なるファイルの要約など）」は避けてください。
- 「ローカルのファイル操作」「外部API連携」「定期自動化（GitHub Actions等）」「簡易的なスクレイピングやデータ集計」など、**自分でプログラムとして動かすからこそ便利で、個人開発の意義があるテーマ**を選定してください。

【今週のニュースストック】
{news_text}

【出力フォーマット（JSON形式で出力してください。Markdownのコードブロックは不要です）】
{{
  "title": "お題のタイトル",
  "background": "選定した背景・元ネタのニュース（なぜ今これをコードで作る意味があるのか）",
  "tech_stack": "使用する技術・API・ライブラリ（Python、Streamlitなど）",
  "steps": [
    "ステップ1の内容",
    "ステップ2の内容",
    "ステップ3の内容"
  ],
  "note_tips": "note記事を書く際のハマりどころやAIとの対話ポイントの予測"
}}
"""

    print("Gemini APIでお題を生成中...")
    # 2026年現在の標準軽量モデルを指定
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    # バッククォーテーション等を除去してJSONとしてパース
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    
    try:
        challenge_json = json.loads(clean_text)
    except Exception:
        challenge_json = {"raw_text": response.text}

    # 生成されたお題を保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(challenge_json, f, ensure_ascii=False, indent=2)
    print("今週のお題を current_challenge.json に保存しました。")

    # 処理完了後、weekly_stock.json を空（リセット）にする
    with open(STOCK_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    print("weekly_stock.json をリセットしました。")

if __name__ == "__main__":
    generate_weekly_challenge()

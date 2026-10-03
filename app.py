import streamlit as st
import json
import os

st.title("💡 今週のバイブコーディング・お題メーカー")

OUTPUT_FILE = "current_challenge.json"

if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    st.header(data.get("title", "お題"))
    st.info(f"**背景・目的**: {data.get('background', '')}")
    st.code(f"使用技術: {data.get('tech_stack', '')}", language="text")
    
    st.subheader("🛠️ 実装ステップ")
    for step in data.get("steps", []):
        st.markdown(f"- {step}")
        
    st.subheader("💡 Note記事用のハマりどころ・Tips")
    st.markdown(data.get("note_tips", ""))
else:
    st.warning("まだお題が生成されていません。GitHub Actionsを手動実行してみましょう！")

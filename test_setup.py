import pandas as pd
import MetaTrader5 as mt5
from newsapi import NewsApiClient
import requests

# ✅ Print pandas version to confirm environment
print("✅ Pandas Version:", pd.__version__)

# === 📡 Test MT5 Connection ===
print("\n📡 Initializing MT5...")
if not mt5.initialize():
    print("❌ MT5 failed to initialize. Error code:", mt5.last_error())
else:
    print("✅ MT5 initialized successfully")
    mt5.shutdown()

# === 📰 Test NewsAPI ===
try:
    newsapi = NewsApiClient(api_key='4578077442ba42f688c7bc3f11a8c73d')  # 🔑 Replace this with your NewsAPI key
    news = newsapi.get_top_headlines(language='en')
    print("\n📰 Top Headline:", news['articles'][0]['title'])
except Exception as e:
    print("❌ NewsAPI error:", e)

# === 🧠 Test Local LLaMA 3 via Ollama ===
try:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": "Explain the impact of CPI on forex trading.",
            "stream": False
        }
    )
    reply = response.json()["response"]
    print("\n🧠 LLaMA 3 response:\n", reply.strip())

except Exception as e:
    print("❌ LLaMA 3 error:", e)

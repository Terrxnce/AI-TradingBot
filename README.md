# AI Trading Bot 🧠📈

An autonomous trading bot that combines technical analysis with local AI reasoning to trade forex and index markets.

## ✅ Features

* Detects Order Blocks, Fair Value Gaps (FVG), Break of Structure (BOS), EMAs from live MT5 data
* Uses local LLaMA 3 (via Ollama) to interpret economic news and generate bias
* Executes trades through MetaTrader 5 with SL/TP and risk control
* Fully local and free: no OpenAI or crypto dependencies

## 🛠 Requirements

* Python 3.11+
* MetaTrader 5 installed
* Ollama (for running LLaMA 3 locally)
* NewsAPI key

## 🚀 Quick Start

```bash
git clone https://github.com/yourusername/AI-TradingBot.git
cd AI-TradingBot
python -m venv tradingbot_env
source tradingbot_env/bin/activate  # or .\tradingbot_env\Scripts\activate on Windows
pip install -r requirements.txt
python test_setup.py
```

## 📄 Core Files

| File                      | Purpose                                              |
| ------------------------- | ---------------------------------------------------- |
| `test_setup.py`           | Tests MT5, NewsAPI, and LLaMA 3 connectivity         |
| `get_candles.py`          | Retrieves live OHLCV data from MT5                   |
| `strategy_engine.py`      | Applies technical strategy logic (FVG, OB, BOS, EMA) |
| `run_strategy_test.py`    | End-to-end test of the technical signal pipeline     |
| `setup_summary.md`        | Log of verified system components and environment    |
| `AI Trading Bot Progress summary.txt` | Summarizes current setup, tools, and next steps for the AI trading bot project               |

## 📅 Project Status

* Environment fully set up (MT5, NewsAPI, LLaMA 3)
* Technical logic tested and functioning
* Ready to implement decision logic and trade execution loop

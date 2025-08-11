import os
import requests


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_trade_notification(symbol, direction, entry, sl, tp, lot, tech_score, ema_trend, ai_confidence, ai_reasoning, risk_note):
    msg = f"""
📢 *NEW TRADE SIGNAL*

📈 *{symbol}* – *{direction}*
💰 Entry: `{entry}`
🛑 SL: `{sl}`
🎯 TP: `{tp}`
📦 Lot Size: `{lot}`

📊 *Technical Score*: {tech_score}
📉 *EMA Trend*: {ema_trend}
🧠 *AI Confidence*: {ai_confidence}/10
🗣️ *Reasoning*: {ai_reasoning}

⚠️ Risk Note: {risk_note}
    """
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg.strip(),
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data, timeout=10)
    except Exception:
        pass


def send_welcome_message():
    # Deprecated: No plaintext onboarding in customer build
    pass

def send_group_login_update():
    # Deprecated: Never send credentials
    pass






def notify_partial_close_config_update():
    # Deprecated: Customer build uses in-app notifications
    pass


def send_bot_online_notification():
    # Internal only
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": "🤖 D.E.V.I Online", "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass


def send_trading_complete_notification():
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": "🏁 Trading Complete", "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass


def send_bot_offline_notification():
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": "⚠️ D.E.V.I Offline", "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass

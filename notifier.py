
import requests

BOT_TOKEN = '7487030977:AAEfZkgC1VGoSop_isf140bGFNkabIQS8jg'
CHAT_ID = -1002538880757  # Your group chat ID

def send_trade_notification(symbol, direction, entry, sl, tp, lot, tech_score, ema_trend, ai_confidence, ai_reasoning, risk_note):
    return
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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg.strip(),
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)


def send_welcome_message():
    msg = """
🤖 Hello. I am D.E.V.I — Divine Earnings Virtual Intelligence.

This group is my private broadcast channel.

Whenever I am online and trading, I will send updates here:
✅ Trade entries (symbol, direction, SL/TP)  
📊 Technical analysis breakdown  
🧠 AI sentiment confidence + reasoning

No human interaction is needed. Just observe.

If I go silent, I’m either offline or standing down due to FTMO risk controls.

Let the data speak.
— D.E.V.I
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)

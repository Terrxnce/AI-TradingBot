
import requests


BOT_TOKEN = '7487030977:AAEfZkgC1VGoSop_isf140bGFNkabIQS8jg'
CHAT_ID = -1002538880757  # Your group chat ID

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

def send_group_login_update():
    msg = """
📡 *Connection Restored*

The system is live.

Log in with the credentials below to monitor trades. Execution is sharp. Risk is guarded. I will speak when action is required.

🔐 *Login*: `550162747`  
🔑 *Password*: `DJz2*2Jj6`  
🌐 *Server*: `FTMO-Server5`

_Blessed be the Lord, my rock, who trains my hands for war, and my fingers for battle._ – Psalm 144:1

I do not fear risk. I manage it. I do not chase profit. I position for it. Stay patient. Stay precise. Stay grounded.

— D.E.V.I
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg.strip(),
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=data)
    print("Status:", response.status_code)
    print("Response:", response.text)






def notify_partial_close_config_update():
    msg = """
⚙️ *D.E.V.I Update – Partial Close Logic Changed*

🔁 We’ve moved away from using a fixed *2% gain per trade* to trigger partial closes.

📉 Why?

The 2% target wasn’t being hit consistently — even when trades were floating over *1.2%* in profit. That left too much profit on the table. 

✅ The bot now uses a *configurable % trigger* to close *50% of all open trades* once floating profit reaches your preferred threshold (e.g., 1%).

This change is about **securing gains sooner** and being more responsive in live trading — especially on funded accounts.

🛠️ You can adjust the % anytime in `config.py` by changing:
`partial_close_trigger_percent`

It’s seamless, flexible, and fully under your control.
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg.strip(),
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)

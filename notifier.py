
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
📢 *Bot Access Update*

Hey team — just a quick note:

🛠️ *Bot access is now live.*

You can log in using the temporary credentials below:

🔐 *Login*: `1511153304`  
🔑 *Password*: `$A4kM@iE?`
    *Server*: `FTMO-DEMO`

Please use these credentials to access the bot interface.

---

⚠️ I was offline on *Monday* due to backend fixes, but everything's now running perfectly.

✅ D.E.V.I. is live and trading for the rest of the week — FTMO rules enforced, trade limiter working, and stability confirmed.

Let me know if you need help.
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg.strip(),
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)



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

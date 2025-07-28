
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


def send_bot_online_notification():
    """
    Send notification when bot goes online and is holding until trading window
    """
    from datetime import datetime
    now = datetime.now()
    
    # Check if there's any upcoming news
    try:
        from news_guard import get_high_impact_news
        news_events = get_high_impact_news()
        news_info = ""
        if news_events:
            news_info = "\n\n📰 *Upcoming High-Impact News:*\n"
            for event in news_events[:3]:  # Show first 3 events
                news_info += f"• {event.get('title', 'News Event')}\n"
    except:
        news_info = "\n\n📰 *News monitoring active*"
    
    msg = f"""
🤖 *D.E.V.I Online*

I am now live and monitoring the markets.

⏰ *Trading Window:* 14:00-16:00 (2:00-4:00 PM)
🎯 *Current Status:* Holding until allowed window
📊 *Focus:* USD pairs and indices only

I will remain patient and wait for the optimal trading conditions. No trades will be taken outside the designated window.

{news_info}

*"The patient hunter gets the prey."*
— D.E.V.I
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg.strip(),
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)


def send_trading_complete_notification():
    """
    Send notification when trading is done for the day
    """
    from datetime import datetime
    now = datetime.now()
    
    msg = f"""
🏁 *Trading Complete*

All positions have been closed. Trading session ended at {now.strftime('%H:%M')}.

📊 *Session Summary:*
• All trades closed successfully
• Risk management protocols maintained
• Ready for next session

I will remain offline until the next trading window.

*"Discipline is the bridge between goals and accomplishment."*
— D.E.V.I
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg.strip(),
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)


def send_bot_offline_notification():
    """
    Send notification when bot goes offline unexpectedly
    """
    from datetime import datetime
    now = datetime.now()
    
    msg = f"""
⚠️ *D.E.V.I Offline*

I have been taken offline at {now.strftime('%H:%M')}.

🔍 *Possible Reasons:*
• System maintenance
• Connection issues
• Manual shutdown
• Risk management trigger

All open positions have been managed according to protocols.

I will return when conditions are optimal.

*"Even the strongest systems need rest."*
— D.E.V.I
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg.strip(),
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)

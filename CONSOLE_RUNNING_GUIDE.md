# **🚀 D.E.V.I Trading Bot - Console Running Guide**

## **Complete Step-by-Step Instructions for Running D.E.V.I from Command Line**

---

## **📋 Prerequisites**

### **Required Software**
- ✅ **Python 3.9+** installed
- ✅ **MetaTrader 5** installed and running
- ✅ **Git** for version control
- ✅ **Windows Command Prompt** or **PowerShell**

### **Required Accounts**
- ✅ **MT5 Trading Account** (demo or live)
- ✅ **Ollama** with LLaMA 3 model installed
- ✅ **Telegram Bot** (optional, for notifications)

---

## **🔧 Initial Setup (One-Time)**

### **Step 1: Clone Repository**
```cmd
# Navigate to your desired directory
cd C:\Users\YourUsername\Projects

# Clone the repository
git clone https://github.com/yourusername/AI_TradingBot.git
cd AI_TradingBot
```

### **Step 2: Create Virtual Environment**
```cmd
# Create virtual environment
python -m venv tradingbot_env

# Activate virtual environment
tradingbot_env\Scripts\activate

# Verify activation (should show (tradingbot_env) prefix)
```

### **Step 3: Install Dependencies**
```cmd
# Install all required packages
pip install -r requirements.txt

# Verify key packages
python -c "import MetaTrader5 as mt5; print('MT5:', mt5.version())"
python -c "import pandas as pd; print('Pandas:', pd.__version__)"
python -c "import ta; print('TA-Lib available')"
```

### **Step 4: Set Environment Variables**
```cmd
# Set Telegram credentials (optional)
setx TELEGRAM_BOT_TOKEN "your_bot_token_here"
setx TELEGRAM_CHAT_ID "your_chat_id_here"

# Set user ID for the bot
setx DEVI_USER_ID "internal"

# Verify environment variables
echo %TELEGRAM_BOT_TOKEN%
echo %TELEGRAM_CHAT_ID%
echo %DEVI_USER_ID%
```

### **Step 5: Configure MT5 Connection**
```cmd
# Test MT5 connection
python test_mt5_connection.py

# Expected output:
# ✅ MT5 initialized successfully
# ✅ Account connected: [Account Number]
# ✅ Balance: $[Amount]
# ✅ EURUSD available for trading
```

---

## **🎯 Daily Running Instructions**

### **Step 1: Prepare Environment**
```cmd
# Navigate to project directory
cd C:\Users\YourUsername\Projects\AI_TradingBot

# Activate virtual environment
tradingbot_env\Scripts\activate

# Verify environment
python -c "import sys; print('Python:', sys.version)"
python -c "import MetaTrader5 as mt5; print('MT5 Available:', mt5.initialize())"
```

### **Step 2: Quick System Validation**
```cmd
# Run quick validation
python quick_validation.py

# Expected output:
# 🔍 D.E.V.I Quick Validation
# ========================================
# ✅ Config loaded
#    Min score: 5.5
#    Trading window: {'start_hour': 13, 'end_hour': 17}
#    Dynamic RRR: True
# ✅ All core modules imported
# ✅ MT5 connected - Account: [Account Number]
#    Balance: $[Amount]
# 
# 🎉 VALIDATION SUCCESSFUL!
# ✅ D.E.V.I is ready for live trading
```

### **Step 3: Start D.E.V.I Trading Bot**

#### **Option A: Standard Start (Recommended)**
```cmd
# Start with quarter-hour time alignment
python "Bot Core\bot_runner.py" --user-id internal --align quarter

# Expected output:
# 🚀 D.E.V.I Trading Bot Starting...
# 📅 Current Time: 2025-01-15 14:30:00 UTC
# ⏰ Aligning to next quarter boundary...
# 🔄 Waiting for 14:45:00 UTC...
# ✅ Time aligned successfully
# 🧠 AI Model: LLaMA 3 (Ollama)
# 📊 Trading Window: 13:00-17:00 UTC
# 🎯 Min Score: 5.5
# 💰 Lot Size: 0.01
# 🔄 Starting main trading loop...
```

#### **Option B: Immediate Start (No Alignment)**
```cmd
# Start immediately without time alignment
python "Bot Core\bot_runner.py" --user-id internal

# Use this for testing or when you want immediate execution
```

#### **Option C: Debug Mode**
```cmd
# Start with verbose logging
python "Bot Core\bot_runner.py" --user-id internal --align quarter --debug

# Shows detailed information about each decision
```

### **Step 4: Monitor Bot Operation**

#### **Real-Time Monitoring**
```cmd
# The bot will display real-time information:
# 
# 🔄 [14:45:00] Analyzing EURUSD...
# 📊 Technical Score: 6.2
# 🧠 AI Decision: BUY (Confidence: 8)
# ✅ Risk Check: PASSED
# 💰 Placing BUY order: 0.01 lots @ 1.0850
# 🎯 SL: 1.0800 | TP: 1.0950 | RRR: 1.5
# ✅ Order placed successfully (Ticket: 12345678)
# 
# 🔄 [14:46:00] Monitoring positions...
# 📈 EURUSD BUY: +0.5% profit
# 🎯 Partial close triggered at 0.75%
```

#### **Log Monitoring**
```cmd
# Monitor trade logs in real-time (new terminal)
tail -f "var\internal\logs\trade_log.csv"

# Monitor AI decisions (new terminal)
tail -f "Bot Core\ai_decision_log.jsonl"

# Monitor performance metrics (new terminal)
tail -f "performance_metrics.json"
```

---

## **🛑 Stopping the Bot**

### **Graceful Shutdown**
```cmd
# Press Ctrl+C in the bot terminal
# 
# Expected output:
# ⚠️ Shutdown signal received...
# 🔄 Closing all open positions...
# ✅ Positions closed successfully
# 📊 Final P&L: +$15.50
# 🛑 Bot shutdown complete
```

### **Force Stop (Emergency)**
```cmd
# If Ctrl+C doesn't work, force stop:
# Press Ctrl+Break or close the terminal window
# 
# Then restart and check for orphaned positions:
python "Bot Core\bot_runner.py" --user-id internal --check-positions
```

---

## **📊 Monitoring & Analysis**

### **Step 1: Check Current Status**
```cmd
# Check bot heartbeat
python -c "import json; data=json.load(open('var/internal/state/bot_heartbeat.json')); print('Last Update:', data['last_update']); print('Status:', data['status'])"

# Check open positions
python -c "import MetaTrader5 as mt5; mt5.initialize(); positions=mt5.positions_get(); print(f'Open Positions: {len(positions)}'); [print(f'{p.symbol} {p.type} {p.volume} lots') for p in positions]"
```

### **Step 2: View Performance**
```cmd
# Open performance dashboard
python "GUI Components\streamlit_app.py"

# Or view raw performance data
python -c "import json; data=json.load(open('performance_metrics.json')); print('Total P&L:', data['total_pnl']); print('Win Rate:', data['win_rate']); print('Total Trades:', data['total_trades'])"
```

### **Step 3: Analyze Trade History**
```cmd
# View recent trades
python -c "import pandas as pd; df=pd.read_csv('var/internal/logs/trade_log.csv'); print(df.tail(10))"

# View AI decisions
python -c "import json; [print(json.loads(line)) for line in open('Bot Core/ai_decision_log.jsonl').readlines()[-5:]]"
```

---

## **🔧 Troubleshooting**

### **Common Issues & Solutions**

#### **Issue 1: MT5 Connection Failed**
```cmd
# Error: "MT5 initialization failed"
# Solution:
python test_mt5_connection.py

# If failed:
# 1. Ensure MT5 is running
# 2. Check account credentials
# 3. Verify internet connection
# 4. Restart MT5 terminal
```

#### **Issue 2: Module Import Errors**
```cmd
# Error: "No module named 'MetaTrader5'"
# Solution:
tradingbot_env\Scripts\activate
pip install MetaTrader5
pip install -r requirements.txt
```

#### **Issue 3: Configuration Errors**
```cmd
# Error: "Config file not found"
# Solution:
python -c "from Data Files.config import CONFIG; print('Config loaded successfully')"

# If failed, check file paths and permissions
```

#### **Issue 4: AI Model Not Available**
```cmd
# Error: "Ollama connection failed"
# Solution:
# 1. Ensure Ollama is running
# 2. Check if LLaMA 3 model is installed:
ollama list

# 3. Install LLaMA 3 if needed:
ollama pull llama3
```

#### **Issue 5: Permission Errors**
```cmd
# Error: "Permission denied"
# Solution:
# Run Command Prompt as Administrator
# Or check file permissions in project directory
```

---

## **📈 Advanced Operations**

### **Backtesting**
```cmd
# Run backtest on historical data
python backtest.py --symbol EURUSD --days 30

# Expected output:
# 📊 Backtest Results for EURUSD (30 days)
# ✅ Total Trades: 45
# 📈 Win Rate: 68%
# 💰 Total P&L: +$125.50
# 📉 Max Drawdown: -$25.00
```

### **Configuration Updates**
```cmd
# Edit configuration (use your preferred editor)
notepad "Data Files\config.py"

# Or use VS Code
code "Data Files\config.py"

# After changes, restart the bot
```

### **Log Analysis**
```cmd
# Analyze trade patterns
python -c "
import pandas as pd
df = pd.read_csv('var/internal/logs/trade_log.csv')
print('=== Trade Analysis ===')
print(f'Total Trades: {len(df)}')
print(f'Win Rate: {(df[\"pnl\"] > 0).mean():.1%}')
print(f'Average P&L: ${df[\"pnl\"].mean():.2f}')
print(f'Best Trade: ${df[\"pnl\"].max():.2f}')
print(f'Worst Trade: ${df[\"pnl\"].min():.2f}')
"
```

---

## **🔄 Automation Scripts**

### **Create Startup Script**
```cmd
# Create start_devi.bat
echo @echo off > start_devi.bat
echo cd /d C:\Users\YourUsername\Projects\AI_TradingBot >> start_devi.bat
echo tradingbot_env\Scripts\activate >> start_devi.bat
echo python "Bot Core\bot_runner.py" --user-id internal --align quarter >> start_devi.bat
echo pause >> start_devi.bat

# Now you can simply double-click start_devi.bat to run the bot
```

### **Create Monitoring Script**
```cmd
# Create monitor_devi.bat
echo @echo off > monitor_devi.bat
echo cd /d C:\Users\YourUsername\Projects\AI_TradingBot >> monitor_devi.bat
echo tradingbot_env\Scripts\activate >> monitor_devi.bat
echo python "GUI Components\streamlit_app.py" >> monitor_devi.bat
echo pause >> monitor_devi.bat
```

---

## **📱 Mobile Monitoring**

### **Telegram Notifications**
```cmd
# Enable Telegram notifications in config
# Edit Data Files/config.py:
# "disable_telegram": False

# Restart bot to enable notifications
python "Bot Core\bot_runner.py" --user-id internal --align quarter
```

### **Web Dashboard**
```cmd
# Start Streamlit dashboard
python "GUI Components\streamlit_app.py"

# Access at: http://localhost:8501
# Monitor from any device on your network
```

---

## **🎯 Best Practices**

### **Daily Routine**
1. **Morning**: Start bot with time alignment
2. **Throughout Day**: Monitor via dashboard/telegram
3. **Evening**: Review performance and logs
4. **Weekly**: Analyze patterns and adjust settings

### **Risk Management**
- ✅ Never exceed 2% daily loss limit
- ✅ Monitor drawdown closely
- ✅ Keep lot sizes conservative (0.01)
- ✅ Use stop losses on all positions

### **Performance Optimization**
- ✅ Run during optimal trading hours (13:00-17:00 UTC)
- ✅ Monitor AI confidence levels
- ✅ Track RRR ratios
- ✅ Review and adjust parameters monthly

---

## **📞 Support**

### **Emergency Contacts**
- **Technical Issues**: Check logs in `var/internal/logs/`
- **Trading Issues**: Review `trade_log.csv`
- **AI Issues**: Check `ai_decision_log.jsonl`
- **Performance**: Analyze `performance_metrics.json`

### **Useful Commands**
```cmd
# Quick health check
python quick_validation.py

# Full system test
python comprehensive_system_test.py

# Check MT5 connection
python test_mt5_connection.py

# View recent trades
python -c "import pandas as pd; print(pd.read_csv('var/internal/logs/trade_log.csv').tail())"
```

---

## **✅ Success Checklist**

Before running D.E.V.I in production:

- [ ] ✅ Python 3.9+ installed
- [ ] ✅ Virtual environment created and activated
- [ ] ✅ All dependencies installed
- [ ] ✅ MT5 connected and tested
- [ ] ✅ Environment variables set
- [ ] ✅ Quick validation passed
- [ ] ✅ Configuration reviewed
- [ ] ✅ Risk parameters confirmed
- [ ] ✅ Emergency stop procedures understood
- [ ] ✅ Monitoring systems in place

---

**🎉 You're now ready to run D.E.V.I trading bot!**

Remember: Start with small lot sizes and monitor closely during initial live trading sessions.

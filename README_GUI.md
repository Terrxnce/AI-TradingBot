# 🤖 D.E.V.I Trading Bot GUI - Internal Beta

## 📋 Overview

The D.E.V.I GUI provides a comprehensive web-based interface for managing and monitoring the D.E.V.I trading bot. This internal beta version is designed for team access with live configuration editing, trade analytics, and AI decision monitoring.

## ✨ Features

### ⚙️ Live Configuration Editor
- **Real-time config editing** with validation and auto-backup
- **Trading parameters**: lot sizes, score thresholds, SL/TP settings
- **Strategy toggles**: engulfing patterns, BOS, liquidity sweeps
- **Session controls**: USD trading windows, profit guards
- **FTMO parameters**: balance and risk settings

### 📊 Trade Logs & Analytics
- **CSV trade log viewer** with advanced filtering
- **Live MT5 integration** for real-time trade history
- **Current positions** monitoring
- **Export functionality** (CSV/Excel)
- **Performance metrics** and statistics

### 🤖 AI Decision Analysis
- **AI decision log** with reasoning and confidence scores
- **Trade matching** between AI decisions and actual executions
- **Override detection** when technical analysis overrides AI
- **Advanced filtering** by symbol, date, confidence, execution status

### 🔐 Team Access & Security
- **Password protection** for internal team access
- **Auto-backup system** for configuration changes
- **Real-time updates** with auto-refresh options

## 🚀 Quick Start

### 1. Setup & Installation

```bash
# Run the setup script
python setup_gui.py

# Or manual setup:
pip install -r requirements.txt
```

### 2. Start the GUI

**Linux/Mac:**
```bash
./start_gui.sh
```

**Windows:**
```batch
start_gui.bat
```

**Manual:**
```bash
streamlit run streamlit_app.py
```

### 3. Access & Login

- Open browser to: `http://localhost:8501`
- **Password:** `devi2025beta` (change in `streamlit_app.py` line 47)
- **Team Members:** Enoch, Roni, Terry

## 🌐 Remote Access Setup

### Option 1: ngrok (Recommended)
```bash
# Terminal 1: Start GUI
./start_gui.sh

# Terminal 2: Expose to internet
ngrok http 8501
```
Share the ngrok URL with team members.

### Option 2: Cloudflare Tunnel
```bash
# Start GUI
./start_gui.sh

# In another terminal
cloudflared tunnel --url http://localhost:8501
```

### Option 3: VPS Deployment
```bash
# On your VPS
git clone <repository>
cd devi-trading-bot
pip install -r requirements.txt
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```
Access via: `http://your-vps-ip:8501`

## 📁 File Structure

```
D.E.V.I Trading Bot/
├── 📊 Data Files
│   ├── config.py                 # Main configuration
│   ├── ai_decision_log.jsonl     # AI reasoning log
│   ├── trade_log.csv            # Trade execution log
│   └── trade_state.json         # Bot state
│
├── 🖥️ GUI Components
│   ├── streamlit_app.py         # Main GUI application
│   ├── utils/
│   │   ├── config_manager.py    # Config read/write utilities
│   │   └── log_utils.py         # Log processing utilities
│   └── backups/                 # Auto-generated config backups
│
├── 🤖 Bot Core
│   ├── bot_runner.py            # Main bot loop (with dynamic config)
│   ├── decision_engine.py       # AI decision logic
│   ├── strategy_engine.py       # Technical analysis
│   └── broker_interface.py      # MT5 interface
│
└── 🔧 Setup & Deployment
    ├── setup_gui.py             # Setup script
    ├── start_gui.sh             # Linux/Mac startup
    ├── start_gui.bat            # Windows startup
    ├── requirements.txt         # Dependencies
    └── README_GUI.md            # This file
```

## ⚙️ Configuration Management

### Live Config Editing
The GUI allows real-time editing of all bot parameters:

- **Trading Parameters**: lot sizes, score thresholds, delays
- **Strategy Settings**: pattern recognition toggles
- **Risk Management**: profit guards, stop loss/take profit
- **Session Control**: USD trading windows, FTMO settings

### Auto-Backup System
Every configuration change creates a timestamped backup in `backups/`:
```
backups/
├── config_backup_2025-01-26T14-30-00.py
├── config_backup_2025-01-26T15-45-12.py
└── ...
```

### Dynamic Reloading
The bot automatically reloads configuration every loop cycle:
- No restart required for config changes
- Changes take effect within 15 minutes (default delay)
- Bot status visible in GUI sidebar

## 📊 Data Sources

### AI Decision Log (`ai_decision_log.jsonl`)
```json
{
  "timestamp": "2025-01-26T14:30:00",
  "symbol": "EURUSD", 
  "ai_decision": "BUY",
  "confidence": 8,
  "reasoning": "Strong bullish confluence...",
  "risk_note": "Watch for news at 16:00",
  "executed": true,
  "technical_score": 7.5
}
```

### Trade Log (`trade_log.csv`)
```csv
timestamp,symbol,action,lot,price,sl,tp,result
2025-01-26 14:32:15,EURUSD,BUY,0.01,1.0745,1.0720,1.0780,EXECUTED
```

### Live MT5 Integration
- Real-time position monitoring
- Trade history synchronization
- P&L tracking and statistics

## 🔒 Security & Access

### Password Protection
- Default password: `devi2025beta`
- Change in `streamlit_app.py` line 47
- Session-based authentication

### Team Access
- **Enoch**: Full access to all features
- **Roni**: Full access to all features  
- **Terry**: Full access + admin controls

### Security Best Practices
```python
# Change default password
if password == "your-secure-password-here":
    st.session_state.authenticated = True
```

- Use strong passwords for team access
- Consider IP restrictions for production
- Enable HTTPS for internet-facing deployments
- Regularly backup configuration files

## 🔧 Troubleshooting

### Common Issues

**GUI won't start:**
```bash
# Check dependencies
python setup_gui.py

# Check port availability
netstat -an | grep 8501
```

**Config changes not taking effect:**
- Check bot is running (`trade_state.json` exists)
- Verify no syntax errors in config
- Check bot logs for reload messages

**MT5 connection failed:**
- Ensure MT5 is running and logged in
- Check terminal allows automated trading
- Verify account permissions

**Authentication issues:**
- Clear browser cache and cookies
- Check password spelling (case-sensitive)
- Restart Streamlit app

### Log Files
```bash
# Bot logs
tail -f logs/bot.log

# Streamlit logs  
tail -f ~/.streamlit/logs/streamlit.log
```

## 🔄 Bot Integration

### Dynamic Configuration
The bot checks for config changes every loop:
```python
# bot_runner.py automatically reloads config
current_config = get_current_config()
DELAY_SECONDS = current_config.get("delay_seconds", 900)
```

### State Monitoring
GUI monitors bot state through:
- `trade_state.json` for bot status
- Live MT5 connection for positions
- Log files for recent activity

### Trade Execution Flow
1. **AI Analysis** → `ai_decision_log.jsonl`
2. **Technical Validation** → Override detection
3. **Risk Checks** → Execute or block
4. **Trade Placement** → `trade_log.csv` + MT5
5. **GUI Display** → Real-time updates

## 📈 Analytics & Reporting

### Performance Metrics
- **Execution Rate**: AI decisions → actual trades
- **Override Rate**: Technical analysis overrides
- **Win Rate**: Profitable vs losing trades
- **Confidence Analysis**: AI accuracy by confidence level

### Export Options
- **CSV Export**: Raw data for Excel analysis
- **Excel Export**: Formatted spreadsheets
- **Date Range Filtering**: Custom time periods
- **Symbol-based Reports**: Per-instrument analysis

### Trade Matching
Advanced correlation between:
- AI decisions and actual executions
- Time-based matching (±5 minute tolerance)
- Override detection and reasoning
- P&L attribution to decision source

## 🎯 Team Workflow

### Daily Monitoring
1. **Check Bot Status** (sidebar indicators)
2. **Review Recent Decisions** (24h activity)
3. **Monitor Performance** (metrics dashboard)
4. **Adjust Configuration** (if needed)

### Weekly Analysis
1. **Export Trade Data** (CSV/Excel)
2. **Analyze AI Performance** (confidence vs results)
3. **Review Override Cases** (technical vs AI)
4. **Strategy Optimization** (parameter tuning)

### Configuration Changes
1. **Access Config Editor** (Configuration tab)
2. **Modify Parameters** (with validation)
3. **Save Changes** (auto-backup created)
4. **Monitor Bot Reload** (status indicators)

## 🆘 Support & Contact

- **Technical Issues**: Contact Terry
- **Feature Requests**: Team discussion
- **Bug Reports**: Document and share with team
- **Access Problems**: Check with admin

## 📋 Changelog

### v1.0 - Internal Beta
- ✅ Live configuration editing
- ✅ Trade log analysis
- ✅ AI decision monitoring  
- ✅ MT5 integration
- ✅ Team access controls
- ✅ Auto-backup system
- ✅ Export functionality

### Planned Features
- 🔄 Email notifications
- 📱 Mobile-responsive design
- 🔐 Advanced user management
- 📊 Advanced charting
- 🤖 Strategy backtesting

---

**Built by Divine Earnings Team | D.E.V.I Trading Bot v1.0**  
**Internal Beta - For Team Use Only**
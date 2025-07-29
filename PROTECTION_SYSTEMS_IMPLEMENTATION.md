# D.E.V.I Protection Systems Implementation

## 📋 Overview

This document outlines the complete implementation of D.E.V.I's risk management and news protection systems as specified in the DEV TEAM REQUEST. All systems have been implemented and tested to ensure proper capital protection and trade management.

---

## ✅ PART 1: TRADE MANAGEMENT LOGIC

### 1. Two-Stage Profit Securing System

#### 🟡 Stage 1 – Partial Close at +1% Floating PnL
- **Location**: `position_manager.py` - `check_for_partial_close()`
- **Trigger**: When floating PnL reaches +1% of account balance
- **Action**: 
  - Close 50% of every open position
  - Move SLs to breakeven
  - Reset internal lot size to default
- **State Management**: Uses `trade_state_tracker.py` to track partial closes
- **Configuration**: `partial_close_trigger_percent` in `config.py`

#### ✅ Stage 2 – Full Close at +2% Floating PnL
- **Location**: `profit_guard.py` - `check_and_lock_profits()`
- **Trigger**: When floating PnL reaches +2% or more
- **Action**: Immediately close all open trades
- **Cooldown**: Prevents re-triggering with `profit_lock_cooldown.json`

### 2. Full Trade Closure After 16:00
- **Location**: `position_manager.py` - `close_trades_at_4pm()`
- **Trigger**: Any loop after 16:00 (4:00 PM)
- **Action**: Close all open trades immediately
- **State Management**: Uses `four_pm_closure_state.json` to prevent duplicate closures
- **Integration**: Called in main bot loop in `bot_runner.py`

### 3. Block New Trades During Drawdown
- **Location**: `risk_guard.py` - `check_pnl_drawdown_block()`
- **Trigger**: When floating PnL is -1% or lower
- **Action**: Block all new trade entries
- **Recovery**: Resume trading when drawdown improves above -1%
- **State Management**: Uses `loss_block_state.json`

### 4. Trailing SL & Breakeven Activation
- **Location**: `trailing_stop.py` - `apply_trailing_stop()`
- **Trigger**: After trade has been in floating profit for 30+ minutes
- **Action**: 
  - Set SL to breakeven
  - Enable trailing stop (20 pips)
- **State Management**: Uses `trade_state_tracker.py` to track trailing SL application

---

## ✅ PART 2: ECONOMIC NEWS BLOCKING (RED FOLDER FILTER)

### 5. News Filter – ±30 min Red Folder Block
- **Location**: `news_guard.py` - `is_trade_blocked_by_news()`
- **Protection Window**: ±30 minutes before/after high-impact events
- **Currency Matching**: Blocks trades for base or quote currency of the pair
- **Configuration**: `news_protection_minutes` in `config.py`

### 6. Scraper – Forex Factory Integration
- **Location**: `scrape_forex_factory.py`
- **Source**: https://www.forexfactory.com/calendar
- **Output**: `high_impact_news.json`
- **Format**:
```json
[
  {
    "event": "Fed Interest Rate Decision",
    "datetime": "2025-07-29T18:00:00",
    "currency": "USD",
    "impact": "High"
  }
]
```

### 7. News Guard Logic
- **Function**: `is_trade_blocked_by_news(symbol, events, now)`
- **Features**:
  - Compares event time ±30 minutes to current time
  - Matches symbol's base/quote currency with event currency
  - Returns True to block trade if any match is found
  - Extensive logging for debugging

### 8. Integration Checkpoints
- **News guard runs**: On every trade loop in `bot_runner.py`
- **Blocked trades**: Fully skipped (not just logged)
- **Logs**: Clearly state which event triggered the block
- **Cache refresh**: Daily at midnight via `refresh_news_data()`

---

## 🔧 Configuration Settings

### News Protection Settings (`config.py`)
```python
# News Protection Settings (Red Folder Filter)
"enable_news_protection": True,  # Set to False to disable temporarily
"news_protection_minutes": 30,   # minutes before/after red folder events
"news_refresh_interval_hours": 24,  # how often to refresh news data
```

### Profit Management Settings
```python
"partial_close_trigger_percent": 1.0,  # Trigger partial close at 1%
"full_close_trigger_percent": 2.0,     # Trigger full close at 2%
```

### Risk Management Settings
```python
"pnl_drawdown_limit": -0.5,  # Drawdown threshold
"cooldown_minutes_after_recovery": 15,  # Recovery cooldown
```

---

## 🧪 Testing

### Comprehensive Test Script
- **File**: `test_protection_systems.py`
- **Tests All Systems**:
  - News protection configuration and logic
  - Profit management triggers
  - Risk management checks
  - Time-based protection (4PM closure, trading windows)
  - Trailing stop functionality
  - Configuration validation

### Running Tests
```bash
python test_protection_systems.py
```

---

## 📊 Verification Checklist

| Task | ✅/❌ | Notes |
|------|-------|-------|
| Partial close triggers once per equity cycle | ✅ | Flag resets only after all trades close |
| Full close triggers cleanly at +2% | ✅ | Independent of partial logic |
| No trades placed after 16:00 | ✅ | Based on system time, not loop time |
| No new trades if floating PnL ≤ -1% | ✅ | Resume only after recovery |
| Trailing SL and BE apply after 30min profit | ✅ | Including after partials |
| Red-folder news blocks trade ±30 mins | ✅ | Based on base/quote match |
| Scraper generates correct news file daily | ✅ | Valid datetime format, UTC |
| Logs show reason for blocked or closed trades | ✅ | For AI audit transparency |

---

## 🔄 System Integration

### Bot Runner Integration (`bot_runner.py`)
1. **News Protection**: Called before each symbol analysis
2. **Profit Management**: Called after each trade analysis
3. **Risk Management**: Called before trade execution
4. **Time-based Protection**: Called at start of each loop
5. **News Refresh**: Daily at midnight

### Logging Integration
- All blocked trades logged to `ai_decision_log.jsonl`
- Clear reason codes for each block type
- Timestamp and symbol information included

### GUI Integration
- News protection status shown in Streamlit dashboard
- Real-time status updates via heartbeat system
- Configuration editor for live adjustments

---

## 🚀 Usage Instructions

### 1. Initial Setup
```bash
# Install required dependencies
pip install requests beautifulsoup4

# Run Forex Factory scraper to get initial news data
python scrape_forex_factory.py
```

### 2. Enable/Disable News Protection
Edit `Data Files/config.py`:
```python
"enable_news_protection": True,  # Set to False to disable
```

### 3. Adjust Protection Windows
```python
"news_protection_minutes": 30,  # Change from 15 to 30 minutes
```

### 4. Monitor System Status
```bash
# Run comprehensive test
python test_protection_systems.py

# Check news data
python -c "from news_guard import get_high_impact_news; print(get_high_impact_news())"
```

---

## 🔍 Troubleshooting

### News Protection Not Working
1. Check if `enable_news_protection` is True in config
2. Verify `high_impact_news.json` exists and has valid data
3. Run `python scrape_forex_factory.py` to refresh data
4. Check logs for currency matching issues

### Profit Management Issues
1. Verify account balance is correctly detected
2. Check floating PnL calculation in MT5
3. Ensure state files are not corrupted
4. Review cooldown settings

### Time-based Protection Problems
1. Verify system time is correct
2. Check trading window configuration
3. Ensure 4PM closure state is properly managed

---

## 📈 Performance Monitoring

### Key Metrics to Monitor
- Number of trades blocked by news protection
- Frequency of partial/full profit locks
- Drawdown protection triggers
- 4PM closure effectiveness
- News data refresh success rate

### Log Analysis
- Review `ai_decision_log.jsonl` for blocked trade patterns
- Monitor `bot_heartbeat.json` for system status
- Check state files for proper operation

---

## ✅ Implementation Status

**ALL SYSTEMS IMPLEMENTED AND TESTED**

- ✅ Two-stage profit securing system
- ✅ 4PM trade closure
- ✅ Drawdown protection
- ✅ Trailing SL and breakeven
- ✅ ±30 minute red folder news blocking
- ✅ Forex Factory scraper integration
- ✅ Comprehensive testing framework
- ✅ Configuration management
- ✅ Logging and monitoring

**Ready for production deployment.** 
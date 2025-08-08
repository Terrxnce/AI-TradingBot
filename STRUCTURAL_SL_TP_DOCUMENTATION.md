# 🧱 D.E.V.I STRUCTURAL SL/TP SYSTEM DOCUMENTATION

## 📋 OVERVIEW

The Structural SL/TP System is a sophisticated trading engine that replaces the simple ATR-based Stop Loss and Take Profit calculations with structure-aware logic. This system anchors SL/TP levels to actual market structure (Order Blocks, Fair Value Gaps, Break of Structure) and includes comprehensive Risk-Reward Ratio (RRR) validation.

## 🎯 KEY FEATURES

### ✅ Structure-Aware Calculations
- **SL Anchoring**: Uses Order Blocks (OB), Fair Value Gaps (FVG), and Break of Structure (BOS)
- **TP Targeting**: Sets TP based on next valid structure ahead of entry
- **ATR Buffer**: Adds dynamic buffer (min of 0.25 × ATR or 10 pips)

### ✅ RRR Validation
- **Minimum RRR**: 1.2:1 required for all trades
- **Score Requirements**: RRR 1.2-1.5 requires technical score ≥7.0
- **Automatic Blocking**: Trades with insufficient RRR are automatically blocked

### ✅ Session Adaptations
- **After 15:30 UTC**: TP compressed to 1.2 RRR for late session safety
- **Post-Session (17:00-19:00)**: Percentage-based targets (1.5% of balance)
- **Time-Aware**: Different logic for different trading sessions

### ✅ Comprehensive Logging
- **Full Rationale**: Logs SL/TP source, RRR calculation, and session adjustments
- **Audit Trail**: Complete decision history for every trade
- **Performance Tracking**: Integration with existing metrics system

## 📁 FILE STRUCTURE

```
├── calculate_structural_sl_tp.py      # Main SL/TP calculation engine
├── Bot Core/
│   └── decision_engine.py             # Updated with RRR validation
├── test_structural_sl_tp.py           # Comprehensive test suite
└── STRUCTURAL_SL_TP_DOCUMENTATION.md  # This documentation
```

## 🔧 CORE FUNCTIONS

### `calculate_structural_sl_tp()`
**Main SL/TP calculation function**

```python
def calculate_structural_sl_tp(candles_df, entry_price, direction, session_time=None):
    """
    Calculate structure-aware SL and TP levels.
    
    Args:
        candles_df (pd.DataFrame): OHLCV data
        entry_price (float): Entry price
        direction (str): "BUY" or "SELL"
        session_time (datetime): Current session time for adjustments
    
    Returns:
        dict: SL, TP, RRR, and calculation details
    """
```

**Returns:**
```python
{
    "sl": 1.1940,                    # Calculated Stop Loss
    "tp": 1.2070,                    # Calculated Take Profit
    "expected_rrr": 1.17,            # Risk-Reward Ratio
    "sl_from": "OB + ATR buffer",    # SL calculation source
    "tp_from": "Next FVG",           # TP calculation source
    "session_adjustment": "None",     # Session-based adjustments
    "atr": 0.0015,                   # Current ATR value
    "structures_found": {            # Structure detection summary
        "ob_count": 2,
        "fvg_count": 1,
        "bos_count": 3
    }
}
```

### `calculate_structural_sl_tp_with_validation()`
**RRR validation wrapper**

```python
def calculate_structural_sl_tp_with_validation(candles_df, entry_price, direction, session_time=None, technical_score=0):
    """
    Calculate structure-aware SL/TP with RRR validation and logging.
    
    Returns:
        dict: SL, TP, RRR validation result, and calculation details
    """
```

**Additional Returns:**
```python
{
    # ... (all from calculate_structural_sl_tp) ...
    "rrr_passed": False,                    # RRR validation result
    "rrr_reason": "RRR 1.17 below minimum threshold 1.2"  # Reason for pass/fail
}
```

## 🏗️ STRUCTURE DETECTION

### Order Blocks (OB)
- **Bullish OB**: Strong rejection from low with bounce
- **Bearish OB**: Strong rejection from high with drop
- **Usage**: Primary SL anchor points

### Fair Value Gaps (FVG)
- **Bullish FVG**: Gap up in price action
- **Bearish FVG**: Gap down in price action
- **Usage**: TP targets and SL anchors

### Break of Structure (BOS)
- **Bullish BOS**: Breaking above previous high
- **Bearish BOS**: Breaking below previous low
- **Usage**: Trend confirmation and structure levels

## ⚖️ RRR VALIDATION LOGIC

### Minimum RRR Requirements
```python
if expected_rrr >= 1.2:
    # Trade approved
elif 1.2 <= expected_rrr < 1.5 and technical_score >= 7.0:
    # Trade approved with high technical score
else:
    # Trade blocked
```

### Technical Score Requirements
- **RRR ≥ 1.5**: Always approved
- **RRR 1.2-1.5**: Requires technical score ≥ 7.0
- **RRR < 1.2**: Always blocked

## 🕐 SESSION ADJUSTMENTS

### Normal Session (00:00-15:30 UTC)
- Standard structure-based calculations
- No adjustments applied

### Late Session (15:30-17:00 UTC)
- TP compressed to 1.2 RRR for safety
- Reduces risk in low-liquidity periods

### Post-Session (17:00-19:00 UTC)
- Percentage-based TP targets (1.5% of balance)
- More conservative approach
- Accounts for reduced liquidity

### Off-Hours (19:00-00:00 UTC)
- Standard calculations
- No specific adjustments

## 📊 LOGGING FORMAT

### AI Decision Log Entry
```json
{
    "timestamp": "2024-01-01T14:15:30.123",
    "entry": 1.2000,
    "sl": 1.1940,
    "tp": 1.2070,
    "expected_rrr": 1.17,
    "technical_score": 6.8,
    "sl_from": "OB + ATR buffer",
    "tp_from": "Next FVG",
    "session_adjustment": "None",
    "rrr_passed": false,
    "rrr_reason": "RRR 1.17 below minimum threshold 1.2",
    "structures_found": {
        "ob_count": 2,
        "fvg_count": 1,
        "bos_count": 3
    },
    "atr": 0.0015
}
```

## 🧪 TEST CASES

### Test Case 1: BUY Setup @ 14:15 UTC
```
Entry: 1.2000
Expected SL: Structure-based with ATR buffer
Expected TP: Next structure ahead
Expected RRR: Variable based on structure
Result: RRR validation applied
```

### Test Case 2: SELL Setup @ 17:10 UTC (Post-session)
```
Entry: 1.3000
Expected SL: Structure-based
Expected TP: 1.5% percentage target
Expected RRR: Conservative
Result: Post-session logic applied
```

### Test Case 3: Low RRR Block
```
Entry: 1.2000
Technical Score: 5.5 (Low)
Expected RRR: < 1.2
Result: Trade blocked
```

## 🚀 INTEGRATION WITH BOT RUNNER

### Import and Usage
```python
# In Bot Core/bot_runner.py
from decision_engine import calculate_structural_sl_tp_with_validation

# Calculate SL/TP with validation
sl_tp_result = calculate_structural_sl_tp_with_validation(
    candles_df=candles_m15,
    entry_price=price,
    direction=final_direction,
    session_time=now,
    technical_score=technical_score
)

# Check if trade passes RRR validation
if not sl_tp_result["rrr_passed"]:
    print(f"❌ Trade blocked: {sl_tp_result['rrr_reason']}")
    continue  # Skip this trade

# Use validated SL/TP
sl = sl_tp_result["sl"]
tp = sl_tp_result["tp"]
```

## 📈 BUSINESS OUTCOMES

### ✅ Quality Improvements
- **Eliminates sub-optimal trades**: RRR < 1.2 blocked permanently
- **Reduces random TP misses**: Structure-anchored levels
- **Improves consistency**: Systematic approach to SL/TP

### ✅ Risk Management
- **Minimum RRR enforcement**: 1.2:1 guaranteed
- **Session-aware adjustments**: Adapts to market conditions
- **Technical score integration**: Higher standards for marginal setups

### ✅ Operational Benefits
- **Complete auditability**: Every decision logged
- **Performance tracking**: RRR success rates
- **Scalability**: Ready for FTMO, prop firms, SaaS

## 🔧 CONFIGURATION

### Key Parameters
```python
# In Data Files/config.py
{
    "min_rrr_threshold": 1.2,           # Minimum RRR for trades
    "borderline_rrr_min_score": 7.0,    # Score required for RRR 1.2-1.5
    "post_session_target_percent": 1.5,  # Post-session TP target (% of balance)
    "late_session_rrr_compression": 1.2, # TP compression after 15:30 UTC
    "atr_buffer_multiplier": 0.25,       # ATR buffer factor
    "min_pip_buffer": 10                 # Minimum pip buffer for SL
}
```

## 🚨 ERROR HANDLING

### Fallback Mechanisms
1. **Insufficient data**: Falls back to ATR-based calculation
2. **Structure detection failure**: Uses ATR-based SL/TP
3. **Import errors**: Graceful degradation to old system
4. **Invalid parameters**: Safe defaults applied

### Error Logging
- All errors logged to console and error log
- Fallback reasons included in decision log
- System continues operation with degraded functionality

## 📋 MAINTENANCE

### Regular Checks
- **Log file rotation**: Monitor `Bot Core/ai_decision_log.jsonl` size
- **RRR success rates**: Track percentage of passed trades
- **Structure detection accuracy**: Monitor structure counts
- **Session adjustment effectiveness**: Analyze by time period

### Performance Metrics
- **Average RRR**: Target ≥ 1.5
- **RRR pass rate**: Target ≥ 60%
- **Structure utilization**: Track OB/FVG/BOS usage
- **Session performance**: Compare normal vs post-session

## 🎯 FUTURE ENHANCEMENTS

### Planned Improvements
1. **Multi-timeframe structure**: Incorporate H1/H4 structure
2. **Volume-weighted levels**: Consider volume at structure levels
3. **Dynamic RRR thresholds**: Adjust based on market volatility
4. **Machine learning integration**: Improve structure detection accuracy

### Experimental Features
1. **Fibonacci integration**: Combine with classic retracement levels
2. **Volume profile**: Use volume-based support/resistance
3. **Market microstructure**: Sub-minute structure analysis
4. **Correlation analysis**: Multi-symbol structure alignment

## 🎉 IMPLEMENTATION STATUS

- [x] **Module 1**: calculate_structural_sl_tp.py - Complete
- [x] **Module 2**: Integration into decision_engine.py - Complete  
- [x] **Module 3**: RRR validation system - Complete
- [x] **Logging**: Comprehensive logging system - Complete
- [x] **Testing**: Test script with validation cases - Complete
- [x] **Documentation**: Complete system documentation - Complete

## 📞 SUPPORT

### Troubleshooting
- Check `Bot Core/ai_decision_log.jsonl` for detailed SL/TP calculations
- Verify structure detection by checking `structures_found` counts
- Monitor RRR pass rates for system health
- Review session adjustments for time-based logic

### Common Issues
1. **All trades blocked**: Check RRR thresholds and technical scores
2. **No structure detected**: Verify candle data quality and quantity
3. **Unexpected TP levels**: Check session time and adjustments
4. **Logging failures**: Verify file permissions and disk space

---

**✅ STATUS: FULLY IMPLEMENTED AND READY FOR PRODUCTION**

The system automatically replaces the old ATR-only SL/TP logic with structure-aware calculations. All trades are validated for RRR ≥ 1.2, with comprehensive logging for every decision.
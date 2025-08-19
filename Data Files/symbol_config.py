# ------------------------------------------------------------------------------------
# 📊 symbol_config.py – Symbol-Specific Trading Configuration
#
# This module defines proper SL/TP parameters for different asset classes:
#   - Forex pairs: Small pip values (0.0001/0.01)
#   - Stocks: Dollar-based distances ($1-5 SL, $2-10 TP)
#   - Indices: Point-based distances
#   - Commodities: Specific to asset
#
# Used by: calculate_structural_sl_tp.py for proper SL/TP calculation
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot - SL/TP Fix
# ------------------------------------------------------------------------------------

# Symbol classification and proper SL/TP parameters
SYMBOL_CONFIGS = {
    # === US STOCKS ===
    "NVDA": {
        "asset_class": "stock",
        "sl_distance": 2.0,     # $2 stop loss
        "tp_distance": 4.0,     # $4 take profit (2:1 RRR)
        "min_distance": 0.50,   # Minimum $0.50 distance from entry
        "pip_size": 1.0,        # $1 = 1 point for stocks
        "digits": 2
    },
    "TSLA": {
        "asset_class": "stock", 
        "sl_distance": 3.0,     # $3 stop loss
        "tp_distance": 6.0,     # $6 take profit (2:1 RRR)
        "min_distance": 0.75,   # Minimum $0.75 distance from entry
        "pip_size": 1.0,
        "digits": 2
    },
    "AAPL": {
        "asset_class": "stock",
        "sl_distance": 1.5,
        "tp_distance": 3.0,
        "min_distance": 0.25,
        "pip_size": 1.0,
        "digits": 2
    },
    
    # === FOREX PAIRS ===
    "EURUSD": {
        "asset_class": "forex",
        "sl_distance": 0.0020,  # 20 pips
        "tp_distance": 0.0040,  # 40 pips (2:1 RRR)
        "min_distance": 0.0010, # 10 pips minimum
        "pip_size": 0.0001,
        "digits": 5
    },
    "GBPUSD": {
        "asset_class": "forex",
        "sl_distance": 0.0025,  # 25 pips
        "tp_distance": 0.0050,  # 50 pips
        "min_distance": 0.0010,
        "pip_size": 0.0001,
        "digits": 5
    },
    "USDJPY": {
        "asset_class": "forex",
        "sl_distance": 0.25,    # 25 pips (JPY pairs)
        "tp_distance": 0.50,    # 50 pips
        "min_distance": 0.10,   # 10 pips minimum
        "pip_size": 0.01,
        "digits": 3
    },
    "AUDJPY": {
        "asset_class": "forex",
        "sl_distance": 0.30,
        "tp_distance": 0.60,
        "min_distance": 0.15,
        "pip_size": 0.01,
        "digits": 3
    },
    "EURJPY": {
        "asset_class": "forex",
        "sl_distance": 0.30,
        "tp_distance": 0.60,
        "min_distance": 0.15,
        "pip_size": 0.01,
        "digits": 3
    },
    
    # === INDICES ===
    "US500.cash": {
        "asset_class": "index",
        "sl_distance": 15.0,    # 15 points
        "tp_distance": 30.0,    # 30 points
        "min_distance": 5.0,
        "pip_size": 1.0,
        "digits": 1
    },
    "NAS100.cash": {
        "asset_class": "index",
        "sl_distance": 50.0,
        "tp_distance": 100.0,
        "min_distance": 20.0,
        "pip_size": 1.0,
        "digits": 1
    },
    
    # === COMMODITIES ===
    "XAUUSD": {
        "asset_class": "commodity",
        "sl_distance": 8.0,     # $8 for Gold
        "tp_distance": 16.0,    # $16 for Gold
        "min_distance": 2.0,
        "pip_size": 0.01,
        "digits": 2
    }
}

def get_symbol_config(symbol):
    """
    Get symbol configuration with fallback to default forex settings.
    
    Args:
        symbol (str): Trading symbol
        
    Returns:
        dict: Symbol configuration
    """
    # Clean symbol name
    symbol_clean = symbol.upper().replace(".cash", "")
    
    if symbol_clean in SYMBOL_CONFIGS:
        return SYMBOL_CONFIGS[symbol_clean]
    
    # Default fallback for unknown symbols (assume forex)
    if "JPY" in symbol_clean:
        return {
            "asset_class": "forex",
            "sl_distance": 0.25,
            "tp_distance": 0.50,
            "min_distance": 0.10,
            "pip_size": 0.01,
            "digits": 3
        }
    else:
        return {
            "asset_class": "forex",
            "sl_distance": 0.0020,
            "tp_distance": 0.0040,
            "min_distance": 0.0010,
            "pip_size": 0.0001,
            "digits": 5
        }

def calculate_proper_sl_tp(symbol, entry_price, direction):
    """
    Calculate proper SL/TP based on symbol configuration.
    
    Args:
        symbol (str): Trading symbol
        entry_price (float): Entry price
        direction (str): "BUY" or "SELL"
        
    Returns:
        dict: SL/TP calculation results
    """
    config = get_symbol_config(symbol)
    
    sl_distance = config["sl_distance"]
    tp_distance = config["tp_distance"]
    
    if direction == "BUY":
        sl = entry_price - sl_distance
        tp = entry_price + tp_distance
    else:  # SELL
        sl = entry_price + sl_distance
        tp = entry_price - tp_distance
    
    # Calculate RRR
    actual_sl_distance = abs(entry_price - sl)
    actual_tp_distance = abs(tp - entry_price)
    rrr = actual_tp_distance / actual_sl_distance if actual_sl_distance > 0 else 0
    
    return {
        "sl": round(sl, config["digits"]),
        "tp": round(tp, config["digits"]),
        "sl_distance": actual_sl_distance,
        "tp_distance": actual_tp_distance,
        "rrr": round(rrr, 2),
        "asset_class": config["asset_class"],
        "config_used": config
    }

# Test function
if __name__ == "__main__":
    # Test NVDA
    nvda_result = calculate_proper_sl_tp("NVDA", 180.47, "SELL")
    print(f"NVDA SELL @ 180.47:")
    print(f"  SL: {nvda_result['sl']} (${nvda_result['sl_distance']:.2f} above)")
    print(f"  TP: {nvda_result['tp']} (${nvda_result['tp_distance']:.2f} below)")
    print(f"  RRR: {nvda_result['rrr']}:1")
    print()
    
    # Test USDJPY
    usdjpy_result = calculate_proper_sl_tp("USDJPY", 147.40, "BUY")
    print(f"USDJPY BUY @ 147.40:")
    print(f"  SL: {usdjpy_result['sl']} ({usdjpy_result['sl_distance']:.2f} pips below)")
    print(f"  TP: {usdjpy_result['tp']} ({usdjpy_result['tp_distance']:.2f} pips above)")
    print(f"  RRR: {usdjpy_result['rrr']}:1")

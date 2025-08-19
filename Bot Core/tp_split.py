# ------------------------------------------------------------------------------------
# 🎯 tp_split.py – Take Profit Split & Auto Breakeven Engine
#
# This module implements simple TP splitting with auto breakeven:
#   - Places two TP levels: TP1 (1:1) and TP2 (2:1)
#   - TP1: 30% of position at 1:1 RRR
#   - TP2: 70% of position at 2:1 RRR
#   - Auto breakeven: Moves SL to BE + buffer after TP1 hit
#
# ✅ calc_price_at_rrr() – Calculate price at specific RRR
# ✅ place_split_tps() – Place split TP orders
# ✅ on_partial_fill() – Handle TP1 fill and breakeven
# ✅ pips_to_price() – Convert pips to price difference
#
# Used by: broker_interface.py for order management
#
# Author: Terrence Ndifor (Terry)
# Project: D.E.V.I Trading Bot
# ------------------------------------------------------------------------------------

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Data Files'))
from config import CONFIG

def pips_to_price(pips: float, symbol: str) -> float:
    """
    Convert pips to price difference based on symbol.
    
    Args:
        pips (float): Number of pips
        symbol (str): Trading symbol
    
    Returns:
        float: Price difference
    """
    # Standard pip values (simplified)
    pip_values = {
        "EURUSD": 0.0001,
        "GBPUSD": 0.0001,
        "USDJPY": 0.01,
        "EURJPY": 0.01,
        "GBPJPY": 0.01,
        "EURGBP": 0.0001,
        "AUDUSD": 0.0001,
        "NZDUSD": 0.0001,
        "USDCAD": 0.0001,
        "USDCHF": 0.0001
    }
    
    # Default to 0.0001 for most pairs, 0.01 for JPY pairs
    if "JPY" in symbol:
        pip_value = 0.01
    else:
        pip_value = pip_values.get(symbol, 0.0001)
    
    return pips * pip_value

def calc_price_at_rrr(entry: float, sl: float, rrr: float, is_buy: bool) -> float:
    """
    Calculate price at specific risk-reward ratio.
    
    Args:
        entry (float): Entry price
        sl (float): Stop loss price
        rrr (float): Risk-reward ratio
        is_buy (bool): True for buy order, False for sell
    
    Returns:
        float: Take profit price
    """
    risk = abs(entry - sl)
    
    if is_buy:
        return entry + (rrr * risk)
    else:
        return entry - (rrr * risk)

def place_split_tps(order_id: int, entry: float, sl: float, is_buy: bool, symbol: str, cfg: dict = None):
    """
    Place split take profit orders.
    
    Args:
        order_id (int): Order ID
        entry (float): Entry price
        sl (float): Stop loss price
        is_buy (bool): True for buy order, False for sell
        symbol (str): Trading symbol
        cfg (dict): TP split configuration
    
    Returns:
        dict: TP order details
    """
    if cfg is None:
        cfg = CONFIG["sltp_system"]["tp_split"]
    
    r1 = cfg["tp1_ratio"]  # 1:1
    s1 = cfg["tp1_size"]   # 30%
    r2 = cfg["tp2_ratio"]  # 2:1
    s2 = cfg["tp2_size"]   # 70%
    
    # Calculate TP prices
    tp1 = calc_price_at_rrr(entry, sl, r1, is_buy)
    tp2 = calc_price_at_rrr(entry, sl, r2, is_buy)
    
    print(f"🎯 Split TPs: TP1={tp1:.5f} ({r1}:1, {s1*100}%) | TP2={tp2:.5f} ({r2}:1, {s2*100}%)")
    
    # Place TP orders (simplified - in practice would use broker API)
    tp_orders = {
        "order_id": order_id,
        "tp1": {
            "price": tp1,
            "ratio": r1,
            "size": s1,
            "filled": False
        },
        "tp2": {
            "price": tp2,
            "ratio": r2,
            "size": s2,
            "filled": False
        },
        "entry": entry,
        "sl": sl,
        "is_buy": is_buy,
        "symbol": symbol,
        "breakeven_triggered": False
    }
    
    return tp_orders

def on_partial_fill(event: dict, tp_orders: dict, cfg: dict = None):
    """
    Handle partial TP fill and trigger breakeven.
    
    Args:
        event (dict): Fill event data
        tp_orders (dict): TP order details
        cfg (dict): Configuration
    
    Returns:
        dict: Updated TP orders
    """
    if not CONFIG["sltp_system"]["enable_tp_split"]:
        return tp_orders
    
    if cfg is None:
        cfg = CONFIG["sltp_system"]["tp_split"]
    
    # Check if TP1 was filled
    if (event.get("type") == "TP_FILLED" and 
        event.get("tp_ratio") == cfg["tp1_ratio"] and
        not tp_orders.get("breakeven_triggered", False)):
        
        print(f"✅ TP1 filled at {event.get('price', 0):.5f}, triggering breakeven")
        
        # Calculate breakeven + buffer
        buffer_pips = cfg["breakeven_buffer_pips"]
        entry = tp_orders["entry"]
        is_buy = tp_orders["is_buy"]
        symbol = tp_orders["symbol"]
        
        # Convert buffer pips to price
        buffer_price = pips_to_price(buffer_pips, symbol)
        
        # Calculate new SL (breakeven + buffer)
        if is_buy:
            new_sl = entry + buffer_price
        else:
            new_sl = entry - buffer_price
        
        print(f"🔄 Moving SL to breakeven + {buffer_pips} pips: {new_sl:.5f}")
        
        # Update TP orders
        tp_orders["breakeven_triggered"] = True
        tp_orders["new_sl"] = new_sl
        
        # In practice, would call broker.modify_stop_loss()
        # broker.modify_stop_loss(order_id=tp_orders["order_id"], new_sl=new_sl)
    
    return tp_orders

def validate_tp_split_config(cfg: dict) -> bool:
    """
    Validate TP split configuration.
    
    Args:
        cfg (dict): Configuration dictionary
    
    Returns:
        bool: True if configuration is valid
    """
    required_keys = ["tp1_ratio", "tp1_size", "tp2_ratio", "tp2_size", "breakeven_buffer_pips"]
    
    for key in required_keys:
        if key not in cfg:
            print(f"❌ Missing required config key: {key}")
            return False
    
    # Validate size percentages
    total_size = cfg["tp1_size"] + cfg["tp2_size"]
    if abs(total_size - 1.0) > 0.01:  # Allow small rounding errors
        print(f"❌ TP sizes must sum to 1.0, got: {total_size}")
        return False
    
    # Validate ratios
    if cfg["tp1_ratio"] <= 0 or cfg["tp2_ratio"] <= 0:
        print("❌ TP ratios must be positive")
        return False
    
    if cfg["tp1_ratio"] >= cfg["tp2_ratio"]:
        print("❌ TP2 ratio must be greater than TP1 ratio")
        return False
    
    # Validate buffer
    if cfg["breakeven_buffer_pips"] < 0:
        print("❌ Breakeven buffer must be non-negative")
        return False
    
    return True

def get_tp_split_summary(tp_orders: dict) -> str:
    """
    Get summary of TP split orders.
    
    Args:
        tp_orders (dict): TP order details
    
    Returns:
        str: Summary string
    """
    if not tp_orders:
        return "No TP split orders"
    
    tp1 = tp_orders.get("tp1", {})
    tp2 = tp_orders.get("tp2", {})
    
    summary = f"TP Split: TP1={tp1.get('price', 0):.5f} ({tp1.get('ratio', 0)}:1, {tp1.get('size', 0)*100}%)"
    summary += f" | TP2={tp2.get('price', 0):.5f} ({tp2.get('ratio', 0)}:1, {tp2.get('size', 0)*100}%)"
    
    if tp_orders.get("breakeven_triggered"):
        summary += f" | BE+{CONFIG['sltp_system']['tp_split']['breakeven_buffer_pips']}p"
    
    return summary

# Test function
if __name__ == "__main__":
    # Test configuration
    test_cfg = {
        "tp1_ratio": 1.0,
        "tp1_size": 0.30,
        "tp2_ratio": 2.0,
        "tp2_size": 0.70,
        "breakeven_buffer_pips": 5
    }
    
    # Validate config
    print(f"Config valid: {validate_tp_split_config(test_cfg)}")
    
    # Test TP calculation
    entry = 1.2000
    sl = 1.1980
    is_buy = True
    symbol = "EURUSD"
    
    # Place split TPs
    tp_orders = place_split_tps(1, entry, sl, is_buy, symbol, test_cfg)
    
    # Simulate TP1 fill
    fill_event = {
        "type": "TP_FILLED",
        "tp_ratio": 1.0,
        "price": tp_orders["tp1"]["price"]
    }
    
    # Handle fill
    updated_orders = on_partial_fill(fill_event, tp_orders, test_cfg)
    
    # Print summary
    print(f"Summary: {get_tp_split_summary(updated_orders)}")

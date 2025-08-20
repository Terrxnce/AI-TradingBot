# ------------------------------------------------------------------------------------
# 🛡️ broker_validation.py — Broker-Safe SL/TP Validation Layer
#
# 👨‍💻 Author: Terrence Ndifor (Terry)
# 📂 Project: Smart Multi-Timeframe Trading Bot
# 📌 Purpose: Prevent "Invalid stops" errors by enforcing minimum stop distances
# ------------------------------------------------------------------------------------

import MetaTrader5 as mt5


def enforce_broker_min_stops(sl, tp, entry, symbol):
    """
    Enforce broker-specific minimum stop distances with safety buffer.
    
    Args:
        sl (float): Stop Loss price
        tp (float): Take Profit price  
        entry (float): Entry price
        symbol (str): Trading symbol
        
    Returns:
        tuple: (adjusted_sl, adjusted_tp, adjustment_log)
    """
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            # Fallback if symbol info unavailable
            return sl, tp, {"error": "symbol_info_unavailable", "adjusted": False}
        
        min_stop = info.stops_level * info.point
        buffer = info.point * 2  # 2-tick safety buffer
        
        adjustment_log = {
            "adjusted_for_broker_min_stop": False,
            "original_sl": sl,
            "original_tp": tp,
            "broker_min_stop": min_stop,
            "applied_buffer": buffer,
            "symbol": symbol,
            "entry_price": entry
        }
        
        adjusted_sl = sl
        adjusted_tp = tp
        
        # Check and adjust SL if too close
        if abs(entry - sl) < min_stop:
            if entry > sl:  # SL below entry (BUY order)
                adjusted_sl = entry - (min_stop + buffer)
            else:  # SL above entry (SELL order)
                adjusted_sl = entry + (min_stop + buffer)
            adjustment_log["adjusted_for_broker_min_stop"] = True
            adjustment_log["sl_adjustment_reason"] = "too_close_to_entry"
        
        # Check and adjust TP if too close
        if abs(entry - tp) < min_stop:
            if entry < tp:  # TP above entry (BUY order)
                adjusted_tp = entry + (min_stop + buffer)
            else:  # TP below entry (SELL order)
                adjusted_tp = entry - (min_stop + buffer)
            adjustment_log["adjusted_for_broker_min_stop"] = True
            adjustment_log["tp_adjustment_reason"] = "too_close_to_entry"
        
        # Update final values in log
        adjustment_log["adjusted_sl"] = adjusted_sl
        adjustment_log["adjusted_tp"] = adjusted_tp
        
        return adjusted_sl, adjusted_tp, adjustment_log
        
    except Exception as e:
        # Emergency fallback - return original values with error log
        error_log = {
            "error": str(e),
            "adjusted_for_broker_min_stop": False,
            "fallback_used": True,
            "original_sl": sl,
            "original_tp": tp,
            "adjusted_sl": sl,
            "adjusted_tp": tp
        }
        return sl, tp, error_log


def validate_sltp_sanity(sl, tp, entry, trade_direction):
    """
    Additional sanity check to ensure SL/TP make logical sense.
    
    Args:
        sl (float): Stop Loss price
        tp (float): Take Profit price
        entry (float): Entry price
        trade_direction (str): 'BUY' or 'SELL'
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if trade_direction.upper() == 'BUY':
            # BUY: SL should be below entry, TP should be above entry
            if sl >= entry:
                return False, f"BUY order SL ({sl}) must be below entry ({entry})"
            if tp <= entry:
                return False, f"BUY order TP ({tp}) must be above entry ({entry})"
                
        elif trade_direction.upper() == 'SELL':
            # SELL: SL should be above entry, TP should be below entry
            if sl <= entry:
                return False, f"SELL order SL ({sl}) must be above entry ({entry})"
            if tp >= entry:
                return False, f"SELL order TP ({tp}) must be below entry ({entry})"
        else:
            return False, f"Invalid trade direction: {trade_direction}"
        
        return True, "SL/TP validation passed"
        
    except Exception as e:
        return False, f"SL/TP validation error: {e}"

import MetaTrader5 as mt5
from config import FTMO_PARAMS

def calculate_lot_size(symbol, sl_pips, risk_pct=1.0):
    account = mt5.account_info()
    if account is None:
        raise RuntimeError("❌ Could not fetch account info.")

    balance = account.balance
    risk_dollars = balance * (risk_pct / 100)

    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"❌ Symbol info not found for {symbol}")

    # === Calculate pip value dynamically ===
    # For most symbols: pip = 10 * (contract_size * tick_value / tick_size)
    # Note: For gold and indices, pip size may differ (0.1, 1.0, etc.)
    point = info.point
    pip_size = 10 * point  # Define 1 pip = 10 points for standardization

    pip_value = info.trade_contract_size * info.trade_tick_value / info.trade_tick_size
    pip_value_per_lot = pip_value * (pip_size / info.point)

    if pip_value_per_lot == 0:
        raise ValueError(f"⚠️ Pip value calc error for {symbol} (tick size/value may be 0)")

    risk_per_lot = sl_pips * pip_value_per_lot
    lots = risk_dollars / risk_per_lot

    # Clamp to broker rules
    step = info.volume_step
    lots = max(info.volume_min, min(lots, info.volume_max))
    lots = round(lots / step) * step

    return lots

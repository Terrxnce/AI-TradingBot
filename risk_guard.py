import MetaTrader5 as mt5
from datetime import datetime, timedelta
from decision_engine import should_override_soft_limit
from config import FTMO_PARAMS

def get_today_midnight():
    now = datetime.now()
    return datetime(now.year, now.month, now.day)

def get_closed_pnl_today():
    midnight = get_today_midnight()
    deals = mt5.history_deals_get(midnight, datetime.now())
    if deals is None:
        return 0.0
    return sum(d.profit for d in deals)

def get_floating_pnl():
    positions = mt5.positions_get()
    if positions is None:
        return 0.0
    return sum(p.profit for p in positions)

def get_equity():
    acc_info = mt5.account_info()
    if acc_info is None or acc_info.equity == 0:
        print("⚠️ Invalid or unavailable equity info.")
        return FTMO_PARAMS["initial_balance"]  # fallback
    return acc_info.equity

def get_balance():
    acc_info = mt5.account_info()
    if acc_info is None or acc_info.balance == 0:
        print("⚠️ Invalid or unavailable balance info.")
        return FTMO_PARAMS["initial_balance"]  # fallback
    return acc_info.balance


def is_within_daily_loss():
    closed_today = get_closed_pnl_today()
    floating = get_floating_pnl()
    daily_loss = closed_today + floating
    limit = -FTMO_PARAMS["max_daily_loss_pct"] * FTMO_PARAMS["initial_balance"]
    return daily_loss >= limit

def is_within_total_loss():
    equity = get_equity()
    min_equity = FTMO_PARAMS["initial_balance"] * (1 - FTMO_PARAMS["max_total_loss_pct"])
    return equity >= min_equity

def is_profit_target_hit():
    balance = get_balance()
    target = FTMO_PARAMS["initial_balance"] * (1 + FTMO_PARAMS["profit_target_pct"])
    return balance >= target

def get_trading_days():
    orders = mt5.history_orders_get(datetime(2000, 1, 1), datetime.now())
    trade_days = set()
    for order in orders:
        if order.type in (mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL):
            trade_days.add(order.time_create.date())
    return len(trade_days)

def is_trading_day_requirement_met():
    return get_trading_days() >= FTMO_PARAMS["min_trading_days"]

def can_trade(ta_signals=None, ai_response_raw=None, call_ai_func=None):
    max_daily_loss = FTMO_PARAMS["max_daily_loss_pct"] * FTMO_PARAMS["initial_balance"]
    max_total_loss = FTMO_PARAMS["max_total_loss_pct"] * FTMO_PARAMS["initial_balance"]
    personal_limit = 0.5 * max_daily_loss  # $5,000 on 200k

    closed_today = get_closed_pnl_today()
    floating = get_floating_pnl()
    equity = get_equity()
    balance = get_balance()

    daily_loss = closed_today + floating
    total_loss = FTMO_PARAMS["initial_balance"] - equity

    print(f"🔒 [RISK CHECK] Closed PnL: {closed_today:.2f} | Floating: {floating:.2f} | Daily Loss: {daily_loss:.2f}")
    print(f"🔒 [RISK CHECK] Equity: {equity:.2f} | Total Loss: {total_loss:.2f} | Balance: {balance:.2f}")

    # ✅ HARD STOP – FTMO daily
    if daily_loss <= -max_daily_loss:
        print("🚫 Blocked: Daily loss limit breached.")
        return False

    # ✅ HARD STOP – FTMO total
    if total_loss >= max_total_loss:
        print("🚫 Blocked: Total loss limit breached.")
        return False

    # ✅ PROFIT TARGET HIT
    if balance >= FTMO_PARAMS["initial_balance"] * (1 + FTMO_PARAMS["profit_target_pct"]):
        print("✅ Profit target hit. No further trades needed.")
        return False

    # ✅ PERSONAL LIMIT HIT – TEMPORARY BYPASS
    if daily_loss <= -personal_limit:
        print("⛔ Personal soft limit breached.")
        print(f"📉 Today's P&L: ${daily_loss:,.2f}")
        print(f"💣 Remaining buffer today: ${max_daily_loss + daily_loss:,.2f}")
        print("⚠️ OVERRIDE CHECK TEMP DISABLED — TRADE WILL CONTINUE")
        return True

    return True

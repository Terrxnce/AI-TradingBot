import MetaTrader5 as mt5
from datetime import datetime, timedelta
import os
import json
from decision_engine import should_override_soft_limit
from config import CONFIG, FTMO_PARAMS

cooldown_file_path = "pnl_cooldown_state.json"
loss_block_file_path = "loss_block_state.json"

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

def soft_breach_recently_triggered():
    if not os.path.exists(cooldown_file_path):
        return False
    with open(cooldown_file_path, "r") as f:
        cooldown_state = json.load(f)
    return cooldown_state.get("cooldown_active", False)

def get_equity():
    acc_info = mt5.account_info()
    if acc_info is None or acc_info.equity == 0:
        print("⚠️ Invalid or unavailable equity info.")
        return FTMO_PARAMS["initial_balance"]
    return acc_info.equity

def get_balance():
    acc_info = mt5.account_info()
    if acc_info is None or acc_info.balance == 0:
        print("⚠️ Invalid or unavailable balance info.")
        return FTMO_PARAMS["initial_balance"]
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

def is_pnl_cooldown_active(tech_score):
    balance = get_balance()
    floating_pnl = get_floating_pnl()
    pnl_pct = (floating_pnl / balance) * 100 if balance else 0
    threshold = CONFIG.get("pnl_drawdown_limit", -0.5)
    min_score_to_bypass = CONFIG.get("pm_usd_asset_min_score", 6)
    cooldown_minutes = CONFIG.get("cooldown_minutes_after_recovery", 15)
    now = datetime.now()

    # Load cooldown state
    if os.path.exists(cooldown_file_path):
        with open(cooldown_file_path, "r") as f:
            cooldown_state = json.load(f)
    else:
        cooldown_state = {
            "cooldown_active": False,
            "recovered_at": None,
            "triggered_at": None
        }

    # Trigger cooldown if threshold breached
    if pnl_pct <= threshold and not cooldown_state["cooldown_active"]:
        cooldown_state["cooldown_active"] = True
        cooldown_state["triggered_at"] = now.isoformat()
        cooldown_state["recovered_at"] = None
        print(f"🧯 PnL below threshold ({pnl_pct:.2f}%). Cooldown triggered.")

    # Start recovery timer if PnL positive
    elif cooldown_state["cooldown_active"] and pnl_pct > 0:
        if not cooldown_state["recovered_at"]:
            cooldown_state["recovered_at"] = now.isoformat()
            print("📈 Floating PnL turned positive. Starting recovery timer...")

        recovered_time = datetime.fromisoformat(cooldown_state["recovered_at"])
        if now - recovered_time >= timedelta(minutes=cooldown_minutes):
            print(f"✅ Recovery complete ({cooldown_minutes} mins). Cooldown lifted.")
            cooldown_state = {
                "cooldown_active": False,
                "recovered_at": None,
                "triggered_at": None
            }

    # Save updated state
    with open(cooldown_file_path, "w") as f:
        json.dump(cooldown_state, f)

    # Block trade unless override score is met
    if cooldown_state["cooldown_active"]:
        if tech_score >= min_score_to_bypass:
            print(f"⚠️ Cooldown active, but high score ({tech_score}/8) allows override.")
            return False
        else:
            print(f"🚫 Trade blocked by cooldown. Current score: {tech_score}/8.")
            return True

    return False

def load_loss_block_state():
    """Load the current loss block state from JSON file."""
    try:
        if os.path.exists(loss_block_file_path):
            with open(loss_block_file_path, "r") as f:
                return json.load(f).get("block_active", False)
        return False
    except Exception as e:
        print(f"⚠️ Error loading loss block state: {e}")
        return False


def set_loss_block_state(active):
    """Set the loss block state and save to JSON file."""
    try:
        with open(loss_block_file_path, "w") as f:
            json.dump({"block_active": active}, f)
        print(f"📝 Loss block state set to: {active}")
    except Exception as e:
        print(f"❌ Error saving loss block state: {e}")


def check_pnl_drawdown_block():
    """
    Check if trading should be blocked due to -1% unrealized PnL drawdown.
    Returns True if trading should be blocked, False if allowed.
    """
    balance = get_balance()
    floating_pnl = get_floating_pnl()
    pnl_threshold = -balance * 0.01  # -1% threshold
    
    block_active = load_loss_block_state()
    
    # If we're currently in block mode
    if block_active:
        if floating_pnl > 0:
            print("✅ Recovery detected: Floating PnL > 0. Resuming trades.")
            set_loss_block_state(False)
            return False  # Allow trading
        else:
            print(f"🧊 Trade frozen — still recovering from drawdown. Current PnL: ${floating_pnl:.2f}")
            return True  # Block trading
    
    # If we're not in block mode, check if we should enter it
    if floating_pnl < pnl_threshold:
        print(f"🚫 Unrealized PnL below -1% threshold: ${floating_pnl:.2f} < ${pnl_threshold:.2f}")
        print("🚫 Entered drawdown block mode - no new trades until recovery.")
        set_loss_block_state(True)
        return True  # Block trading
    
    return False  # Allow trading

def can_trade(ta_signals=None, ai_response_raw=None, call_ai_func=None, tech_score=0):
    max_daily_loss = FTMO_PARAMS["max_daily_loss_pct"] * FTMO_PARAMS["initial_balance"]
    max_total_loss = FTMO_PARAMS["max_total_loss_pct"] * FTMO_PARAMS["initial_balance"]
    personal_limit = 0.5 * max_daily_loss

    closed_today = get_closed_pnl_today()
    floating = get_floating_pnl()
    equity = get_equity()
    balance = get_balance()

    daily_loss = closed_today + floating
    total_loss = FTMO_PARAMS["initial_balance"] - equity

    print(f"🔒 [RISK CHECK] Closed PnL: {closed_today:.2f} | Floating: {floating:.2f} | Daily Loss: {daily_loss:.2f}")
    print(f"🔒 [RISK CHECK] Equity: {equity:.2f} | Total Loss: {total_loss:.2f} | Balance: {balance:.2f}")

    # Check for -1% PnL drawdown block (Feature 3 & 4)
    if check_pnl_drawdown_block():
        return False

    if is_pnl_cooldown_active(tech_score):
        return False

    if soft_breach_recently_triggered():
        if tech_score < CONFIG.get("pm_usd_asset_min_score", 6):
            floating_pnl = get_floating_pnl()
            if floating_pnl <= 0:
                print("🚫 Waiting for floating PnL recovery before continuing...")
                return False


    if daily_loss <= -max_daily_loss:
        print("🚫 Blocked: Daily loss limit breached.")
        return False

    if total_loss >= max_total_loss:
        print("🚫 Blocked: Total loss limit breached.")
        return False

    if balance >= FTMO_PARAMS["initial_balance"] * (1 + FTMO_PARAMS["profit_target_pct"]):
        print("✅ Profit target hit. No further trades needed.")
        return False

    if daily_loss <= -personal_limit:
        print("⛔ Personal soft limit breached.")
        print(f"📉 Today's P&L: ${daily_loss:,.2f}")
        print(f"💣 Remaining buffer today: ${max_daily_loss + daily_loss:,.2f}")

        if call_ai_func and ta_signals and ai_response_raw and "ENTRY_DECISION" in ai_response_raw:
            print("🧠 Checking AI override...")
            should_override = should_override_soft_limit(
                ta_signals=ta_signals,
                ai_response_raw=ai_response_raw,
                daily_loss=daily_loss,
                call_ai_func=call_ai_func
            )
            if should_override:
                print("✅ AI override approved. Continuing trade.")
                return True
            else:
                print("🚫 AI override denied. Blocking trade.")
                return False
        else:
            print("⚠️ Missing AI input — skipping override. Blocking trade.")
            return False

    return True

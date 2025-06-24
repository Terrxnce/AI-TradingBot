import MetaTrader5 as mt5
from broker_interface import initialize_mt5, shutdown_mt5, place_trade, resolve_symbol

def run_isolated_trade_test():
    """
    Tests the place_trade function in isolation.
    """
    print("🚀 Starting isolated trade test...")

    # === Parameters for the test trade ===
    test_symbol_base = "EURUSD"  # Base symbol, resolve_symbol will try to find the broker-specific one
    test_action = "BUY"
    test_lot_size = 0.01 # Use a small lot size for testing

    try:
        initialize_mt5()
        print(f"✅ MT5 Initialized for test.")

        # Resolve the symbol (optional, but good practice to test this part too)
        # In place_trade, symbol.upper() is used, so we ensure it's upper here.
        # The internal resolve_symbol in broker_interface.py is not directly used by place_trade's main logic.
        # However, we can call it here to see if it finds anything.
        # For the actual trade, place_trade will use what's passed to it.

        # First, ensure the symbol is available and visible in MarketWatch
        # This is normally done in bot_runner.py, but essential for place_trade
        symbol_info = mt5.symbol_info(test_symbol_base.upper())
        if symbol_info is None:
            print(f"❌ Symbol {test_symbol_base.upper()} not found by MT5. Cannot proceed with test.")
            return

        if not symbol_info.visible:
            print(f"市场观察中未找到交易品种 {test_symbol_base.upper()}, 尝试添加") # "Symbol not found in MarketWatch, attempting to add"
            if not mt5.symbol_select(test_symbol_base.upper(), True):
                print(f"❌ Failed to add {test_symbol_base.upper()} to MarketWatch. Test cannot proceed.")
                return
            # Re-fetch info after selection
            symbol_info = mt5.symbol_info(test_symbol_base.upper())
            if not symbol_info or not symbol_info.visible:
                print(f"❌ Still cannot see {test_symbol_base.upper()} after attempting to select. Test aborted.")
                return
            print(f"✅ {test_symbol_base.upper()} is now visible in MarketWatch.")

        # Get current price to calculate example SL/TP for the test
        tick = mt5.symbol_info_tick(test_symbol_base.upper())
        if tick is None:
            print(f"❌ Failed to get tick data for {test_symbol_base.upper()} to calculate SL/TP for test. Aborting.")
            return

        entry_price = tick.ask if test_action == "BUY" else tick.bid

        # Example: 35 pips SL/TP for testing (assuming 1 pip = 10 points for a 5-digit broker)
        # This calculation is similar to the one in bot_runner.py for consistency in testing
        points_for_sl_tp = 350  # 35 pips * 10 points/pip
        price_offset = points_for_sl_tp * symbol_info.point # Use symbol_info obtained earlier

        test_sl_price = 0.0
        test_tp_price = 0.0

        if test_action == "BUY":
            test_sl_price = entry_price - price_offset
            test_tp_price = entry_price + price_offset
        # Add SELL logic if you want to test SELL actions
        # elif test_action == "SELL":
        #     test_sl_price = entry_price + price_offset
        #     test_tp_price = entry_price - price_offset

        print(f"\n--- Test Trade Details ---")
        print(f"Action: {test_action}, Symbol: {test_symbol_base.upper()}, Lot: {test_lot_size}")
        print(f"Calculated Entry (for SL/TP): {entry_price:.{symbol_info.digits}f}")
        print(f"Calculated SL Price for test: {test_sl_price:.{symbol_info.digits}f}")
        print(f"Calculated TP Price for test: {test_tp_price:.{symbol_info.digits}f}")
        print(f"-------------------------")

        print(f"\nAttempting to place a {test_action} order for {test_symbol_base.upper()} with lot size {test_lot_size}...")
        place_trade(symbol=test_symbol_base.upper(),
                      action=test_action,
                      lot=test_lot_size,
                      sl_price=test_sl_price,
                      tp_price=test_tp_price)

        print("\n✅ Isolated trade test finished.")
    except RuntimeError as e:
        print(f"❌ Runtime Error during test: {e}")
    except ValueError as e:
        print(f"❌ Value Error during test: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    finally:
        print("Shutting down MT5...")
        shutdown_mt5()
        print("🏁 Test script complete.")

if __name__ == "__main__":
    # Important: Ensure your MetaTrader 5 terminal is running and logged in.
    # Also, ensure "Algo Trading" is enabled in MT5.
    # (Tools -> Options -> Expert Advisors -> Allow algorithmic trading AND the "Algo Trading" button on the toolbar)
    run_isolated_trade_test()

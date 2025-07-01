print("--- Script test_broker_interface.py starting ---")

import sys
print(f"--- Python version: {sys.version} ---")
print(f"--- Python executable: {sys.executable} ---")

try:
    print("--- Attempting to import MetaTrader5 ---")
    import MetaTrader5 as mt5
    print("--- MetaTrader5 imported successfully ---")
    
    # We need broker_interface functions, so import them after MT5
    # Assuming broker_interface.py is in the same directory
    print("--- Attempting to import functions from broker_interface ---")
    from broker_interface import initialize_mt5, shutdown_mt5, place_trade
    print("--- Functions from broker_interface imported successfully ---")

except ImportError as e:
    print(f"--- IMPORT ERROR: {e} ---")
    print("--- Please ensure MetaTrader5 package is installed and accessible,")
    print("--- and that broker_interface.py is in the same directory. ---")
    sys.exit(f"Exiting due to import error: {e}")
except Exception as e:
    print(f"--- UNEXPECTED ERROR DURING IMPORT: {e} ---")
    sys.exit(f"Exiting due to unexpected import error: {e}")


def run_isolated_trade_test():
    print("--- Inside run_isolated_trade_test() function ---")
    print("🚀 Starting isolated trade test...")
    
    test_symbol_base = "EURUSD"
    test_action = "BUY"
    test_lot_size = 0.01

    try:
        print("--- Attempting initialize_mt5() ---")
        initialize_mt5()
        print(f"✅ MT5 Initialized for test.")

        symbol_to_check = test_symbol_base.upper()
        print(f"--- Checking symbol: {symbol_to_check} ---")
        symbol_info = mt5.symbol_info(symbol_to_check)
        
        if symbol_info is None:
            print(f"--- Symbol {symbol_to_check} not found by MT5. Attempting to select it. ---")
            if not mt5.symbol_select(symbol_to_check, True):
                print(f"❌ Failed to initially find or select {symbol_to_check}. Test may fail.")
            else:
                print(f"--- Symbol {symbol_to_check} selected. Re-checking... ---")
                symbol_info = mt5.symbol_info(symbol_to_check)
                if symbol_info is None:
                    print(f"❌ Symbol {symbol_to_check} still not found after select. Aborting test function. ---")
                    return

        if symbol_info and not symbol_info.visible:
            print(f"--- Symbol {symbol_to_check} not visible in MarketWatch, attempting to add... ---")
            if not mt5.symbol_select(symbol_to_check, True):
                print(f"❌ Failed to add {symbol_to_check} to MarketWatch.")
            else:
                symbol_info = mt5.symbol_info(symbol_to_check)
                if not symbol_info or not symbol_info.visible:
                    print(f"❌ Still cannot see {symbol_to_check} after attempting to select.")
                else:
                    print(f"✅ {symbol_to_check} is now visible in MarketWatch.")
        elif symbol_info:
            print(f"✅ {symbol_to_check} is already visible in MarketWatch.")
        else:
            print(f"❌ Critical: Symbol {symbol_to_check} could not be found or made visible. Aborting test function. ---")
            return

        print(f"--- Attempting to place a {test_action} order for {symbol_to_check} with lot size {test_lot_size}... ---")
        place_trade(symbol=symbol_to_check, action=test_action, lot=test_lot_size)
        
        print("✅ Isolated trade test finished.")

    except RuntimeError as e:
        print(f"❌ Runtime Error during test: {e}")
    except ValueError as e:
        print(f"❌ Value Error during test: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred in run_isolated_trade_test: {e}")
        import traceback
        print("--- Traceback ---")
        traceback.print_exc()
        print("--- End Traceback ---")
    finally:
        print("--- Shutting down MT5 from run_isolated_trade_test finally block... ---")
        shutdown_mt5()
        print("🏁 Test script function complete.")

if __name__ == "__main__":
    print("--- Script is being run directly (__name__ == '__main__') ---")
    # Ensure MT5 terminal is running, logged in, and Algo Trading is enabled.
    run_isolated_trade_test()
    print("--- End of script test_broker_interface.py ---")

import pandas as pd
import numpy as np
from datetime import datetime, time as dtime_py # Python's time object
import pytz # For timezone handling

class TechnicalAnalyzer:
    def __init__(self, df):
        self.df = df.copy() # df should have a datetime index or a 'time' column with datetime objects

        # --- Timezone and Session Definitions ---
        self.NY_TZ = pytz.timezone("America/New_York")
        # Asia: 7 PM (19:00) NY prev day to 4 AM (04:00) NY current day
        self.ASIA_START_HOUR = 19
        self.ASIA_END_HOUR = 4
        # London: 3 AM (03:00) to 12 PM (12:00) NY time
        self.LONDON_START_HOUR = 3
        self.LONDON_END_HOUR = 12
        # NY: 9 AM (09:00) to 5 PM (17:00) NY time
        self.NY_START_HOUR = 9
        self.NY_END_HOUR = 17

        # --- Attributes for Previous COMPLETED Session Highs/Lows ---
        self.asia_high_prev = np.nan
        self.asia_low_prev = np.nan
        self.london_high_prev = np.nan
        self.london_low_prev = np.nan
        # (NY prev H/L could be added if needed for multi-day strategies)

        # --- Attributes for CURRENT ONGOING Session Highs/Lows Accumulation ---
        self._current_asia_high = np.nan
        self._current_asia_low = np.nan
        self._current_london_high = np.nan
        self._current_london_low = np.nan
        self._current_ny_high = np.nan # For NY session itself
        self._current_ny_low = np.nan

        # --- State Variables for Session Processing ---
        # To track the NY date of the last processed candle, for daily session resets
        self._last_processed_day_ny = None
        # Flags to manage the state of session accumulation (currently in Asia, London, etc.)
        self._is_accumulating_asia = False
        self._is_accumulating_london = False
        self._is_accumulating_ny = False # Added for NY session accumulation

        if self.df.empty:
            print("Warning: TechnicalAnalyzer initialized with an empty DataFrame.")

        self.calculate_ema()
        self._process_df_for_session_analytics() # Process session data after EMA calculation

    def _is_in_session(self, candle_dt_ny: datetime, start_hour: int, end_hour: int) -> bool:
        """
        Checks if a New York localized datetime object falls within a session defined by start and end hours.
        Handles overnight sessions correctly.
        """
        if not candle_dt_ny or candle_dt_ny.tzinfo is None or candle_dt_ny.tzinfo.zone != self.NY_TZ.zone:
            # This should not happen if candle_dt_ny is always converted properly before calling
            raise ValueError("candle_dt_ny must be a datetime object localized to New York timezone.")

        current_time_ny = candle_dt_ny.time()
        start_time_obj = dtime_py(start_hour, 0)
        end_time_obj = dtime_py(end_hour, 0)

        if start_hour <= end_hour: # Session does not cross midnight (e.g., London 03:00-12:00, NY 09:00-17:00)
            return start_time_obj <= current_time_ny < end_time_obj # Use < end_time for exclusive end
        else: # Session crosses midnight (e.g., Asia 19:00 to 04:00 next day)
            # True if current time is after start OR before end of next day
            return current_time_ny >= start_time_obj or current_time_ny < end_time_obj

    def update_session_analytics_for_candle(self, candle_utc_dt: datetime, candle_high: float, candle_low: float):
        """
        Updates session highs/lows based on the current candle.
        This method should be called for each candle in chronological order.
        Assumes candle_utc_dt is a timezone-aware datetime object (preferably UTC).
        """
        if candle_utc_dt.tzinfo is None:
            # Fallback: If timestamp is naive, assume it's UTC as per _ensure_datetime_index
            # print("Warning: update_session_analytics_for_candle received naive datetime. Assuming UTC.")
            candle_utc_dt = pytz.utc.localize(candle_utc_dt)

        candle_dt_ny = candle_utc_dt.astimezone(self.NY_TZ)
        current_day_ny = candle_dt_ny.date()

        # --- Daily Reset Logic ---
        # If it's a new day in New York, completed sessions from "yesterday NY" become "previous"
        if self._last_processed_candle_time_ny is not None and current_day_ny > self._last_processed_candle_time_ny.date():
            # Asia session might have concluded on the new NY day if it ran past midnight.
            # London session from _last_processed_candle_time_ny.date() is now definitively "previous".
            if self._is_accumulating_london: # If London was active and day changed, finalize it.
                self.london_high_prev = self._current_london_high
                self.london_low_prev = self._current_london_low
            # Asia session: If it was accumulating and crossed midnight, it's more complex.
            # For simplicity, we assume Asia session values are finalized when Asia explicitly ends.
            # Reset current accumulations for the new day
            self._current_asia_high, self._current_asia_low = np.nan, np.nan
            self._current_london_high, self._current_london_low = np.nan, np.nan
            self._current_ny_high, self._current_ny_low = np.nan, np.nan
            self._is_accumulating_asia = False
            self._is_accumulating_london = False
            self._is_accumulating_ny = False

        self._current_processing_day_ny = current_day_ny # Update current processing day

        # --- Determine Current Sessions for the given candle ---
        candle_is_in_asia = self._is_in_session(candle_dt_ny, self.ASIA_START_HOUR, self.ASIA_END_HOUR)
        candle_is_in_london = self._is_in_session(candle_dt_ny, self.LONDON_START_HOUR, self.LONDON_END_HOUR)
        candle_is_in_ny = self._is_in_session(candle_dt_ny, self.NY_START_HOUR, self.NY_END_HOUR)

        # --- Asia Session Processing ---
        if candle_is_in_asia:
            if not self._is_accumulating_asia: # Asia session accumulation period starts
                self._is_accumulating_asia = True
                self._current_asia_high = candle_high # Initialize with current candle's H/L
                self._current_asia_low = candle_low
            else: # Ongoing Asia session accumulation
                self._current_asia_high = max(self._current_asia_high, candle_high) if not np.isnan(self._current_asia_high) else candle_high
                self._current_asia_low = min(self._current_asia_low, candle_low) if not np.isnan(self._current_asia_low) else candle_low
        elif self._is_accumulating_asia and not candle_is_in_asia: # Asia session accumulation period ends
            self.asia_high_prev = self._current_asia_high # Store completed session H/L
            self.asia_low_prev = self._current_asia_low
            self._is_accumulating_asia = False
            # Values in _current_asia_high/low now represent the completed session until they are reset or a new Asia session starts.

        # --- London Session Processing ---
        if candle_is_in_london:
            if not self._is_accumulating_london: # London session accumulation period starts
                self._is_accumulating_london = True
                self._current_london_high = candle_high # Initialize
                self._current_london_low = candle_low
                # If Asia was somehow still accumulating when London starts (e.g. data gap or slight overlap in real-world feed vs strict def)
                # finalize Asia to ensure its 'prev' values are set.
                if self._is_accumulating_asia:
                    self.asia_high_prev = self._current_asia_high
                    self.asia_low_prev = self._current_asia_low
                    self._is_accumulating_asia = False
            else: # Ongoing London session accumulation
                self._current_london_high = max(self._current_london_high, candle_high) if not np.isnan(self._current_london_high) else candle_high
                self._current_london_low = min(self._current_london_low, candle_low) if not np.isnan(self._current_london_low) else candle_low
        elif self._is_accumulating_london and not candle_is_in_london: # London session accumulation period ends
            self.london_high_prev = self._current_london_high # Store completed session H/L
            self.london_low_prev = self._current_london_low
            self._is_accumulating_london = False

        # --- NY Session Processing ---
        if candle_is_in_ny:
            if not self._is_accumulating_ny: # NY session accumulation period starts
                self._is_accumulating_ny = True
                self._current_ny_high = candle_high # Initialize
                self._current_ny_low = candle_low
                # If London was somehow still accumulating, finalize it.
                if self._is_accumulating_london:
                    self.london_high_prev = self._current_london_high
                    self.london_low_prev = self._current_london_low
                    self._is_accumulating_london = False
            else: # Ongoing NY session accumulation
                self._current_ny_high = max(self._current_ny_high, candle_high) if not np.isnan(self._current_ny_high) else candle_high
                self._current_ny_low = min(self._current_ny_low, candle_low) if not np.isnan(self._current_ny_low) else candle_low
        elif self._is_accumulating_ny and not candle_is_in_ny: # NY session accumulation period ends
            # The H/L of the just-ended NY session are stored in _current_ny_high/low.
            # These are not typically used as "previous" for sweeps in the same way Asia/London are for the *next* NY open.
            # However, they might be useful for other EOD logic or if the strategy changes.
            self._is_accumulating_ny = False
            # We can choose to reset _current_ny_high/low to np.nan here or let them persist.
            # For now, they hold the values of the completed NY session.

        self._last_processed_candle_time_ny = candle_dt_ny

        # Return the session status for the *specific candle being processed*
        return candle_is_in_asia, candle_is_in_london, candle_is_in_ny

    def _process_df_for_session_analytics(self):
        """
        Processes the entire DataFrame to calculate session analytics for each candle
        and update overall previous session H/L attributes.
        Adds 'is_in_asia', 'is_in_london', 'is_in_ny' columns to self.df.
        This method should be called after df is set and EMAs are calculated,
        typically during or after __init__.
        """
        if self.df.empty:
            self.df['is_in_asia'] = pd.Series(dtype=bool)
            self.df['is_in_london'] = pd.Series(dtype=bool)
            self.df['is_in_ny'] = pd.Series(dtype=bool)
            return

        self._ensure_datetime_index() # Ensures self.df.index is UTC DatetimeIndex

        # Store results in lists then assign to df columns for efficiency
        session_statuses = []

        # Reset overall state before iterating through the whole DataFrame
        self.asia_high_prev = np.nan
        self.asia_low_prev = np.nan
        self.london_high_prev = np.nan
        self.london_low_prev = np.nan
        self._current_asia_high = np.nan
        self._current_asia_low = np.nan
        self._current_london_high = np.nan
        self._current_london_low = np.nan
        self._current_ny_high = np.nan
        self._current_ny_low = np.nan
        self._last_processed_candle_time_ny = None
        self._current_processing_day_ny = None
        self._is_accumulating_asia = False
        self._is_accumulating_london = False
        self._is_accumulating_ny = False

        for candle_utc_dt, row in self.df.iterrows():
            candle_high = row['high']
            candle_low = row['low']

            # update_session_analytics_for_candle updates self.asia_high_prev etc.
            # and returns status for the current candle
            status = self.update_session_analytics_for_candle(candle_utc_dt, candle_high, candle_low)
            session_statuses.append(status)

        # Assign new columns to the DataFrame
        session_df = pd.DataFrame(session_statuses, index=self.df.index, columns=['is_in_asia', 'is_in_london', 'is_in_ny'])
        self.df = self.df.join(session_df)

    def _ensure_datetime_index(self):
        """Ensures the DataFrame index is datetime and localized to UTC if naive."""
        if not isinstance(self.df.index, pd.DatetimeIndex):
            if 'time' in self.df.columns:
                self.df['time'] = pd.to_datetime(self.df['time'])
                self.df = self.df.set_index('time')
            else:
                raise ValueError("DataFrame must have a DatetimeIndex or a 'time' column that can be converted to DatetimeIndex.")

        if self.df.index.tzinfo is None:
            print("Warning: DataFrame DatetimeIndex is naive. Assuming UTC.")
            self.df = self.df.tz_localize('UTC')
        elif self.df.index.tzinfo != pytz.UTC:
            self.df = self.df.tz_convert('UTC')


    def calculate_ema(self, periods=[21, 50, 200]):
        if self.df.empty:
            for period in periods: # Still create columns to avoid KeyErrors later
                self.df[f'EMA_{period}'] = pd.Series(dtype=float)
            return
        for period in periods:
            self.df[f'EMA_{period}'] = self.df['close'].ewm(span=period, adjust=False).mean()

    def get_trend_direction(self):
        """Determines trend direction based on EMAs for the latest data point."""
        if self.df.empty or len(self.df) < 200: # Relies on EMAs being calculated
            return False, False # Not enough data or EMAs not ready

        # Ensure EMA columns exist
        if not all(col in self.df.columns for col in ['EMA_21', 'EMA_50', 'EMA_200']):
            # This might happen if df was empty during calculate_ema or periods changed
            # print("Warning: EMA columns not found. Recalculating EMAs.")
            self.calculate_ema() # Attempt to recalculate if missing
            if not all(col in self.df.columns for col in ['EMA_21', 'EMA_50', 'EMA_200']):
                 print("Error: EMA columns still missing after recalculation.")
                 return False, False


        latest_ema21 = self.df['EMA_21'].iloc[-1]
        latest_ema50 = self.df['EMA_50'].iloc[-1]
        latest_ema200 = self.df['EMA_200'].iloc[-1]

        is_bullish = latest_ema21 > latest_ema50 and latest_ema50 > latest_ema200
        is_bearish = latest_ema21 < latest_ema50 and latest_ema50 < latest_ema200
        return is_bullish, is_bearish

    def detect_fvg_pine(self):
        """
        Detects FVG based on Pine Script: low > high[1] and high[1] > low[2]
        This checks the condition for the most recent set of 3 candles.
        Returns: Boolean indicating if the FVG pattern is present.
        """
        if len(self.df) < 3:
            return False

        # For latest candle (index -1):
        # low = self.df['low'].iloc[-1]
        # high_1 = self.df['high'].iloc[-2] # Pine high[1]
        # low_2 = self.df['low'].iloc[-3]  # Pine low[2]

        # Pine: low > high[1] and high[1] > low[2]
        # This seems to be for a bullish FVG based on its structure (upward movement)
        # If this is true, an FVG is formed by candle self.df.iloc[-3] and self.df.iloc[-1]
        # The "gap" is between high of self.df.iloc[-3] and low of self.df.iloc[-1]
        # The Pine script's `low > high[1] and high[1] > low[2]` is unusual for FVG.
        # It describes: current low > prev high AND prev high > low of 2 bars ago.
        # This indicates strong upward separation.

        # Let's directly translate the user's Pine:
        # low (current) > high[1] (previous) AND high[1] (previous) > low[2] (two bars ago)
        current_low = self.df['low'].iloc[-1]
        prev_high = self.df['high'].iloc[-2]
        two_bars_ago_low = self.df['low'].iloc[-3]

        fvg_condition = current_low > prev_high and prev_high > two_bars_ago_low
        return fvg_condition

    def get_fvg_levels_pine(self):
        """
        Gets FVG levels based on Pine Script: fvgLow = high[1], fvgHigh = low
        This is called if detect_fvg_pine is true.
        Returns: tuple (fvg_midpoint, fvg_top_boundary) or (None, None)
        """
        if len(self.df) < 2: # Needs current and previous for these definitions
            return None, None

        # Pine: fvgLow = high[1] (previous high), fvgHigh = low (current low)
        fvg_level_bottom_pine = self.df['high'].iloc[-2] # Pine's fvgLow
        fvg_level_top_pine = self.df['low'].iloc[-1]    # Pine's fvgHigh

        # For this to be a "gap" in the conventional sense that fvgHigh > fvgLow:
        if fvg_level_top_pine > fvg_level_bottom_pine:
            fvg_midpoint = (fvg_level_bottom_pine + fvg_level_top_pine) / 2
            return fvg_midpoint, fvg_level_top_pine # Pine's fvgHigh is the top boundary here
        return None, None


    def detect_order_block_pine(self):
        """
        Detects a Bullish Order Block based on Pine Script:
        bearishCandle = close[1] < open[1]
        bullishEngulf = close > open and close > close[1] and open < open[1]
        Returns: Boolean
        """
        if len(self.df) < 2:
            return False

        # Previous candle (index -2)
        prev_close = self.df['close'].iloc[-2]
        prev_open = self.df['open'].iloc[-2]

        # Current candle (index -1)
        curr_close = self.df['close'].iloc[-1]
        curr_open = self.df['open'].iloc[-1]

        bearish_candle_prev = prev_close < prev_open

        # bullishEngulf = close > open and close > close[1] and open < open[1]
        # Note: Pine's open < open[1] for a bullish engulf of a bearish candle is unusual.
        # Standard bullish engulfing of a bearish candle:
        # curr_open < prev_close AND curr_close > prev_open
        # Let's translate the Pine script literally for now:
        bullish_engulf_pine = (curr_close > curr_open and \
                               curr_close > prev_close and \
                               curr_open < prev_open) # This is Pine's open < open[1]

        return bearish_candle_prev and bullish_engulf_pine

    def detect_bos_pine(self):
        """
        Detects Break of Structure (Bullish) based on Pine Script:
        swingHigh = high[1] > high[2] and high[1] > high[3]
        brokeHigh = high > high[1]
        Returns: Boolean
        """
        if len(self.df) < 4: # Needs current, high[1], high[2], high[3]
            return False

        # current_high = self.df['high'].iloc[-1]    # Pine: high
        # prev_high = self.df['high'].iloc[-2]       # Pine: high[1] (this is the swing high candidate)
        # two_prev_high = self.df['high'].iloc[-3]   # Pine: high[2]
        # three_prev_high = self.df['high'].iloc[-4] # Pine: high[3]

        # swingHigh = high[1] > high[2] and high[1] > high[3]
        swing_high_defined_at_prev = self.df['high'].iloc[-2] > self.df['high'].iloc[-3] and \
                                     self.df['high'].iloc[-2] > self.df['high'].iloc[-4]

        # brokeHigh = high > high[1]
        current_high_breaks_swing = self.df['high'].iloc[-1] > self.df['high'].iloc[-2]

        return swing_high_defined_at_prev and current_high_breaks_swing

    def detect_engulfing_pine(self):
        """
        Detects a Bullish Engulfing candle based on Pine Script:
        bullishEngulf = close[1] < open[1] and close > open and close > open[1] and open < close[1]
        Returns: Boolean
        """
        if len(self.df) < 2:
            return False

        prev_close = self.df['close'].iloc[-2]
        prev_open = self.df['open'].iloc[-2]
        curr_close = self.df['close'].iloc[-1]
        curr_open = self.df['open'].iloc[-1]

        prev_is_bearish = prev_close < prev_open
        curr_is_bullish = curr_close > curr_open
        # close > open[1] (current close > previous open)
        curr_close_gt_prev_open = curr_close > prev_open
        # open < close[1] (current open < previous close)
        curr_open_lt_prev_close = curr_open < prev_close

        # Pine: close[1] < open[1] AND close > open AND close > open[1] AND open < close[1]
        # Which translates to:
        # prev_is_bearish AND curr_is_bullish AND curr_close_gt_prev_open AND curr_open_lt_prev_close
        # This is a standard bullish engulfing of a bearish candle.
        return prev_is_bearish and curr_is_bullish and curr_close_gt_prev_open and curr_open_lt_prev_close


    def run_all_pine_logics(self):
        """
        Runs all Pine Script translated detection logic for the latest candle.
        This is a placeholder for how these might be called.
        The actual combination of these signals will be in a more comprehensive method.
        """
        if self.df.empty or len(self.df) < 4: # Min length for BOS
            # Ensure essential keys exist even if empty, with default/NaN values
            return {
                "is_bullish_trend": False, "is_bearish_trend": False,
                "fvg_detected_pine": False, "fvg_mid_pine": np.nan, "fvg_top_pine": np.nan,
                "ob_detected_pine": False,
                "bos_detected_pine": False,
                "engulfing_detected_pine": False,
                "liquidity_sweep_detected_pine": False, # Added
                "is_in_asia_now": False, # Added
                "is_in_london_now": False, # Added
                "is_in_ny_now": False, # Added
                "asia_high_prev": self.asia_high_prev, # Pass through session H/L state
                "asia_low_prev": self.asia_low_prev,
                "london_high_prev": self.london_high_prev,
                "london_low_prev": self.london_low_prev,
                "df_with_analytics": self.df # Return df for inspection
            }

        is_bullish, is_bearish = self.get_trend_direction()
        fvg_detected = self.detect_fvg_pine()
        fvg_mid, fvg_top = np.nan, np.nan # Use np.nan for undefined numeric
        if fvg_detected:
            fvg_mid, fvg_top = self.get_fvg_levels_pine()

        # Liquidity Sweep Detection (will be implemented fully in next step)
        # For now, this is a placeholder. It needs the config and current candle values.
        # This will be properly integrated when we do Step 5.
        # We assume config is available via self.config if set in __init__ or passed.
        # For now, this won't work correctly without self.config and proper call.
        # We'll just return a placeholder for the key.
        liquidity_sweep_detected = False # Placeholder for now
        # Example of how it might be called later (needs self.pine_config):
        # if 'is_in_ny' in self.df.columns and self.df['is_in_ny'].iloc[-1]:
        #     liquidity_sweep_detected = self.detect_liquidity_sweep_pine(
        #         current_close=self.df['close'].iloc[-1],
        #         current_high=self.df['high'].iloc[-1],
        #         current_low=self.df['low'].iloc[-1],
        #         # These are now attributes of the class after _process_df_for_session_analytics
        #         asia_high_prev=self.asia_high_prev,
        #         asia_low_prev=self.asia_low_prev,
        #         london_high_prev=self.london_high_prev,
        #         london_low_prev=self.london_low_prev,
        #         config=getattr(self, 'pine_config', default_config) # Assuming config is stored
        #     )


        return {
            "is_bullish_trend": is_bullish,
            "is_bearish_trend": is_bearish,
            "fvg_detected_pine": fvg_detected,
            "fvg_mid_pine": fvg_mid if fvg_mid is not None else np.nan,
            "fvg_top_pine": fvg_top if fvg_top is not None else np.nan,
            "ob_detected_pine": self.detect_order_block_pine(),
            "bos_detected_pine": self.detect_bos_pine(),
            "engulfing_detected_pine": self.detect_engulfing_pine(),
            "liquidity_sweep_detected_pine": liquidity_sweep_detected, # Added
            "is_in_asia_now": self.df['is_in_asia'].iloc[-1] if 'is_in_asia' in self.df.columns and not self.df.empty else False,
            "is_in_london_now": self.df['is_in_london'].iloc[-1] if 'is_in_london' in self.df.columns and not self.df.empty else False,
            "is_in_ny_now": self.df['is_in_ny'].iloc[-1] if 'is_in_ny' in self.df.columns and not self.df.empty else False,
            "asia_high_prev": self.asia_high_prev,
            "asia_low_prev": self.asia_low_prev,
            "london_high_prev": self.london_high_prev,
            "london_low_prev": self.london_low_prev,
            "df_with_analytics": self.df
        }

    # --- Deprecated/Old methods that will be replaced or removed ---
    # def detect_fvg(self): ...
    # def detect_order_blocks(self): ...
    # def detect_bos(self): ...
    # def run_all(self): ...

    def get_pine_script_signal(self): # No arguments needed if it uses self.pine_config and self.df
        """
        Implements the combined entry logic (longCond) from the Pine Script.
        Returns a dictionary with 'signal': "BUY" or "HOLD", and other context if needed.
        """
        if self.df.empty or len(self.df) < 4: # Min length for some indicators
            return {"signal": "HOLD", "reason": "Not enough data"}

        # Ensure pine_config is available
        if not hasattr(self, 'pine_config') or not self.pine_config:
            # print("Warning: Pine Script config not set in TechnicalAnalyzer. Using default behaviors (likely all true).")
            # Fallback to a default if not set, or raise error. For now, assume it might be missing.
            # This implies that toggles might not work as expected if config isn't set.
            # A better approach is to require config in __init__ or ensure set_pine_config is called.
            # For this iteration, let's assume default_config from Pine Script if self.pine_config is empty/missing.
            # This is not ideal for production but helps proceed with logic.
            # Better: self.pine_config should be guaranteed to be set.
            # For now, let's use a local reference or default if not found on self.
            # This part should be improved: config should be passed to __init__ or set reliably.
        # For now, ensure it's at least an empty dict if not set, to allow .get() to work with defaults.
        cfg = getattr(self, 'pine_config', {})
        if not cfg: # If it was not set or set to None/empty explicitly by set_pine_config
            print("Warning: self.pine_config is not set or is empty. Using default logic for toggles (typically True if not found by .get()).")
            # This means cfg.get('someToggle', True) will default to True for all toggles.
            # Consider raising an error if a valid config is strictly required:
            # raise ValueError("Pine Script configuration (self.pine_config) must be set before calling get_pine_script_signal.")


        # Get all individual signals for the latest candle
        # run_all_pine_logics already computes these based on the latest state of self.df
        signals = self.run_all_pine_logics()

        # --- Apply Pine Script longCond logic ---
        # cfg = self.pine_config # shortcut from before, now cfg is already defined above

        # (not useSessionFilter or inActiveSession)
        in_active_session_now = bool(signals.get('is_in_asia_now', False) or \
                                signals.get('is_in_london_now', False) or \
                                signals.get('is_in_ny_now', False))
        session_filter_check = bool(not cfg.get('useSessionFilter', True) or in_active_session_now)

        # (not useEMAFilter or isBullish)
        ema_filter_check = bool(not cfg.get('useEMAFilter', True) or signals.get('is_bullish_trend', False))

        # (not useOrderBlocks or detectOrderBlock())
        ob_check = bool(not cfg.get('useOrderBlocks', True) or signals.get('ob_detected_pine', False))

        # (not useFVGs or (fvgCond and (not respectFVGMidpoint or close > fvgMid)))
        fvg_detected_pine_signal = signals.get('fvg_detected_pine', False)
        fvg_mid_pine_signal = signals.get('fvg_mid_pine', np.nan)

        fvg_respect_ok = True
        if fvg_detected_pine_signal and cfg.get('respectFVGMidpoint', True):
            if fvg_mid_pine_signal is not None and not np.isnan(fvg_mid_pine_signal):
                fvg_respect_ok = bool(self.df['close'].iloc[-1] > fvg_mid_pine_signal)
            else: # FVG detected, respect midpoint is true, but midpoint is invalid
                fvg_respect_ok = False

        fvg_condition_met = bool(fvg_detected_pine_signal and fvg_respect_ok)
        fvg_check = bool(not cfg.get('useFVGs', True) or fvg_condition_met)

        # (not useBOS or detectBOS())
        bos_check = bool(not cfg.get('useBOS', True) or signals.get('bos_detected_pine', False))

        # (not useEngulfing or detectEngulfing())
        engulfing_check = bool(not cfg.get('useEngulfing', True) or signals.get('engulfing_detected_pine', False))

        # (not useLiquiditySweep or (inNY and detectLiquiditySweepNY()))
        # signals['liquidity_sweep_detected_pine'] already incorporates the logic of:
        #   - master useLiquiditySweep toggle
        #   - is_in_ny_now
        #   - checkAsiaSweep/checkLondonSweep toggles
        # So, the condition simplifies.
        sweep_check = bool(not cfg.get('useLiquiditySweep', True) or signals.get('liquidity_sweep_detected_pine', False))

        # Debug prints for each check
        # print(f"DEBUG: session_filter_check = {session_filter_check} (type: {type(session_filter_check)})")
        # print(f"DEBUG: ema_filter_check = {ema_filter_check} (type: {type(ema_filter_check)})")
        # print(f"DEBUG: ob_check = {ob_check} (type: {type(ob_check)})")
        # print(f"DEBUG: fvg_check = {fvg_check} (type: {type(fvg_check)})")
        # print(f"DEBUG: bos_check = {bos_check} (type: {type(bos_check)})")
        # print(f"DEBUG: engulfing_check = {engulfing_check} (type: {type(engulfing_check)})")
        # print(f"DEBUG: sweep_check = {sweep_check} (type: {type(sweep_check)})")

        long_cond_final = session_filter_check and \
                          ema_filter_check and \
                          ob_check and \
                          fvg_check and \
                          bos_check and \
                          engulfing_check and \
                          sweep_check

        # Ensure long_cond_final is a Python bool
        long_cond_final = bool(long_cond_final)

        if long_cond_final:
            # For now, we don't calculate SL/TP here. That's done in bot_runner.py.
            # We just signal a BUY.
            # We can include fvg_top_pine for the TP2 suggestion from Pine.
            return {
                "signal": "BUY",
                "reason": "Pine Script longCond met",
                "fvg_top_for_tp2": signals.get('fvg_top_pine') if cfg.get('showTP2', True) else np.nan,
                "latest_signals_debug": signals # For debugging
            }

        return {"signal": "HOLD", "reason": "longCond not met", "latest_signals_debug": signals}


# The analyze_structure function needs to be completely rethought
# once TechnicalAnalyzer fully implements the Pine Script logic.
# For now, it's using the old structure.
def analyze_structure(candles_df):
    # This function will eventually use the new methods in TechnicalAnalyzer
    # that are aligned with Pine Script.

    # --- THIS IS THE OLD LOGIC ---
    ta = TechnicalAnalyzer(candles_df) # This now calculates EMAs on init
    # old_result = ta.run_all() # This 'run_all' is the old one.

    # --- CONCEPT FOR NEW LOGIC (using placeholder run_all_pine_logics) ---
    # This is not yet fully integrated into the bot's decision making flow.
    # It's just showing how to get the new signals.
    pine_signals = ta.run_all_pine_logics()

    # Example of how you might use the new signals:
    # This is highly simplified and does not represent the full Pine Script 'longCond'

    # The old `analyze_structure` returned a specific dict. We need to adapt.
    # For now, let's return something simple or indicate it needs full rework.

    # For now, let's return the raw pine_signals for inspection,
    # and a placeholder for the old structure to avoid breaking bot_runner immediately.
    # bot_runner will need to be updated to use the new signal structure.
    if not pine_signals: # Should not happen if run_all_pine_logics returns a dict
        return { "bos": False, "fvg_valid": False, "ob_tap": False, "ema_trend": "neutral", "pine_signals_raw": {} }

    # Placeholder for old structure:
    ema_trend = "bullish" if pine_signals.get("is_bullish_trend") else \
                  "bearish" if pine_signals.get("is_bearish_trend") else "neutral"

    return {
        # Old keys - these will become invalid as per Pine logic, map them as best as possible
        "bos": pine_signals.get("bos_detected_pine", False),
        "fvg_valid": pine_signals.get("fvg_detected_pine", False),
        "ob_tap": pine_signals.get("ob_detected_pine", False),
        "ema_trend": ema_trend,
        # New keys with more detailed Pine signals:
        "pine_signals_raw": pine_signals # Contains all new detailed signals
    }

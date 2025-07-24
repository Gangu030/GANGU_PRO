import pandas as pd
import pandas_ta as ta
import logging

logger = logging.getLogger(__name__)

class GYStrategy:
    def __init__(self, trap_threshold=0.001, vwap_rejection_strength=0.0005):
        """
        Initializes the GY Strategy with parameters.
        :param trap_threshold: Percentage deviation to consider a "trap" (e.g., 0.1% for 0.001)
        :param vwap_rejection_strength: Percentage deviation from VWAP for rejection (e.g., 0.05% for 0.0005)
        """
        self.trap_threshold = trap_threshold
        self.vwap_rejection_strength = vwap_rejection_strength
        self.symbol_data = {} # To store required data per symbol (e.g., VWAP, previous close/high/low)

    async def update_data(self, symbol, candles_df):
        """
        Updates internal data required for GY strategy calculations.
        This function needs to be called with updated candle data periodically.
        :param symbol: Trading symbol
        :param candles_df: Pandas DataFrame with columns 'open', 'high', 'low', 'close', 'volume'
        """
        if 'volume' not in candles_df.columns:
            logger.warning(f"Volume data not available for {symbol}. VWAP cannot be calculated for GY Strategy.")
            return

        # Calculate VWAP
        candles_df.ta.vwap(append=True)

        if 'VWAP' in candles_df.columns and not candles_df.empty:
            latest_candle = candles_df.iloc[-1]
            self.symbol_data[symbol] = {
                'vwap': latest_candle['VWAP'],
                'open': latest_candle['open'],
                'high': latest_candle['high'],
                'low': latest_candle['low'],
                'close': latest_candle['close'],
                'prev_close': candles_df.iloc[-2]['close'] if len(candles_df) > 1 else latest_candle['close'] # Needs at least 2 candles
            }
            logger.debug(f"Updated GY Strategy data for {symbol}: {self.symbol_data[symbol]}")
        else:
            logger.error(f"Failed to update GY Strategy data for {symbol}. Check candles_df and VWAP calculation.")

    async def check_signal(self, symbol, current_ltp):
        """
        Checks for GY Strategy (Trap Breakout + VWAP Rejection) signals.
        :param symbol: Trading symbol
        :param current_ltp: Current Last Traded Price
        :return: 'BUY', 'SELL', or None
        """
        if symbol not in self.symbol_data:
            logger.warning(f"GY Strategy data not available for {symbol}. Cannot check signal.")
            return None

        data = self.symbol_data[symbol]
        vwap = data['vwap']
        open_price = data['open']
        high = data['high']
        low = data['low']
        close_price = data['close']
        prev_close = data['prev_close']

        # Logic for Trap Breakout:
        # A trap can occur when price moves significantly past a key level (e.g., previous close, day's high/low)
        # but then reverses sharply.
        # This is a basic interpretation, real GY logic is more nuanced.
        
        # Example: Bull Trap (price goes above prev_close/day_high, then reverses below it)
        # Example: Bear Trap (price goes below prev_close/day_low, then reverses above it)

        # Simplified Trap Logic (needs refinement based on actual GY logic details)
        buy_trap = False
        sell_trap = False

        # If current LTP is significantly below the day's high but above the day's open
        # and it had briefly gone above previous close (indicating failed breakout)
        if current_ltp < (high - high * self.trap_threshold) and current_ltp > open_price:
            if high > (prev_close + prev_close * self.trap_threshold): # If it broke prev_close significantly
                 # This is a very rough interpretation of a "trap"
                pass # You'd need more complex candle pattern recognition here
        
        # VWAP Rejection Logic:
        # Price approaches VWAP and then bounces off it.
        # Buy signal if price drops near VWAP and bounces up (LTP > VWAP but was lower)
        # Sell signal if price rises near VWAP and bounces down (LTP < VWAP but was higher)

        vwap_upper_band = vwap * (1 + self.vwap_rejection_strength)
        vwap_lower_band = vwap * (1 - self.vwap_rejection_strength)

        # Assuming 'close_price' is the previous candle's close
        # If current_ltp has crossed above vwap from below (rejection from below)
        if current_ltp > vwap and close_price < vwap_lower_band:
            logger.info(f"GY BUY signal for {symbol}: LTP {current_ltp} crossed above VWAP {vwap} from below.")
            return "BUY"
        # If current_ltp has crossed below vwap from above (rejection from above)
        elif current_ltp < vwap and close_price > vwap_upper_band:
            logger.info(f"GY SELL signal for {symbol}: LTP {current_ltp} crossed below VWAP {vwap} from above.")
            return "SELL"

        return None

# Example Usage (This would be integrated into main.py or a data processing module)
if __name__ == "__main__":
    # Dummy data for demonstration (replace with actual historical data)
    data_points = [
        {'open': 100, 'high': 102, 'low': 99, 'close': 101, 'volume': 1000},
        {'open': 101, 'high': 103, 'low': 100, 'close': 102, 'volume': 1200},
        {'open': 102, 'high': 104, 'low': 101, 'close': 100.5, 'volume': 1500}, # Price crosses below VWAP
        {'open': 100.5, 'high': 102, 'low': 99.5, 'close': 101.5, 'volume': 1300}, # Bounces back
        {'open': 101.5, 'high': 103, 'low': 100, 'close': 102.5, 'volume': 1400}
    ]
    candles_df = pd.DataFrame(data_points)

    gy_strategy = GYStrategy()
    
    # Simulate real-time updates:
    async def simulate_gy_signals():
        await gy_strategy.update_data("NSE:EXAMPLE-EQ", candles_df.iloc[:3])
        print(f"LTP 101.8, Signal: {await gy_strategy.check_signal('NSE:EXAMPLE-EQ', 101.8)}") # Should be around VWAP
        
        await gy_strategy.update_data("NSE:EXAMPLE-EQ", candles_df.iloc[:4]) # New candle for update
        print(f"LTP 100.2, Signal: {await gy_strategy.check_signal('NSE:EXAMPLE-EQ', 100.2)}") # Below VWAP
        
        await gy_strategy.update_data("NSE:EXAMPLE-EQ", candles_df.iloc[:5]) # New candle for update
        print(f"LTP 102.8, Signal: {await gy_strategy.check_signal('NSE:EXAMPLE-EQ', 102.8)}") # Above VWAP, potential BUY

    asyncio.run(simulate_gy_signals())
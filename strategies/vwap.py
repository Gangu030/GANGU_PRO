import pandas as pd
import pandas_ta as ta
import logging

logger = logging.getLogger(__name__)

class VWAPStrategy:
    def __init__(self):
        self.symbol_vwap_data = {} # To store VWAP and its related data per symbol

    async def calculate_vwap(self, symbol, candles_df):
        """
        Calculates VWAP for a given symbol.
        :param symbol: Trading symbol
        :param candles_df: Pandas DataFrame with columns 'high', 'low', 'close', 'volume'
        """
        if 'volume' not in candles_df.columns:
            logger.warning(f"Volume data not available for {symbol}. Cannot calculate VWAP.")
            return

        # Ensure correct column names for pandas_ta
        # pandas_ta expects 'high', 'low', 'close', 'volume'
        # It adds 'VWAP' column to the DataFrame
        candles_df.ta.vwap(append=True)
        
        if 'VWAP' in candles_df.columns:
            self.symbol_vwap_data[symbol] = candles_df['VWAP'].iloc[-1] # Get latest VWAP
            logger.debug(f"Calculated VWAP for {symbol}: {self.symbol_vwap_data[symbol]}")
        else:
            logger.error(f"VWAP calculation failed for {symbol}. Check pandas_ta setup and data.")

    async def check_signal(self, symbol, current_ltp):
        """
        Checks for VWAP signals (LTP crossing VWAP).
        :param symbol: Trading symbol
        :param current_ltp: Current Last Traded Price
        :return: 'BUY', 'SELL', or None
        """
        if symbol in self.symbol_vwap_data:
            vwap = self.symbol_vwap_data[symbol]
            if current_ltp > vwap:
                logger.info(f"VWAP BUY signal for {symbol}: LTP {current_ltp} > VWAP {vwap}")
                return "BUY"
            elif current_ltp < vwap:
                logger.info(f"VWAP SELL signal for {symbol}: LTP {current_ltp} < VWAP {vwap}")
                return "SELL"
        return None

# Example Usage (This would be integrated into main.py or a data processing module)
if __name__ == "__main__":
    # Dummy data for demonstration (replace with actual historical data)
    data = {
        'high': [100, 102, 101, 103, 104, 105, 106, 107],
        'low': [98, 99, 97, 98, 99, 100, 101, 102],
        'close': [99, 101, 98, 100, 103, 104, 105, 106],
        'volume': [1000, 1200, 900, 1500, 1100, 1300, 1000, 1400]
    }
    candles_df = pd.DataFrame(data)
    
    vwap_strategy = VWAPStrategy()
    asyncio.run(vwap_strategy.calculate_vwap("NSE:EXAMPLE-EQ", candles_df))

    # Test signals
    print(f"Signal for 103 (assuming VWAP around 102): {asyncio.run(vwap_strategy.check_signal('NSE:EXAMPLE-EQ', 103))}")
    print(f"Signal for 101 (assuming VWAP around 102): {asyncio.run(vwap_strategy.check_signal('NSE:EXAMPLE-EQ', 101))}")
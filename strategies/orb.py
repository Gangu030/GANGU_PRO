import pandas as pd
import logging

logger = logging.getLogger(__name__)

class ORBStrategy:
    def __init__(self, open_range_minutes=15):
        self.open_range_minutes = open_range_minutes
        self.open_range_high = {}
        self.open_range_low = {}
        self.orb_initialized = {}

    async def calculate_orb(self, symbol, candles_df):
        """
        Calculates the Open Range for a given symbol.
        :param symbol: Trading symbol (e.g., NSE:NIFTY50-INDEX)
        :param candles_df: Pandas DataFrame with columns 'datetime', 'high', 'low'
        """
        if symbol not in self.orb_initialized:
            # Filter candles for the open range period (e.g., first 15 minutes)
            # Assuming candles_df is sorted by datetime and contains 1-minute or similar granular data
            
            # This is a simplification. In a real scenario, you'd define market open time
            # and slice candles based on that.
            first_n_candles = candles_df.head(self.open_range_minutes)
            
            if not first_n_candles.empty:
                self.open_range_high[symbol] = first_n_candles['high'].max()
                self.open_range_low[symbol] = first_n_candles['low'].min()
                self.orb_initialized[symbol] = True
                logger.info(f"ORB initialized for {symbol}: High={self.open_range_high[symbol]}, Low={self.open_range_low[symbol]}")
            else:
                logger.warning(f"Not enough data to initialize ORB for {symbol}")
        
    async def check_signal(self, symbol, current_ltp):
        """
        Checks for ORB breakout signals.
        :param symbol: Trading symbol
        :param current_ltp: Current Last Traded Price
        :return: 'BUY', 'SELL', or None
        """
        if symbol in self.orb_initialized:
            orb_high = self.open_range_high[symbol]
            orb_low = self.open_range_low[symbol]

            if current_ltp > orb_high:
                logger.info(f"ORB BUY signal for {symbol}: LTP {current_ltp} > ORB High {orb_high}")
                return "BUY"
            elif current_ltp < orb_low:
                logger.info(f"ORB SELL signal for {symbol}: LTP {current_ltp} < ORB Low {orb_low}")
                return "SELL"
        return None

# Example Usage (This would be integrated into main.py or a data processing module)
if __name__ == "__main__":
    # Dummy data for demonstration (replace with actual historical data)
    data = {
        'datetime': pd.to_datetime(['2023-01-01 09:15:00', '2023-01-01 09:16:00', '2023-01-01 09:17:00', '2023-01-01 09:18:00',
                                    '2023-01-01 09:19:00', '2023-01-01 09:20:00', '2023-01-01 09:21:00', '2023-01-01 09:22:00']),
        'high': [100, 102, 101, 103, 104, 105, 106, 107],
        'low': [98, 99, 97, 98, 99, 100, 101, 102],
        'close': [99, 101, 98, 100, 103, 104, 105, 106]
    }
    candles_df = pd.DataFrame(data)
    
    orb_strategy = ORBStrategy(open_range_minutes=5)
    asyncio.run(orb_strategy.calculate_orb("NSE:EXAMPLE-EQ", candles_df))

    # Test signals
    print(f"Signal for 99: {asyncio.run(orb_strategy.check_signal('NSE:EXAMPLE-EQ', 99))}")
    print(f"Signal for 105: {asyncio.run(orb_strategy.check_signal('NSE:EXAMPLE-EQ', 105))}")
    print(f"Signal for 97: {asyncio.run(orb_strategy.check_signal('NSE:EXAMPLE-EQ', 97))}")
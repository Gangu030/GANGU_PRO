import os
import json
import logging
import asyncio
from datetime import datetime, time, timedelta
from fyers_apiv3.fyersModel import FyersModel
from fyers_apiv3.FyersWebsocket import data_ws
from config import FYERS_APP_ID, FYERS_SECRET_KEY, FYERS_REDIRECT_URI

from keep_alive import keep_alive

# --- Configuration ---
AUTH_CODE_FILE = "fyers_token.json"
LOGS_DIR = "logs"

# Define the instruments you want to subscribe to
SYMBOLS_TO_SUBSCRIBE = ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ"]

# Strategy Parameters
SHORT_SMA_PERIOD = 5
LONG_SMA_PERIOD = 20
CANDLE_HISTORY_LIMIT = max(SHORT_SMA_PERIOD, LONG_SMA_PERIOD) + 5

# NEW: Trading Parameters
TRADE_QUANTITY = 1  # Example quantity - Adjust based on your capital and risk
TARGET_PERCENTAGE = 0.5  # 0.5% target profit
STOP_LOSS_PERCENTAGE = 0.25  # 0.25% stop loss
TRAILING_SL_POINTS = 0.1  # Example: 0.1 Rupee trailing stop loss (adjust based on tick size and price)

# Global variables
fyers_ws_client = None
live_candles = {}
completed_candle_history = {symbol: [] for symbol in SYMBOLS_TO_SUBSCRIBE}

# NEW: Track current positions (simple in-memory tracker)
# Structure: { "SYMBOL": {"side": "BUY" or "SELL", "quantity": QTY, "entry_price": PRICE} }
current_positions = {}

# FyersModel instance for REST API calls (will be initialized in main)
fyers_rest_client = None

# --- Logging Setup ---
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(
                            os.path.join(LOGS_DIR, "main_app.log")),
                        logging.StreamHandler()
                    ])


# --- Token Loading Function ---
def get_saved_access_token():
    """Loads the Fyers access token from the saved file."""
    if os.path.exists(AUTH_CODE_FILE):
        try:
            with open(AUTH_CODE_FILE, 'r') as f:
                token_data = json.load(f)
                access_token = token_data.get("access_token")
                if access_token:
                    logging.info("Successfully loaded Fyers access token.")
                    return access_token
        except json.JSONDecodeError:
            logging.error(
                f"Error decoding {AUTH_CODE_FILE}. Token file might be corrupted."
            )
        except Exception as e:
            logging.error(
                f"An unexpected error occurred while reading token file: {e}")
    logging.warning("Fyers access token not found or could not be loaded.")
    return None


# --- WebSocket Callback Functions ---


def on_open():
    """Called when the WebSocket connection is established."""
    logging.info(
        "WebSocket connection established. Subscribing to instruments...")
    if fyers_ws_client:
        fyers_ws_client.subscribe(symbols=SYMBOLS_TO_SUBSCRIBE,
                                  data_type="MarketData")
        logging.info(f"Subscribed to: {SYMBOLS_TO_SUBSCRIBE} for MarketData.")
    else:
        logging.error(
            "Fyers WebSocket client not initialized in on_open callback.")


def on_message(message):
    """
    Called when a new message (market data) is received.
    Processes the tick data and updates live 1-minute candles.
    """
    try:
        if isinstance(message, list):
            for data_item in message:
                process_market_data(data_item)
        elif isinstance(message, dict):
            process_market_data(message)
    except Exception as e:
        logging.error(f"Error processing WebSocket message: {e}")


def process_market_data(data_item):
    """Helper function to process individual market data items."""
    global live_candles

    if data_item.get('type') != 'df':
        logging.debug(
            f"Skipping non-data message: {data_item.get('type')} - {data_item.get('message')}"
        )
        return

    symbol = data_item.get("symbol")
    ltp = data_item.get("ltp")
    vol_traded_today = data_item.get("vol_traded_today")

    if not symbol or ltp is None:
        logging.warning(
            f"Skipping malformed data item (missing symbol/ltp): {data_item}")
        return

    try:
        current_ts_epoch = data_item.get("timestamp") or data_item.get(
            "last_traded_time")
        if current_ts_epoch:
            current_time = datetime.fromtimestamp(current_ts_epoch)
        else:
            current_time = datetime.now()
            logging.warning(
                f"Timestamp missing for {symbol}, using current time: {current_time}"
            )

    except Exception as e:
        logging.error(
            f"Error parsing timestamp for {symbol}: {e}. Data: {data_item}. Using current time."
        )
        current_time = datetime.now()

    current_minute_start = current_time.replace(second=0, microsecond=0)

    if symbol not in live_candles or live_candles[symbol][
            "timestamp"] != current_minute_start:
        logging.info(
            f"New 1-minute candle for {symbol} at {current_minute_start.strftime('%H:%M')}"
        )
        live_candles[symbol] = {
            "open": ltp,
            "high": ltp,
            "low": ltp,
            "close": ltp,
            "volume": 0,
            "cumulative_day_volume": vol_traded_today,
            "timestamp": current_minute_start
        }
    else:
        current_candle = live_candles[symbol]
        current_candle["high"] = max(current_candle["high"], ltp)
        current_candle["low"] = min(current_candle["low"], ltp)
        current_candle["close"] = ltp
        current_candle["cumulative_day_volume"] = vol_traded_today

    # logging.info(f"Updated {symbol} 1-min candle: "
    #              f"O={live_candles[symbol]['open']}, H={live_candles[symbol]['high']}, "
    #              f"L={live_candles[symbol]['low']}, C={live_candles[symbol]['close']}, "
    #              f"DailyVol={live_candles[symbol]['cumulative_day_volume']} "
    #              f"at {current_time.strftime('%H:%M:%S')}")


def on_error(error):
    """Called when a WebSocket error occurs."""
    logging.error(f"WebSocket Error: {error}")


def on_close():
    """Called when the WebSocket connection is closed."""
    logging.info("WebSocket connection closed.")


async def run_websocket_client(raw_access_token):
    """Initializes and runs the Fyers WebSocket client."""
    global fyers_ws_client

    websocket_formatted_token = f"{FYERS_APP_ID}:{raw_access_token}"
    logging.info(
        f"Using WebSocket token format: {FYERS_APP_ID}:<your_token_starts_here...> (masked for security)"
    )

    fyers_ws_client = data_ws.FyersDataSocket(
        access_token=websocket_formatted_token,
        log_path=LOGS_DIR,
        litemode=False,
        write_to_file=False,
        reconnect=True,
        on_connect=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)

    logging.info("Connecting to Fyers WebSocket...")
    fyers_ws_client.connect()


# --- Strategy Related Functions ---


def calculate_sma(data_points, period):
    """Calculates the Simple Moving Average (SMA) for a given period."""
    if len(data_points) < period:
        return None
    return sum(data_points[-period:]) / period


def check_sma_crossover(symbol):
    """
    Checks for a Simple Moving Average crossover signal.
    This function assumes completed_candle_history[symbol] is populated with enough candles.
    """
    history = completed_candle_history[symbol]

    if len(history) < LONG_SMA_PERIOD:
        return None

    close_prices = [candle['close'] for candle in history]

    short_sma = calculate_sma(close_prices, SHORT_SMA_PERIOD)
    long_sma = calculate_sma(close_prices, LONG_SMA_PERIOD)

    if short_sma is None or long_sma is None:
        return None

    if len(history) < LONG_SMA_PERIOD + 1:
        return None

    prev_close_prices = close_prices[:-1]
    prev_short_sma = calculate_sma(prev_close_prices, SHORT_SMA_PERIOD)
    prev_long_sma = calculate_sma(prev_close_prices, LONG_SMA_PERIOD)

    if prev_short_sma is None or prev_long_sma is None:
        return None

    signal = None
    if short_sma > long_sma and prev_short_sma <= prev_long_sma:
        signal = "BUY"
    elif short_sma < long_sma and prev_short_sma >= prev_long_sma:
        signal = "SELL"

    if signal:
        logging.info(
            f"STRATEGY SIGNAL for {symbol} at {history[-1]['timestamp'].strftime('%H:%M')}: {signal}!"
            f" (Short SMA: {short_sma:.2f}, Long SMA: {long_sma:.2f})")
    return signal


# NEW: Order Placement Function
def execute_trade(symbol, signal_type, current_price):
    """
    Executes a trade based on the signal using Fyers Bracket Order.
    This is a simplified example.
    """
    global current_positions, fyers_rest_client

    if fyers_rest_client is None:
        logging.error("Fyers REST client not initialized. Cannot place order.")
        return

    # Prevent re-entry if already in a position for this symbol
    if symbol in current_positions:
        logging.info(
            f"Already in a {current_positions[symbol]['side']} position for {symbol}. Skipping new entry."
        )
        return

    side = 1 if signal_type == "BUY" else -1  # 1 for BUY, -1 for SELL

    # Calculate target and stop loss prices
    target_price = current_price * (
        1 +
        TARGET_PERCENTAGE / 100) if signal_type == "BUY" else current_price * (
            1 - TARGET_PERCENTAGE / 100)
    stop_loss_price = current_price * (
        1 - STOP_LOSS_PERCENTAGE / 100
    ) if signal_type == "BUY" else current_price * (1 +
                                                    STOP_LOSS_PERCENTAGE / 100)

    # Fyers Bracket Order (BO) parameters
    # Note: priceType, productType, orderType, etc., are crucial.
    # Check Fyers API docs for exact parameters. Assuming "MARKET" entry.
    # For TSL, Fyers often uses `trailingStopLoss` in ticks or points.

    # Adjust target/stop-loss values to be in points/ticks from current price for Fyers API
    # Assuming `limitPrice` is for target, `stopLoss` is for stop loss points from entry.
    # Fyers BO requires `stopLoss` and `limitPrice` as absolute values, not points away.
    # The `price` parameter for the main order is the entry price.

    # Let's use the absolute difference for SL/TP as Fyers typically expects this for BO/CO.
    # Example: if entry is 100, target 0.5%, target price is 100.5.
    # Then `stopLoss` (absolute) = 0.25, `limitPrice` (absolute) = 0.5
    # (assuming `stopLoss` and `limitPrice` in BO order params are the absolute points difference)
    # This might require careful reading of Fyers API docs for exact interpretation of `stopLoss` and `limitPrice` in BO.
    # For now, let's assume `stopLoss` and `target` in the order payload are the points relative to the trigger price,
    # and `trailingStopLoss` is also relative.

    # If using absolute values:
    # `stopLossPrice` (absolute price where SL is triggered)
    # `targetPrice` (absolute price where target is hit)

    # Let's use relative points for `stopLoss` and `target` in the order request, as is common for BOs.
    # For example, if current price is 100, SL 0.25%, then SL points = 0.25. Target points = 0.5.
    sl_points = round(current_price * (STOP_LOSS_PERCENTAGE / 100), 2)
    tp_points = round(current_price * (TARGET_PERCENTAGE / 100), 2)

    order_data = {
        "symbol": symbol,
        "qty": TRADE_QUANTITY if signal_type == "BUY" else
        -TRADE_QUANTITY,  # Negative quantity for SELL
        "type":
        2,  # 2 for Limit Order, 1 for Market Order. Let's start with MARKET for entry.
        # For BO, the entry leg can be Market (1), Limit (2), or SL-M (3).
        "side": side,
        "productType": "BO",  # Bracket Order
        "limitPrice": 0,  # Not applicable for Market entry
        "stopPrice": 0,  # Not applicable for Market entry
        "validity": "DAY",  # DAY or IOC
        "disclosedQty": 0,
        "offlineOrder": False,
        "price": 0,  # Market order doesn't need price
        "orderType":
        1,  # This is the type of the main order leg (1 for MARKET)
        "stopLoss": sl_points,  # Stop loss in absolute points from entry
        "takeProfit": tp_points,  # Target profit in absolute points from entry
        "trailingStopLoss":
        TRAILING_SL_POINTS  # Trailing SL in absolute points from stopLoss
    }

    logging.info(
        f"Attempting to place {signal_type} BO for {symbol} at {current_price} "
        f"Qty: {order_data['qty']}, SL: {sl_points} points, TP: {tp_points} points, TSL: {TRAILING_SL_POINTS} points."
    )

    try:
        # Place the order
        # The Fyers place_order method is synchronous by default
        order_response = fyers_rest_client.place_order(data=order_data)

        if order_response and order_response.get("code") == 200:
            order_id = order_response.get("id")
            logging.info(
                f"Successfully placed {signal_type} Bracket Order for {symbol}. Order ID: {order_id}"
            )
            # Update local position tracker
            current_positions[symbol] = {
                "side": signal_type,
                "quantity": TRADE_QUANTITY,
                "entry_price": current_price,
                "order_id": order_id  # Store the main order ID
            }
        else:
            logging.error(
                f"Failed to place {signal_type} Bracket Order for {symbol}: {order_response}"
            )

    except Exception as e:
        logging.error(
            f"An error occurred while placing order for {symbol}: {e}")


# --- Main Application Logic ---
async def main():
    """Main function to run the application."""
    keep_alive()
    logging.info("Keep-alive web server started.")

    access_token = get_saved_access_token()

    if access_token:
        logging.info(
            "Access Token obtained. Testing REST API (profile fetch)...")
        try:
            global fyers_rest_client  # Declare global to assign to it
            fyers_rest_client = FyersModel(token=access_token,
                                           is_async=False,
                                           client_id=FYERS_APP_ID,
                                           log_path=LOGS_DIR)
            profile_response = fyers_rest_client.get_profile()

            if profile_response and profile_response.get("code") == 200:
                logging.info("Successfully fetched user profile via REST API.")
            else:
                logging.error(
                    f"Failed to fetch user profile via REST API: {profile_response}"
                )

        except Exception as e:
            logging.error(f"An error occurred during REST API call: {e}")

        logging.info("Starting WebSocket client for real-time data...")
        await run_websocket_client(access_token)

        last_minute_checked = None
        market_close_time_utc = time(10, 0, 0)  # 3:30 PM IST in UTC

        while True:
            current_datetime_utc = datetime.utcnow()
            current_time_utc = current_datetime_utc.time()

            if current_time_utc >= market_close_time_utc:
                logging.info(
                    f"Market close time ({market_close_time_utc.strftime('%H:%M')} UTC) reached. Exiting system."
                )
                # You might want to square off any open positions here before exiting.
                if fyers_ws_client:
                    # fyers_ws_client.close() # Or a similar method to explicitly close connection
                    pass
                break

            current_minute_start = current_datetime_utc.replace(second=0,
                                                                microsecond=0)

            if last_minute_checked is None or current_minute_start > last_minute_checked:
                for symbol in list(live_candles.keys()):
                    candle = live_candles[symbol]
                    candle_ts_utc_start = candle["timestamp"].replace(
                        second=0, microsecond=0)

                    if candle_ts_utc_start < current_minute_start:
                        logging.info(
                            f"1-Minute Candle CLOSED for {symbol}: "
                            f"Time={candle['timestamp'].strftime('%Y-%m-%d %H:%M')}, "
                            f"O={candle['open']}, H={candle['high']}, "
                            f"L={candle['low']}, C={candle['close']}, "
                            f"DailyVol={candle['cumulative_day_volume']}")

                        completed_candle_history[symbol].append(candle.copy())

                        if len(completed_candle_history[symbol]
                               ) > CANDLE_HISTORY_LIMIT:
                            completed_candle_history[symbol].pop(0)

                        signal = check_sma_crossover(symbol)
                        if signal:
                            # NEW: Execute the trade when a signal is generated
                            # Use the last closing price of the just-closed candle as the trigger price
                            current_price_for_trade = candle['close']
                            execute_trade(symbol, signal,
                                          current_price_for_trade)

                            # Simple exit for the day after a trade is placed (optional, for testing)
                            # You would remove this in a real system where you manage multiple trades.
                            # For simplicity, if we place an order, let's assume we are done for this simulation.
                            # This is just to prevent rapid-fire orders in a simple test.
                            # break # Uncomment this line if you want to exit after the first trade.

                last_minute_checked = current_minute_start

            await asyncio.sleep(0.5)

    else:
        logging.error(
            "No access token available. Please run `python3 -m fyers_api.auth` to generate it first."
        )


if __name__ == "__main__":
    asyncio.run(main())

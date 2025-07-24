import os
import asyncio
import logging
from datetime import datetime, time, timedelta
import pytz
from threading import Thread
from flask import Flask
import json

# Fyers API imports (ensure fyers-api is installed via requirements.txt)
try:
    from fyers_api import fyersModel
    from fyers_api.fyers_ws import FyersSocket
except ImportError:
    print(
        "Fyers API libraries not found. Please ensure 'fyers-api' is installed."
    )
    print("You might need to run: pip install fyers-api")
    exit(1)

# --- Configuration & Global Variables ---
# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
FYERS_APP_ID = os.environ.get('FYERS_APP_ID')
FYERS_ACCESS_TOKEN = os.environ.get('FYERS_ACCESS_TOKEN')
FYERS_SECRET_KEY = os.environ.get(
    'FYERS_SECRET_KEY')  # Usually not directly used in bot, but good to have

# Ensure essential environment variables are set
if not FYERS_APP_ID or not FYERS_ACCESS_TOKEN or not FYERS_SECRET_KEY:
    logging.error(
        "Missing one or more Fyers environment variables (FYERS_APP_ID, FYERS_ACCESS_TOKEN, FYERS_SECRET_KEY). Please set them."
    )
    exit(1)
else:
    logging.info("Fyers environment variables loaded.")
    logging.info("FYERS_ACCESS_TOKEN loaded from environment variable.")

# Global FyersModel instance
fyers_rest_client = None

# Global WebSocket client instance and data storage
fyers_ws_client = None
live_candles = {}  # Stores the latest 1-minute candle data for each symbol
completed_candle_history = {
}  # Stores completed 1-minute candles for SMA calculation
CANDLE_HISTORY_LIMIT = 200  # Number of 1-minute candles to keep for SMA calculation
SMA_FAST_PERIOD = 9
SMA_SLOW_PERIOD = 21

# --- Flask Keep-Alive Server ---
app = Flask(__name__)


@app.route('/')
def home():
    return "Fyers Trading Bot is running and keeping connection alive!"


def run_keep_alive():
    logging.info("Keep-alive web server started.")
    app.run(host='0.0.0.0', port=8080, debug=False)


# --- Fyers WebSocket Callbacks ---


def onmessage(message):
    global live_candles
    # logging.info(f"Raw WebSocket Message: {message}") # Uncomment for raw message debugging

    if isinstance(message, dict):
        if message.get('t') == 'df':  # Data frame message
            for candle_data in message.get('v', []):
                symbol = candle_data.get('symbol')
                if symbol:
                    # Convert timestamp to IST/UTC datetime object
                    # Fyers provides timestamp in epoch seconds (IST)
                    timestamp_ist_epoch = candle_data.get('timestamp')
                    if timestamp_ist_epoch:
                        timestamp_utc = datetime.fromtimestamp(
                            timestamp_ist_epoch,
                            tz=pytz.timezone('Asia/Kolkata')).astimezone(
                                pytz.utc)

                        # Update the latest 1-minute candle
                        live_candles[symbol] = {
                            'timestamp':
                            timestamp_utc,
                            'open':
                            candle_data.get('open'),
                            'high':
                            candle_data.get('high'),
                            'low':
                            candle_data.get('low'),
                            'close':
                            candle_data.get('close'),
                            'volume':
                            candle_data.get('vol'),
                            'cumulative_day_volume':
                            candle_data.get(
                                'short_mkt_qty')  # For cumulative day volume
                        }
                        # logging.info(f"Updated live candle for {symbol}: {live_candles[symbol]}") # Uncomment to see live candle updates
        elif message.get('t') == 'error':
            logging.error(f"WebSocket Error Message: {message.get('msg')}")
        elif message.get('t') == 'order_update':
            logging.info(f"Order Update: {message}")
        elif message.get('t') == 'order_status':
            logging.info(f"Order Status: {message}")
        else:
            logging.info(f"Received WebSocket data: {message}")
    else:
        logging.warning(
            f"Unexpected message type from WebSocket: {type(message)} - {message}"
        )


def onerror(message):
    logging.error(f"WebSocket Error: {message}")


def onopen():
    logging.info("Websocket connected")
    # Subscribing to market data for SBIN and RELIANCE
    data_type = "symbolData"  # "symbolData" for 1-minute candle, "depth" for market depth etc.
    symbols_to_subscribe = ['NSE:SBIN-EQ', 'NSE:RELIANCE-EQ']
    # If you want to use the 'token' based format for WebSocket (recommended by Fyers)
    # The format is 'token':'1,2,3...' where 1,2,3 are Fyers instrument tokens
    # You'll need to fetch instrument tokens via Fyers API first or hardcode them
    # For now, let's assume direct symbol string works for symbolData, if not use tokens
    # The `fyers-api` library often handles token conversion internally for subscribe with symbol strings.
    logging.info(
        f"WebSocket connection established. Subscribing to instruments...")
    fyers_ws_client.subscribe(symbols=symbols_to_subscribe,
                              data_type=data_type)
    logging.info(f"Subscribed to: {symbols_to_subscribe} for {data_type}.")


def onclose():
    logging.info("Websocket connection closed.")


# --- Fyers API Initialization ---


def authenticate_fyers(app_id, secret_key, access_token):
    """Initializes and returns the FyersModel client."""
    try:
        fyers = fyersModel.FyersModel(
            client_id=app_id,
            token=access_token,
            log_path=os.getcwd()  # Log path set to current working directory
        )
        logging.info(
            "Access Token obtained. Testing REST API (profile fetch)...")
        profile = fyers.get_profile()
        if profile and profile.get('s') == 'ok':
            logging.info("Successfully fetched user profile via REST API.")
            return fyers
        else:
            logging.error(f"Failed to fetch user profile: {profile}")
            return None
    except Exception as e:
        logging.error(
            f"Error during Fyers authentication or profile fetch: {e}")
        return None


def initialize_fyers_client(access_token):
    """Initializes and returns the FyersSocket WebSocket client."""
    try:
        # FyersSocket requires access_token in a specific format for WebSocket
        # It's usually FYERS_APP_ID + ":" + ACCESS_TOKEN
        # This is where your actual access token from the login flow or env var goes
        # For direct use from env var, ensure it's the complete token
        ws_token = f"{FYERS_APP_ID}:{access_token}"
        logging.info(
            f"Using WebSocket token format: {FYERS_APP_ID}:<your_token_starts_here...> (masked for security)"
        )

        data_socket = FyersSocket(
            access_token=ws_token,
            log_path=os.getcwd(),
            litemode=False,  # Set to True for Lite mode (only LTP)
            write_to_file=False,
            handler_message=onmessage,
            handler_error=onerror,
            handler_open=onopen,
            handler_close=onclose)
        logging.info("Connecting to Fyers WebSocket...")
        # Run the WebSocket connection in a separate thread to not block the main async loop
        Thread(target=data_socket.connect).start()
        return data_socket
    except Exception as e:
        logging.error(f"Error initializing Fyers WebSocket client: {e}")
        return None


# --- Trading Logic (SMA Crossover) ---


def calculate_sma(data, period):
    """Calculates Simple Moving Average."""
    if len(data) < period:
        return None
    return sum(c['close'] for c in data[-period:]) / period


def check_sma_crossover(symbol):
    """Checks for SMA crossover signals."""
    history = completed_candle_history.get(symbol)
    if not history or len(history) < SMA_SLOW_PERIOD:
        return None

    fast_sma = calculate_sma(history, SMA_FAST_PERIOD)
    slow_sma = calculate_sma(history, SMA_SLOW_PERIOD)

    if fast_sma is None or slow_sma is None:
        return None

    # Get previous SMAs for crossover check
    # Need at least two data points to check crossover
    if len(
            history
    ) < SMA_SLOW_PERIOD + 1:  # Need previous candle for previous SMA calculation
        return None

    prev_history = history[:
                           -1]  # History excluding the very last (current) candle
    prev_fast_sma = calculate_sma(prev_history, SMA_FAST_PERIOD)
    prev_slow_sma = calculate_sma(prev_history, SMA_SLOW_PERIOD)

    if prev_fast_sma is None or prev_slow_sma is None:
        return None

    if fast_sma > slow_sma and prev_fast_sma <= prev_slow_sma:
        logging.info(
            f"STRATEGY SIGNAL for {symbol}: BUY (Fast SMA crossed above Slow SMA)"
        )
        return "BUY"
    elif fast_sma < slow_sma and prev_fast_sma >= prev_slow_sma:
        logging.info(
            f"STRATEGY SIGNAL for {symbol}: SELL (Fast SMA crossed below Slow SMA)"
        )
        return "SELL"
    return None


def execute_trade(symbol, signal, price):
    """
    Executes a trade based on the signal.
    This is a placeholder. You need to implement actual order placement using fyers_rest_client.
    """
    if not fyers_rest_client:
        logging.error(
            "Fyers REST client not initialized. Cannot execute trade.")
        return

    # Example: Place a market order
    # Replace with your actual order parameters (e.g., quantity, product_type, order_type)
    order_params = {
        "symbol": symbol,
        "qty": 1,  # Example quantity
        "type":
        2,  # 1: Limit Order, 2: Market Order, 3: Stop Order, 4: Stop Limit Order
        "side": 1 if signal == "BUY" else -1,  # 1: Buy, -1: Sell
        "productType": "INTRADAY",  # INTRADAY, CNC, MARGIN, CO, BO
        "limitPrice": 0,
        "stopPrice": 0,
        "validity": "DAY",  # DAY, IOC
        "disclosedQty": 0,
        "offlineOrder": False,
        "orderTag": "my_algo_trade"  # Optional tag
    }

    try:
        logging.info(
            f"Attempting to place {signal} order for {symbol} at price {price}..."
        )
        response = fyers_rest_client.place_order(data=order_params)
        if response and response.get('s') == 'ok':
            order_id = response.get('id')
            logging.info(
                f"Successfully placed {signal} order for {symbol}. Order ID: {order_id}"
            )
            logging.info(f"Order response: {response}")
        else:
            logging.error(
                f"Failed to place {signal} order for {symbol}: {response}")
    except Exception as e:
        logging.error(f"Error placing order for {symbol}: {e}")


# --- Main Bot Logic ---


async def main():
    global fyers_rest_client, fyers_ws_client, live_candles, completed_candle_history

    # Start the Flask keep-alive server in a separate thread
    keep_alive_thread = Thread(target=run_keep_alive)
    keep_alive_thread.daemon = True  # Daemonize thread so it exits when main program exits
    keep_alive_thread.start()

    # Authenticate Fyers REST API
    fyers_rest_client = authenticate_fyers(FYERS_APP_ID, FYERS_SECRET_KEY,
                                           FYERS_ACCESS_TOKEN)
    if not fyers_rest_client:
        logging.error("Failed to initialize Fyers REST client. Exiting.")
        return

    # Initialize Fyers WebSocket client
    fyers_ws_client = initialize_fyers_client(FYERS_ACCESS_TOKEN)
    if not fyers_ws_client:
        logging.error("Failed to initialize Fyers WebSocket client. Exiting.")
        return

    # Initialize candle history for subscribed symbols
    symbols_to_subscribe = ['NSE:SBIN-EQ', 'NSE:RELIANCE-EQ']
    for symbol in symbols_to_subscribe:
        completed_candle_history[symbol] = []
        live_candles[symbol] = {
        }  # Initialize empty live candle for each symbol

    # Define market hours in UTC (IST is UTC + 5:30)
    # 9:15 AM IST = 3:45 AM UTC
    # 3:30 PM IST = 10:00 AM UTC
    market_open_time_utc = time(3, 45, 0)
    market_close_time_utc = time(10, 0, 0)

    last_minute_checked = None

    while True:
        current_datetime_utc = datetime.utcnow()
        current_time_utc = current_datetime_utc.time()

        # Check if within market hours to process candles and trade
        if market_open_time_utc <= current_time_utc < market_close_time_utc:
            current_minute_start = current_datetime_utc.replace(second=0,
                                                                microsecond=0)

            if last_minute_checked is None or current_minute_start > last_minute_checked:
                for symbol in list(live_candles.keys()):
                    candle = live_candles.get(
                        symbol
                    )  # Use .get to avoid KeyError if symbol not yet updated
                    if not candle: continue  # Skip if no live candle data yet

                    candle_ts_utc_start = candle["timestamp"].replace(
                        second=0, microsecond=0)

                    # Process only if the candle timestamp is for a past minute
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
                            # Execute the trade when a signal is generated
                            current_price_for_trade = candle['close']
                            execute_trade(symbol, signal,
                                          current_price_for_trade)

                last_minute_checked = current_minute_start

            await asyncio.sleep(0.5
                                )  # Poll more frequently within market hours

        elif current_time_utc >= market_close_time_utc:
            logging.info(
                f"Market close time ({market_close_time_utc.strftime('%H:%M')} UTC) reached. Exiting system."
            )
            # No explicit close needed for fyers_ws_client as program termination handles it.
            break  # Exit the loop and end the program after market close

        else:  # Before market open
            logging.info(
                f"Market not yet open. Current UTC time: {current_time_utc.strftime('%H:%M:%S')}. Waiting for market open (UTC {market_open_time_utc.strftime('%H:%M')})."
            )
            await asyncio.sleep(60)  # Sleep longer if market is closed


# --- Main Execution ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped manually.")
    except Exception as e:
        logging.critical(f"An unhandled error occurred: {e}", exc_info=True)

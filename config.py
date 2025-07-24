import os
from datetime import time

# --- Fyers API Configuration ---
# It's highly recommended to set these as Replit Secrets (Environment Variables)
# Go to "Secrets" tab (lock icon) in Replit and add:
# FYERS_APP_ID, FYERS_SECRET_KEY, FYERS_REDIRECT_URI
FYERS_APP_ID = os.getenv("FYERS_APP_ID",
                         "Q4LF1M847E-100")  # REPLACE WITH YOUR ACTUAL APP ID
FYERS_SECRET_KEY = os.getenv(
    "FYERS_SECRET_KEY", "Q1MNJE45D1")  # REPLACE WITH YOUR ACTUAL SECRET KEY
FYERS_REDIRECT_URI = os.getenv(
    "FYERS_REDIRECT_URI",
    "https://trade.fyers.in/api-login/redirect-uri/index.html")
FYERS_TOKEN_FILE = "fyers_token.json"  # File to store the access token

# --- Telegram Bot Credentials (Optional, if using Telegram for alerts) ---
# Set these as Replit Secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "7035988656:AAFDZUIAmcEtc2_vT6ocbgYP8klvE7FqV5s")  # REPLACE
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7470969874")  # REPLACE

# --- Trading Parameters ---
TRADE_QUANTITY = 1  # Default quantity for trades (ALWAYS START WITH MINIMUM FOR TESTING)

# PRODUCT_TYPE: CRITICAL for Bracket Orders, must be "BO"
PRODUCT_TYPE = "BO"  # For Bracket Orders (e.g., CNC for delivery, INTRADAY for regular intraday)

# ORDER_TYPE: 1 for Market, 2 for Limit, 3 for Stop, 4 for Stop-Limit
ORDER_TYPE = 2  # Using Limit Order for entry in Bracket Order for better control
LIMIT_PRICE_BUFFER = 0.05  # For Limit orders (e.g., 0.05% above/below LTP for entry price)

# Bracket Order (BO) Parameters:
# These values are in POINTS (e.g., 0.50 means 0.50 Rupee away from entry price)
# IMPORTANT: Double-check Fyers API v3 documentation to confirm units for these parameters!
BO_STOP_LOSS_POINTS = 0.50  # Stop loss points away from entry price (e.g., 0.50 Rs)
BO_TARGET_PROFIT_POINTS = 1.00  # Target profit points away from entry price (e.g., 1.00 Rs)
BO_TRAILING_SL_POINTS = 0.25  # Trailing stop loss points (how much SL trails the price)

# --- Strategy Parameters (for SMA Crossover) ---
SHORT_SMA_PERIOD = 5  # Period for the short-term Simple Moving Average
LONG_SMA_PERIOD = 20  # Period for the long-term Simple Moving Average

# Symbols to Trade/Monitor in main.py
# Ensure these match what you actually subscribe to and want to trade
# These are the primary symbols for your core trading logic in main.py
SYMBOLS_TO_TRADE = [
    {
        "name": "SBIN",
        "fyers_symbol": "NSE:SBIN-EQ"
    }, {
        "name": "RELIANCE",
        "fyers_symbol": "NSE:RELIANCE-EQ"
    }
    # Add more symbols here that your main.py should actively track and trade
]

# Market Open/Close Times (UTC)
# Fyers real-time data and historical data often use UTC.
# IST (Indian Standard Time) is UTC+5:30.
# Indian Market Open: 9:15 AM IST = 3:45 AM UTC
# Indian Market Close: 3:30 PM IST = 10:00 AM UTC
market_open_time_utc = time(3, 45, 0)
market_close_time_utc = time(10, 0, 0)

# --- Dashboard Configuration (for dashboard/app.py) ---
# These are the symbols and strategies the dashboard will display.
# Consider making this list match SYMBOLS_TO_TRADE for consistency
# if main.py is the only source of data.
DASHBOARD_CONFIG = {
    "symbols": [
        {
            "name": "SBIN",
            "fyers_symbol": "NSE:SBIN-EQ",
            "segment": "EQUITY"
        },
        {
            "name": "RELIANCE",
            "fyers_symbol": "NSE:RELIANCE-EQ",
            "segment": "EQUITY"
        },
        # You can add more symbols here if you intend to display them on the dashboard,
        # but remember main.py needs to subscribe to them to provide live data.
        # Example:
        # {"name": "NIFTY50", "fyers_symbol": "NSE:NIFTY50-INDEX", "segment": "INDICES"},
        # {"name": "BANKNIFTY", "fyers_symbol": "NSE:NIFTYBANK-INDEX", "segment": "INDICES"},
        # {"name": "TCS", "fyers_symbol": "NSE:TCS-EQ", "segment": "EQUITY"},
    ],
    "strategies": {
        "SMA Crossover": {
            "enabled": True,
            "description": "Short SMA crosses Long SMA",
            "params": {}
        },
        "VWAP_Only": {
            "enabled": False,
            "description": "Volume Weighted Average Price Strategy",
            "params": {}
        },
        "ORB_Only": {
            "enabled": False,
            "description": "Opening Range Breakout Strategy",
            "params": {}
        },
        "VWAP_ORB": {
            "enabled": False,
            "description": "Combined VWAP and ORB Strategy",
            "params": {}
        },
        "GY_Strategy": {
            "enabled": False,
            "description": "Your custom GY Strategy",
            "params": {}
        },
    },
    "auto_trading_enabled":
    False,  # Global toggle for auto trading via dashboard
    "current_strategy_mode":
    "SMA Crossover"  # Default strategy selected on dashboard
}

# --- Log file paths ---
LOGS_DIR = "logs"
FYERS_DATA_SOCKET_LOG = os.path.join(LOGS_DIR, "fyersDataSocket.log")
FYERS_REQUESTS_LOG = os.path.join(LOGS_DIR, "fyersRequests.log")
APPLICATION_LOG = os.path.join(LOGS_DIR,
                               "application.log")  # Main application log

# Create logs directory if it doesn't exist
os.makedirs(LOGS_DIR, exist_ok=True)

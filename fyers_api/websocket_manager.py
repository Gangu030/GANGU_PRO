import asyncio
import json
import logging
from fyers_apiv3.FyersWebsocket import FyersWebsocket
from config import FYERS_APP_ID, FYERS_DATA_SOCKET_LOG

logger = logging.getLogger(__name__)

class FyersWebSocketManager:
    def __init__(self, access_token: str, telegram_sender_func):
        self.client_id = FYERS_APP_ID
        self.access_token = access_token
        self.telegram_sender = telegram_sender_func
        self.fyers_ws = None
        self.ltp_cache = {} # Cache for Last Traded Price

    def on_open(self):
        logger.info("Fyers WebSocket connection opened.")
        asyncio.create_task(self.telegram_sender("Fyers WebSocket connection opened."))

    async def on_message(self, message):
        """Callback function to handle incoming WebSocket messages."""
        # logger.debug(f"Received WebSocket message: {message}")
        try:
            data = json.loads(message)
            if data and data.get('t') == 'tf': # 't' for type, 'tf' for tickerfeed
                symbol = data.get('s')
                ltp = data.get('v', {}).get('lp') # Last Price
                
                if symbol and ltp is not None:
                    self.ltp_cache[symbol] = ltp
                    # logger.debug(f"Updated LTP for {symbol}: {ltp}")
                    # You can add more processing here, e.g., building OHLCV candles
                    # based on tick data
            
            # Additional logic for processing other types of messages (e.g., order updates)
            if data and data.get('t') == 'om': # Order messages
                logger.info(f"Order Update: {data}")
                order_status = data.get('v', {}).get('orderStatus', 'UNKNOWN')
                symbol_name = data.get('v', {}).get('symbol', 'N/A')
                order_id = data.get('v', {}).get('id', 'N/A')
                message_text = f"Order Update for {symbol_name} (ID: {order_id}): Status - {order_status}"
                asyncio.create_task(self.telegram_sender(message_text))


        except json.JSONDecodeError as e:
            logger.error(f"Error decoding WebSocket message JSON: {e} - Message: {message}")
        except Exception as e:
            logger.exception(f"Error processing WebSocket message: {e} - Message: {message}")

    def on_close(self):
        logger.warning("Fyers WebSocket connection closed.")
        asyncio.create_task(self.telegram_sender("Fyers WebSocket connection closed. Attempting to reconnect..."))
        # Implement re-connection logic here if needed
        # For simplicity, we'll let `connect` handle it, but you might need a loop.

    def on_error(self, message):
        logger.error(f"Fyers WebSocket error: {message}")
        asyncio.create_task(self.telegram_sender(f"Fyers WebSocket error: {message}"))

    def subscribe_to_symbols(self, symbols: list):
        """Sets the symbols to be subscribed to when connecting."""
        # The FyersWebsocket object needs to be initialized AFTER on_message etc. are defined
        # or it uses a different callback mechanism.
        # This will store symbols to be subscribed on connection.
        self.symbols_to_subscribe = symbols
        logger.info(f"Symbols configured for subscription: {symbols}")

    async def connect(self):
        """Connects to the Fyers WebSocket and starts listening for messages."""
        if not self.access_token:
            logger.error("Access token not available for WebSocket connection.")
            await self.telegram_sender("Fyers WebSocket connection failed: Access token missing.")
            return

        # FyersWebsocket requires client_id and access_token directly
        self.fyers_ws = FyersWebsocket(
            client_id=self.client_id,
            access_token=self.access_token,
            # Data handler receives raw JSON string, so we need to decode it in on_message
            data_type="symbolData", # 'symbolData' for LTP, 'orderUpdates' for order messages
            log_path=FYERS_DATA_SOCKET_LOG,
            litemode=True # Lite mode for faster tick data
        )

        self.fyers_ws.onconnect = self.on_open
        self.fyers_ws.onmessage = self.on_message
        self.fyers_ws.onclose = self.on_close
        self.fyers_ws.onerror = self.on_error

        # Start the WebSocket connection in a non-blocking way
        # The connect() method itself will manage the connection life cycle
        logger.info("Attempting to connect to Fyers WebSocket...")
        await self.fyers_ws.connect() # This is an async method
        
        # After successful connection, send subscription request
        if self.symbols_to_subscribe:
            await self.fyers_ws.subscribe(symbols=self.symbols_to_subscribe)
            logger.info(f"Subscription request sent for: {self.symbols_to_subscribe}")

    async def disconnect(self):
        """Disconnects from the Fyers WebSocket."""
        if self.fyers_ws:
            await self.fyers_ws.close()
            logger.info("Fyers WebSocket disconnected.")

    def get_ltp_cache(self):
        """Returns the current LTP cache."""
        return self.ltp_cache
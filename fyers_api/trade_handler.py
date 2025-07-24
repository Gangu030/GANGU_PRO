import logging
from fyers_apiv3.FyersAPI import FyersAPI
from fyers_apiv3.exceptions import exceptions
from config import TRADE_QUANTITY, PRODUCT_TYPE, ORDER_TYPE, LIMIT_PRICE_BUFFER

logger = logging.getLogger(__name__)

class FyersTradeHandler:
    def __init__(self, fyers_api_instance: FyersAPI, telegram_sender_func):
        self.fyers = fyers_api_instance
        self.telegram_sender = telegram_sender_func

    async def place_order(self, symbol: str, side: str, qty: int, order_type: int, price: float = 0.0):
        """
        Places an order with Fyers.
        :param symbol: Fyers instrument symbol (e.g., "NSE:NIFTY50-INDEX")
        :param side: "BUY" or "SELL"
        :param qty: Quantity to trade
        :param order_type: 1 for MARKET, 2 for LIMIT, 3 for STOP, 4 for STOP_LIMIT
        :param price: Required for LIMIT/STOP_LIMIT orders
        """
        if not self.fyers:
            await self.telegram_sender(f"Order placement failed for {symbol}: Fyers API not initialized.")
            logger.error(f"Order placement failed for {symbol}: Fyers API not initialized.")
            return None

        side_value = 1 if side.upper() == "BUY" else -1
        
        # Construct order payload
        order_payload = {
            "symbol": symbol,
            "qty": qty,
            "type": order_type,
            "side": side_value,
            "productType": PRODUCT_TYPE,
            "limitPrice": price if order_type in [2, 4] else 0,
            "stopPrice": price if order_type in [3, 4] else 0,
            "disclosedQty": 0,
            "validity": "DAY",
            "offlineOrder": False,
        }

        # For market orders, ensure limitPrice and stopPrice are 0
        if order_type == 1: # Market order
            order_payload["limitPrice"] = 0
            order_payload["stopPrice"] = 0
        elif order_type == 2: # Limit order
            if price == 0:
                logger.error(f"Limit order for {symbol} requires a price.")
                await self.telegram_sender(f"Order failed for {symbol}: Limit order requires a price.")
                return None
            order_payload["stopPrice"] = 0
        elif order_type == 3: # Stop order (SL-M)
             if price == 0:
                logger.error(f"Stop order for {symbol} requires a trigger price.")
                await self.telegram_sender(f"Order failed for {symbol}: Stop order requires a trigger price.")
                return None
             order_payload["limitPrice"] = 0
        elif order_type == 4: # Stop-Limit order (SL-L)
             if price == 0 or order_payload["stopPrice"] == 0:
                logger.error(f"Stop-Limit order for {symbol} requires both limitPrice and stopPrice.")
                await self.telegram_sender(f"Order failed for {symbol}: Stop-Limit order requires both limitPrice and stopPrice.")
                return None

        try:
            response = self.fyers.place_order(data=order_payload)
            logger.info(f"Order placement response for {symbol} ({side} {qty}): {response}")
            if response and response.get("code") == 200:
                order_id = response.get("id")
                await self.telegram_sender(f"✅ Order Placed for {symbol} ({side} {qty})! Order ID: {order_id}")
                return order_id
            else:
                message = response.get("message", "Unknown error during order placement")
                await self.telegram_sender(f"❌ Order Failed for {symbol} ({side} {qty}): {message}")
                logger.error(f"Order failed for {symbol}: {message}")
                return None
        except exceptions.FyersAPIError as e:
            logger.error(f"Fyers API Error placing order for {symbol}: {e}")
            await self.telegram_sender(f"❌ Fyers API Error placing order for {symbol}: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred during order placement for {symbol}: {e}")
            await self.telegram_sender(f"❌ Unexpected Error placing order for {symbol}: {e}")
        return None

    async def get_order_status(self, order_id: str):
        """Fetches the status of a specific order."""
        if not self.fyers:
            logger.error("Cannot get order status: Fyers API not initialized.")
            return None
        try:
            response = self.fyers.orderbook()
            if response and response.get("code") == 200:
                orders = response.get("orderBook", [])
                for order in orders:
                    if order.get("id") == order_id:
                        logger.info(f"Order status for {order_id}: {order.get('status')}")
                        return order
                logger.warning(f"Order ID {order_id} not found in order book.")
                return None
            else:
                message = response.get("message", "Unknown error fetching order book")
                logger.error(f"Failed to fetch order book: {message}")
                return None
        except exceptions.FyersAPIError as e:
            logger.error(f"Fyers API Error fetching order status for {order_id}: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred fetching order status for {order_id}: {e}")
        return None

    async def cancel_order(self, order_id: str):
        """Cancels a pending order."""
        if not self.fyers:
            logger.error("Cannot cancel order: Fyers API not initialized.")
            return False
        try:
            cancel_payload = {"id": order_id}
            response = self.fyers.cancel_order(data=cancel_payload)
            if response and response.get("code") == 200:
                logger.info(f"Order {order_id} cancelled successfully: {response}")
                await self.telegram_sender(f"Order {order_id} cancelled successfully.")
                return True
            else:
                message = response.get("message", "Unknown error during order cancellation")
                logger.error(f"Failed to cancel order {order_id}: {message}")
                await self.telegram_sender(f"Failed to cancel order {order_id}: {message}")
                return False
        except exceptions.FyersAPIError as e:
            logger.error(f"Fyers API Error cancelling order {order_id}: {e}")
            await self.telegram_sender(f"Fyers API Error cancelling order {order_id}: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred during order cancellation for {order_id}: {e}")
            await self.telegram_sender(f"Unexpected Error cancelling order {order_id}: {e}")
        return False
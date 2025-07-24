import telegram
import asyncio
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        self.chat_id = TELEGRAM_CHAT_ID
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Telegram BOT_TOKEN or CHAT_ID is not configured. Telegram alerts will not work.")

    async def send_message(self, message):
        """Sends a message to the configured Telegram chat ID."""
        if not self.bot or not self.chat_id:
            logger.error("Telegram bot not initialized. Cannot send message.")
            return

        try:
            # Use parse_mode=telegram.ParseMode.MARKDOWN_V2 for rich formatting
            # Be careful with special characters when using MARKDOWN_V2, they need escaping
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode=telegram.constants.ParseMode.HTML)
            logger.info(f"Telegram message sent: {message}")
        except telegram.error.TelegramError as e:
            logger.error(f"Telegram API Error sending message: {e}")
            logger.error(f"Check if bot token and chat ID are correct. Message: '{message}'")
        except Exception as e:
            logger.exception(f"Unexpected error sending Telegram message: {e}")

# Example Usage
if __name__ == "__main__":
    async def main():
        telegram_bot = TelegramBot()
        await telegram_bot.send_message("GANGU PRO Telegram Bot is online and ready! (Test Message)")

    # Run the async main function
    asyncio.run(main())
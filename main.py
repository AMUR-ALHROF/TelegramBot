#!/usr/bin/env python3

# Main entry point for the Treasure Hunter Telegram Bot

import logging
import asyncio
from bot import TreasureHunterBot  # ← لاحظ الاسم الصحيح هنا

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to start the bot"""
    try:
        # Initialize and start the bot
        bot = TreasureHunterBot()  # ← تأكد من التسمية الصحيحة
        await bot.start()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
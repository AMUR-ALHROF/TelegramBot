"""
Main Telegram bot implementation for Treasure Hunter Bot
"""

import logging
import asyncio
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    CallbackQueryHandler
)
from telegram.constants import ParseMode

from config import Config
from ai_analyzer import AIAnalyzer
from treasure_hunter import TreasureHunterGuide
from utils import RateLimiter, image_to_base64, format_response, escape_markdown
from database import DatabaseManager
from leaderboard import LeaderboardManager

logger = logging.getLogger(__name__)

class TreasureHunterBot:
    """Main bot class for treasure hunting assistance"""
    
    def __init__(self):
        """Initialize the bot with required components"""
        # Validate configuration
        Config.validate()
        
        # Initialize components
        self.ai_analyzer = AIAnalyzer(Config.OPENAI_API_KEY)
        self.treasure_guide = TreasureHunterGuide()
        self.rate_limiter = RateLimiter(Config.MAX_REQUESTS_PER_MINUTE)
        
        # Initialize database and leaderboard
        self.db_manager = DatabaseManager()
        self.leaderboard = LeaderboardManager(self.db_manager)
        
        # Initialize Telegram application
        self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
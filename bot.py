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
        
        # Initialize Telegram application
        self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        self.application.add_handler(CommandHandler("ask", self.ask_command))
        self.application.add_handler(CommandHandler("signal", self.signal_command))
        self.application.add_handler(CommandHandler("tips", self.tips_command))
        self.application.add_handler(CommandHandler("equipment", self.equipment_command))
        self.application.add_handler(CommandHandler("legal", self.legal_command))
        self.application.add_handler(CommandHandler("safety", self.safety_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            welcome_message = self.treasure_guide.get_welcome_message()
            
            # Create inline keyboard for quick actions
            keyboard = [
                [InlineKeyboardButton("📸 Analyze Image", callback_data="help_analyze")],
                [InlineKeyboardButton("❓ Ask Question", callback_data="help_ask")],
                [InlineKeyboardButton("📊 Signal Analysis", callback_data="help_signal")],
                [InlineKeyboardButton("💡 Get Tips", callback_data="tips")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                welcome_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("Welcome to Treasure Hunter Bot! Use /help for available commands.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            help_message = self.treasure_guide.get_help_message()
            
            # Split message if too long
            message_chunks = format_response(help_message)
            
            for chunk in message_chunks:
                await update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await update.message.reply_text("Help information is temporarily unavailable. Please try again later.")
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command"""
        try:
            instruction_text = """📸 **Image Analysis Instructions:**
            
To analyze an image for treasure hunting signals:

1️⃣ **Upload a clear photo** of your find, signal, or site
2️⃣ **Include a caption** with any specific questions or context
3️⃣ **Wait for AI analysis** - this may take a few moments

**Best Results Tips:**
• Use good lighting and clear focus
• Include size reference (coin, ruler, etc.)
• Photograph from multiple angles if needed
• Mention specific areas of interest

Upload your image now, and I'll provide detailed treasure hunting analysis! 🔍"""
            
            await update.message.reply_text(
                instruction_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error in analyze command: {e}")
            await update.message.reply_text("Please upload an image to analyze for treasure hunting signals.")
    
    async def ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ask command"""
        try:
            user_id = update.effective_user.id
            
            # Check rate limiting
            if not self.rate_limiter.is_allowed(user_id):
                wait_time = self.rate_limiter.get_wait_time(user_id)
                await update.message.reply_text(
                    f"⏰ Please wait {wait_time} seconds before asking another question."
                )
                return
            
            # Get question from command arguments
            question = " ".join(context.args) if context.args else ""
            
            if not question:
                await update.message.reply_text(
                    "❓ **Ask a Treasure Hunting Question:**\n\n"
                    "Usage: `/ask [your question]`\n\n"
                    "Examples:\n"
                    "• `/ask What's the best detector for beginners?`\n"
                    "• `/ask How deep can modern detectors find coins?`\n"
                    "• `/ask What are the best beaches for metal detecting?`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Get AI response
            result = await self.ai_analyzer.answer_treasure_question(question)
            
            if result["success"]:
                response_chunks = format_response(f"💡 **Answer:**\n\n{result['answer']}")
                
                for chunk in response_chunks:
                    await update.message.reply_text(
                        chunk,
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.message.reply_text(
                    f"❌ Sorry, I couldn't answer your question: {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in ask command: {e}")
            await update.message.reply_text("Sorry, I encountered an error processing your question. Please try again.")
    
    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signal command"""
        try:
            user_id = update.effective_user.id
            
            # Check rate limiting
            if not self.rate_limiter.is_allowed(user_id):
                wait_time = self.rate_limiter.get_wait_time(user_id)
                await update.message.reply_text(
                    f"⏰ Please wait {wait_time} seconds before analyzing another signal."
                )
                return
            
            # Get signal description from command arguments
            signal_description = " ".join(context.args) if context.args else ""
            
            if not signal_description:
                await update.message.reply_text(
                    "📊 **Signal Analysis Instructions:**\n\n"
                    "Usage: `/signal [description of your signal]`\n\n"
                    "Examples:\n"
                    "• `/signal Strong consistent tone at 6 inches, VDI shows 87`\n"
                    "• `/signal Choppy signal, jumps between iron and coin range`\n"
                    "• `/signal Deep target, faint signal, reads different from multiple angles`\n\n"
                    "Include details like:\n"
                    "• Signal strength and consistency\n"
                    "• Depth indication\n"
                    "• VDI/TID numbers\n"
                    "• Ground conditions\n"
                    "• Detector model and settings",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Get AI analysis
            result = await self.ai_analyzer.analyze_signal_pattern(signal_description)
            
            if result["success"]:
                response_chunks = format_response(f"📊 **Signal Analysis:**\n\n{result['analysis']}")
                
                for chunk in response_chunks:
                    await update.message.reply_text(
                        chunk,
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.message.reply_text(
                    f"❌ Sorry, I couldn't analyze your signal: {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in signal command: {e}")
            await update.message.reply_text("Sorry, I encountered an error analyzing your signal. Please try again.")
    
    async def tips_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tips command"""
        try:
            tips_message = self.treasure_guide.get_general_tips()
            message_chunks = format_response(tips_message)
            
            for chunk in message_chunks:
                await update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in tips command: {e}")
            await update.message.reply_text("Tips are temporarily unavailable. Please try again later.")
    
    async def equipment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /equipment command"""
        try:
            equipment_message = self.treasure_guide.get_equipment_recommendations()
            message_chunks = format_response(equipment_message)
            
            for chunk in message_chunks:
                await update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in equipment command: {e}")
            await update.message.reply_text("Equipment recommendations are temporarily unavailable. Please try again later.")
    
    async def legal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /legal command"""
        try:
            legal_message = self.treasure_guide.get_legal_guidelines()
            message_chunks = format_response(legal_message)
            
            for chunk in message_chunks:
                await update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in legal command: {e}")
            await update.message.reply_text("Legal guidelines are temporarily unavailable. Please try again later.")
    
    async def safety_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /safety command"""
        try:
            safety_message = self.treasure_guide.get_safety_guidelines()
            message_chunks = format_response(safety_message)
            
            for chunk in message_chunks:
                await update.message.reply_text(
                    chunk,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in safety command: {e}")
            await update.message.reply_text("Safety guidelines are temporarily unavailable. Please try again later.")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded photos for analysis"""
        try:
            user_id = update.effective_user.id
            
            # Check rate limiting
            if not self.rate_limiter.is_allowed(user_id):
                wait_time = self.rate_limiter.get_wait_time(user_id)
                await update.message.reply_text(
                    f"⏰ Please wait {wait_time} seconds before uploading another image."
                )
                return
            
            # Get the largest photo
            photo = update.message.photo[-1]
            
            # Download photo
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            file = await context.bot.get_file(photo.file_id)
            photo_data = await file.download_as_bytearray()
            
            # Convert to base64
            base64_image = image_to_base64(photo_data, Config.MAX_IMAGE_SIZE_MB)
            
            if not base64_image:
                await update.message.reply_text(
                    "❌ Sorry, I couldn't process this image. Please ensure it's under "
                    f"{Config.MAX_IMAGE_SIZE_MB}MB and in a supported format (JPG, PNG, etc.)."
                )
                return
            
            # Get user caption/question
            user_question = update.message.caption or ""
            
            # Analyze image
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            result = await self.ai_analyzer.analyze_treasure_image(base64_image, user_question)
            
            if result["success"]:
                response_chunks = format_response(f"🔍 **Image Analysis:**\n\n{result['analysis']}")
                
                for chunk in response_chunks:
                    await update.message.reply_text(
                        chunk,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                # Add helpful follow-up options
                keyboard = [
                    [InlineKeyboardButton("❓ Ask Follow-up", callback_data="help_ask")],
                    [InlineKeyboardButton("💡 Get Tips", callback_data="tips")],
                    [InlineKeyboardButton("🛠️ Equipment Help", callback_data="equipment")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "Need more help? Choose an option below:",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    f"❌ Sorry, I couldn't analyze your image: {result['error']}\n\n"
                    "Please try uploading a clear, well-lit photo."
                )
                
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await update.message.reply_text(
                "Sorry, I encountered an error analyzing your image. Please try again."
            )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages that aren't commands"""
        try:
            user_id = update.effective_user.id
            message_text = update.message.text
            
            # Check if it looks like a question
            question_indicators = ['?', 'what', 'how', 'where', 'when', 'why', 'which', 'can', 'should', 'help']
            
            if any(indicator in message_text.lower() for indicator in question_indicators):
                # Check rate limiting
                if not self.rate_limiter.is_allowed(user_id):
                    wait_time = self.rate_limiter.get_wait_time(user_id)
                    await update.message.reply_text(
                        f"⏰ Please wait {wait_time} seconds before asking another question."
                    )
                    return
                
                # Show typing indicator
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                
                # Answer the question
                result = await self.ai_analyzer.answer_treasure_question(message_text)
                
                if result["success"]:
                    response_chunks = format_response(f"💡 **Answer:**\n\n{result['answer']}")
                    
                    for chunk in response_chunks:
                        await update.message.reply_text(
                            chunk,
                            parse_mode=ParseMode.MARKDOWN
                        )
                else:
                    await update.message.reply_text(
                        f"❌ Sorry, I couldn't answer your question: {result['error']}"
                    )
            else:
                # Provide helpful guidance
                await update.message.reply_text(
                    "👋 Hi there! I'm here to help with treasure hunting questions and image analysis.\n\n"
                    "Try:\n"
                    "• Upload a photo for analysis 📸\n"
                    "• Ask a question about treasure hunting ❓\n"
                    "• Use /help for all available commands 💡"
                )
                
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await update.message.reply_text(
                "I'm here to help with treasure hunting! Use /help to see what I can do."
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses"""
        try:
            query = update.callback_query
            await query.answer()
            
            callback_data = query.data
            
            if callback_data == "help_analyze":
                await query.edit_message_text(
                    "📸 **Image Analysis Help:**\n\n"
                    "Upload any photo related to treasure hunting:\n"
                    "• Metal detecting finds\n"
                    "• Signals on your detector screen\n"
                    "• Potential hunting sites\n"
                    "• Artifacts or relics\n\n"
                    "I'll provide expert analysis and identification help!",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif callback_data == "help_ask":
                await query.edit_message_text(
                    "❓ **Ask Questions Help:**\n\n"
                    "Ask me anything about treasure hunting:\n"
                    "• Equipment recommendations\n"
                    "• Hunting techniques and tips\n"
                    "• Site research and selection\n"
                    "• Find identification\n"
                    "• Legal and safety guidelines\n\n"
                    "Just type your question or use `/ask [question]`",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif callback_data == "help_signal":
                await query.edit_message_text(
                    "📊 **Signal Analysis Help:**\n\n"
                    "Describe your metal detecting signals:\n"
                    "• Signal strength and consistency\n"
                    "• Depth readings\n"
                    "• VDI/TID numbers\n"
                    "• Detector model and settings\n\n"
                    "Use `/signal [description]` for detailed analysis!",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif callback_data == "tips":
                await self.tips_command(update, context)
            elif callback_data == "equipment":
                await self.equipment_command(update, context)
                
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await query.edit_message_text("Sorry, something went wrong. Please try again.")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "🔧 Sorry, I encountered a technical issue. Please try again in a moment."
                )
            except Exception as e:
                logger.error(f"Error sending error message: {e}")
    
    async def start(self):
        """Start the bot"""
        try:
            logger.info("Starting Treasure Hunter Bot...")
            
            # Start the application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Bot started successfully!")
            
            # Keep the bot running
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
        finally:
            # Cleanup
            await self.application.stop()
            await self.application.shutdown()

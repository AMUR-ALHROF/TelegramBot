import os
import logging
import asyncio

# لا نحتاج لاستيراد Flask إذا لم نستخدمه كخادم ويب أساسي
# from flask import Flask, request, abort

# استيراد مكونات البوت الخاصة بك
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)
from telegram.constants import ParseMode # تأكد من استيراد ParseMode

from config import Config
from ai_analyzer import AIAnalyzer
from treasure_hunter import TreasureHunterGuide
from utils import RateLimiter, image_to_base64, format_response, escape_markdown
from database import DatabaseManager
from leaderboard import LeaderboardManager

# إعداد السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة البوت ومكوناته
class TreasureHunterBot:
    """Main bot class for treasure hunting assistance"""

    def __init__(self):
        """Initialize the bot with required components"""
        # Validate configuration
        try:
            Config.validate()
            logger.info("Configuration validated successfully.")
        except ValueError as e:
            logger.critical(f"Critical configuration error: {e}")
            # sys.exit(1) # يمكن تفعيل هذا للخروج المبكر إذا كانت هناك أخطاء حرجة في التكوين

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

        # *** تم إزالة منطق initialize() من هنا ***
        # سيتم تهيئة التطبيق تلقائيًا عند تشغيل run_webhook()

    def _setup_handlers(self):
        """Setup all command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        # تفعيل معالجات الرسائل والصور وزر الكول باك
        self.application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, self.photo_message_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message_handler))
        self.application.add_handler(CallbackQueryHandler(self.callback_query_handler))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends a welcome message when the command /start is issued."""
        user = update.effective_user
        if user:
            logger.info(f"Received /start command from user: {user.id} ({user.full_name})")
            await update.message.reply_html(
                rf"أهلاً بك {escape_markdown(user.first_name)}! 👋"
                + "\nأنا هنا لأساعدك في رحلة البحث عن الكنوز.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("ابدأ البحث 🔍", callback_data="start_hunt")]
                ])
            )
        else:
            logger.warning("Received /start command but effective_user is None.")
            await update.message.reply_text("أهلاً بك! أنا هنا لأساعدك في رحلة البحث عن الكنوز.")

    async def photo_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles incoming photo messages."""
        user = update.effective_user
        if not user:
            logger.warning("Received photo message but effective_user is None.")
            return

        logger.info(f"Received photo from user: {user.id} ({user.full_name})")

        if not self.rate_limiter.check_limit(user.id):
            await update.message.reply_text("لقد تجاوزت حد الطلبات المسموح به. يرجى المحاولة لاحقاً.")
            return

        try:
            file_id = update.message.photo[-1].file_id
            new_file = await context.bot.get_file(file_id)
            image_url = new_file.file_path
            logger.info(f"Downloading image from: {image_url}")

            base64_image = await asyncio.to_thread(image_to_base64, image_url)

            if not base64_image:
                await update.message.reply_text("عذراً، لم أستطع معالجة الصورة.")
                return

            await update.message.reply_text("جاري تحليل الصورة... يرجى الانتظار.")

            analysis_result = await self.ai_analyzer.analyze_image_for_treasure(base64_image)

            response_text = format_response(analysis_result)
            await update.message.reply_markdown_v2(response_text)

        except Exception as e:
            logger.error(f"Error processing photo from user {user.id}: {e}", exc_info=True)
            await update.message.reply_text("عذراً، حدث خطأ أثناء معالجة الصورة.")

    async def text_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles incoming text messages."""
        user = update.effective_user
        if not user:
            logger.warning("Received text message but effective_user is None.")
            return

        text = update.message.text
        logger.info(f"Received text '{text}' from user: {user.id} ({user.full_name})")

        if not self.rate_limiter.check_limit(user.id):
            await update.message.reply_text("لقد تجاوزت حد الطلبات المسموح به. يرجى المحاولة لاحقاً.")
            return

        try:
            await update.message.reply_text("جاري معالجة طلبك... يرجى الانتظار.")

            analysis_result = await self.ai_analyzer.analyze_text_for_treasure(text)

            response_text = format_response(analysis_result)
            await update.message.reply_markdown_v2(response_text)

        except Exception as e:
            logger.error(f"Error processing text from user {user.id}: {e}", exc_info=True)
            await update.message.reply_text("عذراً، حدث خطأ أثناء معالجة رسالتك النصية.")

    async def callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles callback queries from inline keyboard buttons."""
        query = update.callback_query
        user = query.effective_user
        if not user:
            logger.warning("Received callback query but effective_user is None.")
            return

        logger.info(f"Received callback query '{query.data}' from user: {user.id} ({user.full_name})")

        await query.answer()

        try:
            if query.data == "start_hunt":
                await query.edit_message_text(text="حسناً، لكي أساعدك في رحلة البحث عن الكنوز، يمكنك إرسال:")
                await query.message.reply_text(
                    "1️⃣  **صورة** لمكان أو علامة تعتقد أنها قد تكون مرتبطة بكنز.\n"
                    "2️⃣  **وصف نصي** للمكان أو العلامة أو أي معلومات لديك.\n\n"
                    "سأقوم بتحليل المعلومات وتقديم الإرشادات.",
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logger.error(f"Error processing callback query from user {user.id}: {e}", exc_info=True)
            await query.edit_message_text(text="عذراً، حدث خطأ أثناء معالجة طلبك.")

# إنشاء كائن البوت (instance)
bot_instance = TreasureHunterBot()
application = bot_instance.application # اختصار للوصول إلى Application object

# نقطة الدخول الرئيسية للخدمة (في Render)
if __name__ == '__main__':
    # الحصول على الـ URL الخارجي من متغيرات بيئة Render
    WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")
    if not WEBHOOK_URL:
        logger.critical("RENDER_EXTERNAL_URL environment variable not set. Cannot run webhook.")
        # Fallback to local polling if URL is not set (for local development)
        logger.info("Running bot with long polling locally as RENDER_EXTERNAL_URL is not set.")
        async def run_local_bot():
            await application.run_polling(drop_pending_updates=True)
        asyncio.run(run_local_bot())
    else:
        # هذه هي الطريقة الصحيحة لتشغيل البوت بـ Webhook في الإنتاج
        logger.info(f"Starting webhook for Telegram Bot at {WEBHOOK_URL}/webhook")
        # يجب أن يكون المنفذ هو 10000 في Render
        PORT = int(os.environ.get("PORT", 10000))

        # تشغيل الويب هوك. Application.run_webhook تتولى كل شيء (HTTP Server, Event Loop)
        # وهذا يحل مشكلة "Event loop is closed"
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook", # المسار الذي ستستقبل عليه التحديثات
            webhook_url=f"{WEBHOOK_URL}/webhook" # الـ URL الكامل للـ Webhook
        )
else:
    # هذا الجزء ليس مطلوباً لـ Render إذا استخدمنا 'python main.py' كأمر تشغيل
    # ولكن يمكن إبقاؤه لأي استخدامات مستقبلية حيث يتم استيراد main.py كوحدة
    logger.info("main.py is being imported. This path is for non-direct execution (e.g., specific WSGI/ASGI servers).")
    pass

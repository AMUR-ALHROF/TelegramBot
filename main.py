import os
import logging
from flask import Flask, request, abort
import asyncio
import threading

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

# تهيئة تطبيق Flask
app = Flask(__name__)

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
            # sys.exit(1)

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

        # تهيئة التطبيق عند بناء البوت في بيئة الويب
        try:
            if not asyncio.get_event_loop().is_running():
                asyncio.run(self.application.initialize())
            else:
                asyncio.create_task(self.application.initialize())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.application.initialize())
            loop.close()

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

    # ** يجب أن تكون هذه الدوال موجودة لديك في ملف main.py أو في ملفات أخرى مستوردة **
    # ** إذا لم تكن موجودة أو فارغة، سيؤدي ذلك إلى أخطاء (AttributeError). **

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
            # افتراض أن الصورة هي الأكبر جودة
            file_id = update.message.photo[-1].file_id
            new_file = await context.bot.get_file(file_id)
            # استخدام path وليس file_path لأنه Render قد يتطلب مسار محلي
            # أو تحميل مباشر للبيانات إذا كان الحجم كبيرا
            # For simplicity, let's assume get_file provides a direct download URL
            image_url = new_file.file_path
            logger.info(f"Downloading image from: {image_url}")

            # يجب أن تقوم دالة image_to_base64 بتحميل الصورة من الـ URL
            # وتحويلها إلى Base64
            base64_image = await asyncio.to_thread(image_to_base64, image_url) # استخدام asyncio.to_thread إذا كانت دالة image_to_base64 متزامنة

            if not base64_image:
                await update.message.reply_text("عذراً، لم أستطع معالجة الصورة.")
                return

            await update.message.reply_text("جاري تحليل الصورة... يرجى الانتظار.")

            # تحليل الصورة
            analysis_result = await self.ai_analyzer.analyze_image_for_treasure(base64_image)

            # تنسيق وإرسال الرد
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

            # تحليل النص
            analysis_result = await self.ai_analyzer.analyze_text_for_treasure(text)

            # تنسيق وإرسال الرد
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

        # Always answer callback queries, even if just an empty one
        await query.answer()

        try:
            if query.data == "start_hunt":
                await query.edit_message_text(text="حسناً، لكي أساعدك في رحلة البحث عن الكنوز، يمكنك إرسال:")
                await query.message.reply_text(
                    "1️⃣  **صورة** لمكان أو علامة تعتقد أنها قد تكون مرتبطة بكنز.\n"
                    "2️⃣  **وصف نصي** للمكان أو العلامة أو أي معلومات لديك.\n\n"
                    "سأقوم بتحليل المعلومات وتقديم الإرشادات.",
                    parse_mode="Markdown"
                )
            # يمكنك إضافة المزيد من حالات query.data هنا
            # elif query.data == "another_action":
            #     await query.edit_message_text(text="Executing another action...")
        except Exception as e:
            logger.error(f"Error processing callback query from user {user.id}: {e}", exc_info=True)
            await query.edit_message_text(text="عذراً، حدث خطأ أثناء معالجة طلبك.")


# إنشاء كائن البوت (instance)
bot_instance = TreasureHunterBot()

# ربط Flask بالـ Webhook الخاص بـ Telegram
@app.route('/webhook', methods=['POST'])
async def webhook():
    """Handle incoming webhook updates from Telegram."""
    if request.method == "POST":
        update_json = request.get_json()
        if not update_json:
            logger.warning("Received POST request without JSON data.")
            abort(400) # Bad Request

        logger.info(f"Received webhook update: {update_json.get('update_id')}")

        # Run the async processing in a separate thread to avoid Flask's event loop conflicts
        threading.Thread(target=lambda: asyncio.run(bot_instance.application.process_update(
            Update.de_json(update_json, bot_instance.application.bot)
        ))).start()

        return 'ok' # Return 'ok' quickly to Telegram to avoid timeouts.
    return 'Method Not Allowed', 405

@app.route('/')
def home():
    logger.info("Home route accessed. Flask is responding.")
    return "✅ خدمة الويب (Flask) تعمل بنجاح."

if __name__ != '__main__':
    logger.info("main.py is being imported by Gunicorn. Flask app is ready.")
    pass

else:
    logger.info("main.py is being run directly. Running bot with long polling locally.")
    async def run_local_bot():
        await bot_instance.application.run_polling(drop_pending_updates=True)

    async def main_local():
        await run_local_bot()

    asyncio.run(main_local())

import os
import logging
from flask import Flask, request, abort
import asyncio
import threading # استيراد threading لإدارة حلقة الأحداث بشكل أفضل

# استيراد مكونات البوت الخاصة بك
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes, # <--- تأكد من وجود هذا الاستيراد
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

        # تهيئة التطبيق عند بناء البوت في بيئة الويب هو أمر حساس.
        # سنجرب هذا النهج الذي يحاول تهيئة حلقة الأحداث في نفس الثريد.
        # إذا استمرت مشكلة 'Event loop is closed' (والتي ظهرت سابقا)،
        # قد نحتاج إلى حل أكثر تعقيدًا باستخدام run_webhook أو Threading.
        try:
            if not asyncio.get_event_loop().is_running():
                asyncio.run(self.application.initialize())
            else:
                # إذا كانت هناك حلقة أحداث بالفعل (كما في Gunicorn)، حاول تشغيلها كـ Task
                asyncio.create_task(self.application.initialize())
        except RuntimeError:
            # إذا لم تكن هناك حلقة أحداث عاملة، قم بإنشاء واحدة وتشغيل التهيئة
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.application.initialize())
            loop.close() # أغلق الحلقة بعد التهيئة إذا لم تكن ستستخدم


    def _setup_handlers(self):
        """Setup all command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        # أضف هنا باقي المعالجات (handlers) التي لديك في بوتك
        # self.application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, self.photo_message_handler))
        # self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message_handler))
        # self.application.add_handler(CallbackQueryHandler(self.callback_query_handler))

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


# إنشاء كائن البوت (instance)
bot_instance = TreasureHunterBot()

# ربط Flask بالـ Webhook الخاص بـ Telegram
@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.method == "POST":
        update_json = request.get_json()
        if not update_json:
            logger.warning("Received POST request without JSON data.")
            abort(400)

        logger.info(f"Received webhook update: {update_json.get('update_id')}")

        try:
            # لم نعد بحاجة إلى استدعاء initialize هنا بعد نقله إلى __init__
            update = Update.de_json(update_json, bot_instance.application.bot)
            await bot_instance.application.process_update(update)
            return 'ok'
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}", exc_info=True)
            abort(500)
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

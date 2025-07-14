import os
import logging
from flask import Flask, request, abort # أضفنا request و abort
import asyncio # لضمان عمل العمليات غير المتزامنة بشكل صحيح

# استيراد مكونات البوت الخاصة بك
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # <--- تأكد من وجود هذه هنا
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes, # <--- وتأكد من وجود هذه هنا
    CallbackQueryHandler
)

from config import Config # للتأكد من استيراد إعدادات التوكن والمفاتيح
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
        # Validate configuration (هذا سيضمن التحقق من وجود TELEGRAM_BOT_TOKEN و OPENAI_API_KEY)
        try:
            Config.validate()
            logger.info("Configuration validated successfully.")
        except ValueError as e:
            logger.critical(f"Critical configuration error: {e}")
            # يمكنك اختيار إنهاء التطبيق هنا إذا كانت المتغيرات الأساسية مفقودة
            # sys.exit(1) # هذه تحتاج استيراد sys

        # Initialize components
        self.ai_analyzer = AIAnalyzer(Config.OPENAI_API_KEY)
        self.treasure_guide = TreasureHunterGuide()
        self.rate_limiter = RateLimiter(Config.MAX_REQUESTS_PER_MINUTE)

        # Initialize database and leaderboard
        self.db_manager = DatabaseManager()
        self.leaderboard = LeaderboardManager(self.db_manager)

        # Initialize Telegram application
        # نستخدم Application.builder().updater(None).build() لـ Webhook
        # ثم نضبط update_queue يدوياً عند تلقي التحديثات
        self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

        # Setup handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup all command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        # أضف هنا باقي المعالجات (handlers) التي لديك في بوتك إذا كانت موجودة في كودك الأصلي
        # self.application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, self.photo_message_handler))
        # self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message_handler))
        # self.application.add_handler(CallbackQueryHandler(self.callback_query_handler))

    # يجب أن تكون هذه الدوال (أوامر البوت) داخل TreasureHunterBot
    # أضف هنا جميع دوال معالجة الأوامر والرسائل التي لديك
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
async def webhook(): # يجب أن تكون دالة async لمعالجة Update.de_json و put
    if request.method == "POST":
        update_json = request.get_json()
        if not update_json:
            logger.warning("Received POST request without JSON data.")
            abort(400) # Bad Request

        logger.info(f"Received webhook update: {update_json.get('update_id')}")

        try:
            # قم بمعالجة التحديث باستخدام application.process_update
            # أو إضافة التحديث إلى queue إذا كان application يعمل في حلقة حدث منفصلة
            # في هذا الإعداد، سنستخدم process_update مباشرة
            update = Update.de_json(update_json, bot_instance.application.bot)
            await bot_instance.application.process_update(update)
            return 'ok'
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}", exc_info=True)
            abort(500) # Internal Server Error
    return 'Method Not Allowed', 405

@app.route('/')
def home():
    logger.info("Home route accessed. Flask is responding.")
    return "✅ خدمة الويب (Flask) تعمل بنجاح."

# هذا الجزء ضروري لتشغيل تطبيق Flask بواسطة Gunicorn
# Gunicorn سيستدعي app من هذا الملف، لذلك لا نحتاج لـ app.run هنا
if __name__ != '__main__':
    logger.info("main.py is being imported by Gunicorn. Flask app is ready.")
    # لا نقوم بتعيين الـ webhook هنا بشكل تلقائي مع كل بدء تشغيل
    # لأن الطريقة الأكثر موثوقية هي تعيينه يدوياً مرة واحدة أو عبر سكريبت نشر منفصل
    pass

else:
    # هذا الجزء للتشغيل المحلي المباشر (ليس ضرورياً لـ Render)
    # هنا سنستخدم long polling للتشغيل المحلي السهل
    logger.info("main.py is being run directly. Running bot with long polling locally.")
    async def run_local_bot():
        # لتشغيل البوت محليًا باستخدام long polling
        # drop_pending_updates=True يتجاهل أي تحديثات لم تتم معالجتها
        await bot_instance.application.run_polling(drop_pending_updates=True)

    async def main_local():
        # تشغيل البوت بـ long polling محلياً
        await run_local_bot()

    # بدء تشغيل التطبيق غير المتزامن
    # يجب أن تتأكد أن هذا هو المكان الوحيد الذي يتم فيه تشغيل asyncio.run()
    asyncio.run(main_local())

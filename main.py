import os
import logging
from flask import Flask, request, abort # أضفنا request و abort
import asyncio # لضمان عمل العمليات غير المتزامنة بشكل صحيح

# استيراد مكونات البوت الخاصة بك
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
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
            # sys.exit(1)

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
        # أضف هنا باقي المعالجات (handlers) التي لديك في بوتك
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
# ونحتاج فقط لتعيين الـ webhook عند بدء التطبيق
if __name__ != '__main__':
    logger.info("main.py is being imported by Gunicorn. Flask app is ready.")
    # عند بدء Gunicorn، قم بتعيين الويب هوك مرة واحدة فقط
    # تأكد من أن هذا يتم مرة واحدة فقط عند بدء تشغيل الخادم
    async def set_webhook_on_startup():
        webhook_url = os.environ.get("RENDER_EXTERNAL_HOSTNAME") # Render يوفر هذا المتغير
        if webhook_url:
            full_webhook_url = f"https://{webhook_url}/webhook" # /webhook هو المسار الذي حددناه
            logger.info(f"Attempting to set webhook to: {full_webhook_url}")
            try:
                await bot_instance.application.bot.set_webhook(url=full_webhook_url)
                logger.info("Webhook set successfully.")
                # يمكنك إضافة استدعاء لـ getWebhookInfo هنا للتحقق الفوري
                info = await bot_instance.application.bot.get_webhook_info()
                logger.info(f"Webhook info after setting: {info.to_dict()}")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}", exc_info=True)
        else:
            logger.warning("RENDER_EXTERNAL_HOSTNAME environment variable not found. Webhook may not be set.")

    # قم بتشغيل دالة تعيين الويب هوك عند بدء تشغيل Gunicorn
    # هذا يتطلب تشغيل حدث asyncio.run أو loop.run_until_complete
    # ولكن الطريقة الأبسط هي جعل Gunicorn يستدعي Flask app، والفلاك يتولى الويب هوك
    # سنستخدم طريقة بسيطة لضمان تشغيل الـ webhook عند بدء الخدمة.
    # يمكننا إضافة ذلك في دالة start_command أو في __init__ للـ TreasureHunterBot
    # ولكن لضمان أنها تعمل عند بدء Gunicorn، سنفعلها كـ background task
    # Note: This is a simplified approach. For robust webhook management in production
    # you might want to use a separate script or a dedicated webhook setup endpoint.

    # لتشغيل الكود غير المتزامن عند بدء التشغيل، نحتاج إلى Event Loop.
    # بما أن gunicorn يشغل Flask، يمكننا استخدام thread pool لتشغيل الـ async code
    # أو ببساطة ترك تعيين الـ webhook يدوياً أولاً.
    # الطريقة الأكثر شيوعاً هي تعيين الـ webhook مرة واحدة فقط عند النشر يدوياً أو عبر GitHub Action.
    # ولكن إذا كنت تريده أن يُعيّن في كل مرة يبدأ فيها الخادم:
    # سيتم تشغيل هذا الكود عندما يتم استيراد main.py بواسطة gunicorn
    # تأكد من أنك تستخدم python-telegram-bot v20.x+ التي تدعم async/await

    # لا يمكن استدعاء asyncio.run() مباشرة هنا لأن gunicorn يدير الـ event loop الخاص به
    # الأفضل هو تعيين الويب هوك يدوياً أو عند أول طلب للروت /
    # أو يمكنك استخدام مكتبة مثل aiohttp مع Flask إذا كنت تريد تعيين ويب هوك async عند البدء
    # للطريقة المبسطة: تأكد من أن الويب هوك يتم تعيينه يدوياً أو عن طريق تشغيل سكريبت منفصل مرة واحدة.
    pass # لا تفعل شيئاً هنا، gunicorn سيتولى تشغيل Flask

else:
    # هذا الجزء للتشغيل المحلي المباشر (ليس ضرورياً لـ Render)
    # هنا سنستخدم long polling للتشغيل المحلي السهل
    logger.info("main.py is being run directly. Running bot with long polling locally.")
    async def run_local_bot():
        # لتشغيل البوت محليًا باستخدام long polling
        await bot_instance.application.run_polling(drop_pending_updates=True)

    # تشغيل Flask app (الذي سيستمع على المسار /)
    # وتشغيل البوت في نفس الوقت (إذا لم تكن تستخدم webhooks محلياً)
    # يمكننا تشغيل الاثنين معاً باستخدام asyncio.gather
    async def main_local():
        # تشغيل Flask في Event Loop الخاص به (ليس مثالياً، لكن لغرض التوضيح)
        # أو يمكن تشغيل Flask بشكل منفصل وترك البوت يعمل بـ long polling
        # للحصول على setup كامل مع webhook محلياً، ستحتاج إلى ngrok أو ما شابه
        # ولكن بما أن الهدف هو Render (webhook)، فإن هذا الجزء هو فقط للتجربة المحلية
        await run_local_bot() # قم بتشغيل البوت بـ long polling محلياً

    # بدء تشغيل التطبيق غير المتزامن
    # يجب أن تتأكد أن هذا هو المكان الوحيد الذي يتم فيه تشغيل asyncio.run()
    # لتشغيل flask مع gunicorn لا تحتاج الى asyncio.run في هذا السياق
    asyncio.run(main_local())

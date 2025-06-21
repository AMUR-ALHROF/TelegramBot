import os
import logging
from flask import Flask
from threading import Thread
import asyncio # <=== استيراد asyncio الجديد والمهم
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai
from PIL import Image
import requests
from io import BytesIO
import base64

# إعداد السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة تطبيق Flask
app = Flask(__name__) # هذا هو متغير "app" الذي سيبحث عنه Gunicorn

class TreasureAnalyzerBot:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        if not self.telegram_token:
            logger.error("TELEGRAM_BOT_TOKEN مفقود في متغيرات البيئة.")
            raise ValueError("TELEGRAM_BOT_TOKEN مفقود")
        if not self.openai_api_key:
            logger.error("OPENAI_API_KEY مفقود في متغيرات البيئة.")
            raise ValueError("OPENAI_API_KEY مفقود")

        openai.api_key = self.openai_api_key
        # قم بتهيئة ApplicationBuilder في دالة __init__
        # ولكن بناء الـ Application نفسه سيتم لاحقًا لضمان عمله في نفس ثريد Polling
        self.application_builder = Application.builder().token(self.telegram_token)
        self.bot_app = None # سيتم تهيئته لاحقاً في الثريد الصحيح

        logger.info("TreasureAnalyzerBot instance initialized (tokens loaded).") # سجل جديد

    # دالة لتهيئة Handlers (المعالجات)
    def setup_handlers(self):
        if self.bot_app:
            self.bot_app.add_handler(CommandHandler("start", self.start))
            self.bot_app.add_handler(CommandHandler("help", self.help))
            self.bot_app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
            self.bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
            logger.info("Telegram bot handlers set up.") # سجل جديد
        else:
            logger.error("bot_app is not initialized when trying to set up handlers.")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Received /start command from user {update.message.from_user.id}") # سجل جديد
        await update.message.reply_text("👋 أهلاً بك في بوت تحليل الكنوز والنقوش القديمة باستخدام الذكاء الاصطناعي.")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Received /help command from user {update.message.from_user.id}") # سجل جديد
        await update.message.reply_text(
            "/start - بدء\n"
            "/help - تعليمات\n"
            "📸 أرسل صورة لتحليلها\n"
            "❓ أرسل سؤالًا"
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            logger.info(f"Received text message from user {update.message.from_user.id}") # سجل جديد
            await update.message.reply_text("جاري التفكير...")
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "أجب على الأسئلة التاريخية باللغة العربية."},
                    {"role": "user", "content": update.message.text}
                ]
            )
            answer = response.choices[0].message.content
            await update.message.reply_text(answer)
        except Exception as e:
            logger.error(f"خطأ في معالجة النص: {e}", exc_info=True) # سجل جديد مع معلومات الخطأ الكاملة
            await update.message.reply_text("حدث خطأ أثناء الاتصال بـ GPT. يرجى المحاولة مرة أخرى.")

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            logger.info(f"Received image from user {update.message.from_user.id}") # سجل جديد
            await update.message.reply_text("جاري تحليل الصورة...")
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_base64 = base64.b64encode(photo_bytes).decode('utf-8')

            response = openai.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "حلل هذه الصورة بحثًا عن دلائل آثار، كن دقيقاً ومفصلاً."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ]
            )
            result = response.choices[0].message.content
            await update.message.reply_text(result)
        except Exception as e:
            logger.error(f"خطأ في معالجة الصورة: {e}", exc_info=True) # سجل جديد مع معلومات الخطأ الكاملة
            await update.message.reply_text("تعذر تحليل الصورة. يرجى التأكد من أن الصورة واضحة أو المحاولة لاحقاً.")

# إنشاء مثيل البوت
bot_instance = TreasureAnalyzerBot()

# نقطة الدخول لتطبيق Flask
@app.route('/')
def home():
    logger.info("Home route accessed. Flask is responding.") # سجل جديد
    return "✅ البوت يعمل على Render Web Service! (Telegram polling is active)"

# دالة لتهيئة وتشغيل البوت في ثريد منفصل مع حلقة حدث خاصة بها
def start_telegram_bot_polling_in_thread():
    logger.info("Attempting to start Telegram bot polling in a new thread with a dedicated asyncio event loop.") # سجل جديد

    # إنشاء وتهيئة حلقة حدث جديدة للثريد الحالي
    try:
        loop = asyncio.get_event_loop() # حاول الحصول على حلقة حدث موجودة
    except RuntimeError: # إذا لم تكن موجودة، قم بإنشاء واحدة
        loop = asyncio.new_event_loop()
    
    asyncio.set_event_loop(loop) # تعيين حلقة الحدث للثريد الحالي

    # بناء التطبيق وإعداد المعالجات هنا، لضمان أنها مرتبطة بحلقة الحدث الصحيحة
    try:
        logger.info("Building Telegram Application within polling thread.") # سجل جديد
        # أعد بناء التطبيق هنا لضمان عمله ضمن حلقة الحدث الحالية
        bot_instance.bot_app = bot_instance.application_builder.build()
        bot_instance.setup_handlers() # إعداد المعالجات بعد بناء bot_app
        
        logger.info("Starting Telegram bot polling...") # سجل جديد
        loop.run_until_complete(bot_instance.bot_app.run_polling())
        logger.info("Telegram bot polling finished/stopped.") # سجل جديد
    except Exception as e:
        logger.error(f"Critical Error in Telegram bot polling thread: {e}", exc_info=True) # سجل خطأ حرج
    finally:
        loop.close() # إغلاق حلقة الحدث عند الانتهاء أو حدوث خطأ

# ***الجزء المعدل الرئيسي في النهاية***
# سنقوم بتشغيل البوت في ثريد منفصل فوراً عند بدء تشغيل السكريبت بواسطة Gunicorn.
if __name__ != '__main__':
    logger.info("main.py is being imported by Gunicorn. Initializing and starting bot polling thread.") # سجل جديد
    # تشغيل الثريد الذي سيقوم بتهيئة حلقة حدث asyncio وتشغيل البوت
    bot_thread = Thread(target=start_telegram_bot_polling_in_thread, daemon=True) # daemon=True يسمح للتطبيق بالخروج حتى لو كان الثريد يعمل
    bot_thread.start()
    logger.info("Telegram bot polling thread started.") # سجل جديد
else:
    # هذا الجزء يعمل عند تشغيل main.py مباشرة (للتطوير المحلي مثلاً)
    logger.info("main.py is being run directly. Starting bot polling on main thread (for local testing).")
    try:
        # هنا سنقوم بتهيئة bot_app وإعداد Handlers قبل run_polling
        bot_instance.bot_app = bot_instance.application_builder.build()
        bot_instance.setup_handlers()
        bot_instance.bot_app.run_polling()
    except Exception as e:
        logger.error(f"Error when running bot locally: {e}", exc_info=True)


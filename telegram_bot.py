import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai
from PIL import Image # للتأكد من وجودها إذا كنت تستخدم معالجة الصور
import requests # للتأكد من وجودها إذا كنت تستخدم معالجة الصور
from io import BytesIO # للتأكد من وجودها إذا كنت تستخدم معالجة الصور
import base64

# إعداد السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TreasureAnalyzerBot:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        if not self.telegram_token:
            logger.critical("TELEGRAM_BOT_TOKEN مفقود في متغيرات البيئة. لا يمكن بدء البوت.")
            raise ValueError("TELEGRAM_BOT_TOKEN مفقود")
        if not self.openai_api_key:
            logger.critical("OPENAI_API_KEY مفقود في متغيرات البيئة. لا يمكن الاتصال بـ OpenAI.")
            raise ValueError("OPENAI_API_KEY مفقود")

        openai.api_key = self.openai_api_key
        self.application_builder = Application.builder().token(self.telegram_token)
        self.bot_app = None # سيتم تهيئته لاحقاً

        logger.info("TreasureAnalyzerBot instance initialized (tokens loaded).")

    def setup_handlers(self):
        if self.bot_app:
            self.bot_app.add_handler(CommandHandler("start", self.start))
            self.bot_app.add_handler(CommandHandler("help", self.help))
            self.bot_app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
            self.bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
            logger.info("Telegram bot handlers set up.")
        else:
            logger.error("bot_app is not initialized when trying to set up handlers.")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Received /start command from user {update.message.from_user.id}")
        await update.message.reply_text("👋 أهلاً بك في بوت تحليل الكنوز والنقوش القديمة باستخدام الذكاء الاصطناعي.")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Received /help command from user {update.message.from_user.id}")
        await update.message.reply_text(
            "/start - بدء\n"
            "/help - تعليمات\n"
            "📸 أرسل صورة لتحليلها\n"
            "❓ أرسل سؤالًا"
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            logger.info(f"Received text message from user {update.message.from_user.id}")
            await update.message.reply_text("جاري التفكير...")
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo", # ****** تم التغيير هنا من gpt-4 إلى gpt-3.5-turbo ******
                messages=[
                    {"role": "system", "content": "أجب على الأسئلة التاريخية باللغة العربية. كن دقيقاً ومفصلاً."},
                    {"role": "user", "content": update.message.text}
                ]
            )
            answer = response.choices[0].message.content
            await update.message.reply_text(answer)
        except openai.APIError as e:
            logger.error(f"خطأ API من OpenAI في معالجة النص: {e.type} - {e.message}", exc_info=True)
            await update.message.reply_text(f"حدث خطأ في الاتصال بـ OpenAI: {e.message}. يرجى التحقق من مفتاح API والرصيد.")
        except Exception as e:
            logger.error(f"خطأ غير متوقع في معالجة النص: {e}", exc_info=True)
            await update.message.reply_text("حدث خطأ أثناء معالجة طلبك النصي. يرجى المحاولة مرة أخرى.")

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            logger.info(f"Received image from user {update.message.from_user.id}")
            await update.message.reply_text("جاري تحليل الصورة...")
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            image_base64 = base64.b64encode(photo_bytes).decode('utf-8')

            response = openai.chat.completions.create(
                model="gpt-4-vision-preview", # ****** هذا النموذج يتطلب وصولاً خاصاً / رصيداً ******
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "حلل هذه الصورة بحثًا عن دلائل آثار، كن دقيقاً ومفصلاً. أجب باللغة العربية."},
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
        except openai.APIError as e:
            logger.error(f"خطأ API من OpenAI في معالجة الصورة: {e.type} - {e.message}", exc_info=True)
            await update.message.reply_text(f"حدث خطأ في الاتصال بـ OpenAI لتحليل الصورة: {e.message}. يرجى التحقق من مفتاح API والرصيد ووصولك لنموذج Vision.")
        except Exception as e:
            logger.error(f"خطأ غير متوقع في معالجة الصورة: {e}", exc_info=True)
            await update.message.reply_text("تعذر تحليل الصورة. يرجى التأكد من أن الصورة واضحة أو المحاولة لاحقاً.")

# هذا الجزء سيشغل البوت فقط عند تشغيل هذا الملف
if __name__ == '__main__':
    logger.info("telegram_bot.py is being run directly. Starting bot polling.")
    try:
        bot_instance = TreasureAnalyzerBot()
        bot_instance.bot_app = bot_instance.application_builder.build()
        bot_instance.setup_handlers()
        # استخدام run_polling مع poll_interval و timeout لمنع التعليق
        bot_instance.bot_app.run_polling(poll_interval=1.0, timeout=30)
        logger.info("Telegram bot polling finished/stopped.")
    except Exception as e:
        logger.critical(f"FATAL ERROR: Could not start Telegram bot polling: {e}", exc_info=True)


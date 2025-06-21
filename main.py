import os
import logging
from flask import Flask
from threading import Thread
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
        self.bot_app = Application.builder().token(self.telegram_token).build()

        self.bot_app.add_handler(CommandHandler("start", self.start))
        self.bot_app.add_handler(CommandHandler("help", self.help))
        self.bot_app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("👋 أهلاً بك في بوت تحليل الكنوز والنقوش القديمة باستخدام الذكاء الاصطناعي.")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "/start - بدء\n"
            "/help - تعليمات\n"
            "📸 أرسل صورة لتحليلها\n"
            "❓ أرسل سؤالًا"
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
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
            logger.error(f"خطأ في معالجة النص: {e}")
            await update.message.reply_text("حدث خطأ أثناء الاتصال بـ GPT. يرجى المحاولة مرة أخرى.")

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
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
            logger.error(f"خطأ في معالجة الصورة: {e}")
            await update.message.reply_text("تعذر تحليل الصورة. يرجى التأكد من أن الصورة واضحة أو المحاولة لاحقاً.")

# إنشاء مثيل البوت
bot_instance = TreasureAnalyzerBot()

# نقطة الدخول لتطبيق Flask
@app.route('/')
def home():
    return "✅ البوت يعمل على Render Web Service! (Telegram polling is active)"

# دالة لتهيئة وتشغيل البوت
def start_telegram_bot_polling():
    logger.info("✅ بدأ تشغيل بوت التليجرام (polling)...")
    bot_instance.bot_app.run_polling()

# ***الجزء المعدل الرئيسي هنا***
# سنقوم بتشغيل البوت في ثريد منفصل فوراً عند بدء تشغيل السكريبت.
# هذا يضمن بدء البوت بغض النظر عن أول طلب لـ Flask.
# تأكد أن هذا الجزء يأتي بعد تعريف 'bot_instance'
if __name__ != '__main__': # هذا الشرط يعني "إذا لم يكن السكريبت يُشغل مباشرة (مثل python main.py)"
    # ولكن يتم استيراده بواسطة Gunicorn.
    # في بيئة Gunicorn، يتم استيراد ملفك، وليس تشغيله مباشرة كـ __main__.
    # لذلك، هذا هو المكان المناسب لبدء الثريد الخاص بالبوت.
    logger.info("يتم استيراد main.py بواسطة Gunicorn. بدء ثريد البوت.")
    # التأكد من أن البوت لا يتم تشغيله إلا مرة واحدة لكل عملية Gunicorn Worker
    # (Gunicorn قد يشغل عدة عمليات 'worker' لتطبيقك)
    # لا حاجة لـ 'daemon=True' إذا كان Gunicorn سيهتم بإغلاق الثريدات.
    Thread(target=start_telegram_bot_polling).start()

# ملاحظة: لا تستخدم app.run() هنا، Gunicorn سيتولى تشغيل تطبيق Flask.

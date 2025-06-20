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

# Flask لتشغيل Web Service
app = Flask(__name__)

class TreasureAnalyzerBot:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN مفقود")
        if not self.openai_api_key:
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
            logger.error(e)
            await update.message.reply_text("حدث خطأ أثناء الاتصال بـ GPT.")

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = BytesIO(photo_bytes)

        try:
            response = openai.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "حلل هذه الصورة بحثًا عن دلائل آثار."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/jpeg;base64," + base64.b64encode(image.getvalue()).decode()
                                }
                            }
                        ]
                    }
                ]
            )
            result = response.choices[0].message.content
            await update.message.reply_text(result)
        except Exception as e:
            logger.error(e)
            await update.message.reply_text("تعذر تحليل الصورة.")

    def run(self):
        logger.info("✅ البوت يعمل الآن...")

        def start_bot():
            self.bot_app.run_polling()

        Thread(target=start_bot).start()

bot = TreasureAnalyzerBot()
bot.run()

@app.route('/')
def home():
    return "✅ البوت يعمل على Render Web Service!"
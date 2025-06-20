import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai
from PIL import Image
import requests
from io import BytesIO

# إعداد سجل الأحداث
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TreasureAnalyzerBot:
    def __init__(self):
        # جلب المفاتيح من البيئة
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        if not self.telegram_token:
            raise ValueError("يجب ضبط متغير البيئة TELEGRAM_BOT_TOKEN")
        if not self.openai_api_key:
            raise ValueError("يجب ضبط متغير البيئة OPENAI_API_KEY")

        openai.api_key = self.openai_api_key
        self.app = Application.builder().token(self.telegram_token).build()

        # تعريف الأوامر
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("👋 أهلاً بك في بوت تحليل الكنوز والنقوش القديمة باستخدام الذكاء الاصطناعي. أرسل صورة أو سؤال!")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "/start - بدء استخدام البوت\n"
            "/help - التعليمات\n"
            "📸 أرسل صورة لتحليلها\n"
            "❓ أرسل سؤالًا عن التاريخ أو الآثار"
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        question = update.message.text
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "أجب على الأسئلة المتعلقة بالكنوز والنقوش القديمة باللغة العربية."},
                    {"role": "user", "content": question}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            answer = response.choices[0].message.content
            await update.message.reply_text(answer)
        except Exception as e:
            logger.error(e)
            await update.message.reply_text("حدث خطأ أثناء محاولة الاتصال بـ GPT. الرجاء المحاولة لاحقًا.")

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = BytesIO(photo_bytes)

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "حلل هذه الصورة بحثاً عن دلائل دفائن أو نقوش قديمة"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/jpeg;base64," + base64.b64encode(image.getvalue()).decode()
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            result = response.choices[0].message.content
            await update.message.reply_text(result)
        except Exception as e:
            logger.error(e)
            await update.message.reply_text("حدث خطأ أثناء تحليل الصورة. الرجاء التأكد من جودة الصورة أو المحاولة لاحقًا.")

    def run(self):
        logger.info("✅ البوت يعمل الآن...")
        self.app.run_polling()


# نقطة البداية
if __name__ == '__main__':
    bot = TreasureAnalyzerBot()
    bot.run()
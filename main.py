import logging
import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv
from openai import OpenAI
import requests
from io import BytesIO
from PIL import Image
import base64

from database import DatabaseManager

# تحميل متغيرات البيئة من .env
load_dotenv()

# تسجيل الأخطاء والمعلومات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# مفاتيح API
openai_api_key = os.getenv("OPENAI_API_KEY")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "8080"))

if not openai_api_key or not telegram_token or not DATABASE_URL or not WEBHOOK_URL:
    logger.critical("Environment variables missing. Please check .env or Render settings.")
    exit(1)

# إعداد OpenAI
openai_client = OpenAI(api_key=openai_api_key)

# قاعدة البيانات
db_manager = DatabaseManager(DATABASE_URL)

# رسالة الترحيب
WELCOME_MESSAGE = (
    "أهلاً بك أمير الحروف 👑!\n"
    "أنا هنا لأساعدك في رحلة البحث عن الكنوز. 🔎💰\n"
    "أرسل لي صورة للنقش الذي وجدته وسأقوم بتحليله لك.\n"
    "ويمكنك أيضًا أن تسألني عن أي شيء يخص الحضارات والآثار القديمة!"
)

MAX_FREE_REQUESTS = 5

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db_manager.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(WELCOME_MESSAGE)
    logger.info(f"User {user.id} started the bot.")

def check_request_limit(user_id: int) -> tuple[bool, int]:
    user = db_manager.get_user_by_telegram_id(user_id)
    if not user:
        return False, 0
    if user.last_request_date.date() != datetime.utcnow().date():
        db_manager.update_user_requests(user_id, 0, datetime.utcnow())
        return True, MAX_FREE_REQUESTS
    if user.requests_count < MAX_FREE_REQUESTS:
        return True, MAX_FREE_REQUESTS - user.requests_count
    return False, 0

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_allowed, remaining = check_request_limit(user_id)
    if not is_allowed:
        await update.message.reply_text(f"عذرًا، لقد استنفدت ({MAX_FREE_REQUESTS}) طلبًا اليوم. أعد المحاولة غدًا.")
        return
    db_manager.increment_user_requests(user_id)
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)
    base64_image = base64.b64encode(photo_bytes.read()).decode("utf-8")
    await update.message.reply_text("جارٍ تحليل الصورة...")
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "ما هذا النقش؟ صفه بالتفصيل... وأجب بصيغة JSON فقط، مع الحقول (وصف_النقش، الحضارة، المعنى، هل_يوجد_كنوز، نصائح_إضافية)."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ],
                }
            ],
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```json"):
            raw = raw[len("```json"):].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        data = json.loads(raw)
        reply = (
            f"✨ **تحليل النقش:** ✨\n\n"
            f"📜 **وصف:** {data.get('وصف_النقش', 'لا يوجد')}\n"
            f"🏛️ **الحضارة:** {data.get('الحضارة', 'غير معروفة')}\n"
            f"🔍 **المعنى:** {data.get('المعنى', 'غير واضح')}\n"
            f"💰 **هل يوجد كنوز؟** {data.get('هل_يوجد_كنوز', 'غير مؤكد')}\n"
            f"💡 **نصائح:** {data.get('نصائح_إضافية', 'لا شيء')}"
        )
        await update.message.reply_text(reply, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text("حدث خطأ أثناء تحليل الصورة. جرب مجددًا لاحقًا.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    is_allowed, remaining = check_request_limit(user_id)
    if not is_allowed:
        await update.message.reply_text(f"عذرًا، لقد استنفدت ({MAX_FREE_REQUESTS}) طلبًا اليوم. أعد المحاولة غدًا.")
        return
    db_manager.increment_user_requests(user_id)
    await update.message.reply_text("جارٍ البحث عن إجابة...")
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "أنت خبير في الحضارات والآثار القديمة."},
                {"role": "user", "content": text}
            ],
            max_tokens=500,
        )
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"Text error: {e}")
        await update.message.reply_text("حدث خطأ أثناء المعالجة. حاول لاحقًا.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Error: {context.error}")
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.")

def main() -> None:
    app = Application.builder().token(telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info(f"✅ Running Webhook on port {PORT}, URL: {WEBHOOK_URL}/{telegram_token}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=telegram_token,
        webhook_url=f"{WEBHOOK_URL}/{telegram_token}"
    )

if __name__ == "__main__":
    main()
Import logging
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
from openai import OpenAI
from io import BytesIO
import base64

from database import DatabaseManager

# إعدادات التسجيل (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# تحميل متغيرات البيئة من نظام التشغيل مباشرة (Render لا يستخدم .env)
openai_api_key = os.getenv("OPENAI_API_KEY")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", "8080"))

# فحص المتغيرات المطلوبة
missing_vars = []
if not openai_api_key:
    missing_vars.append("OPENAI_API_KEY")
if not telegram_token:
    missing_vars.append("TELEGRAM_BOT_TOKEN")
if not DATABASE_URL:
    missing_vars.append("DATABASE_URL")
if not WEBHOOK_URL:
    missing_vars.append("WEBHOOK_URL")

if missing_vars:
    logger.critical(f"Missing environment variables: {', '.join(missing_vars)}. Please set them in Render's dashboard.")
    exit(1)

# تهيئة OpenAI و قاعدة البيانات
openai_client = OpenAI(api_key=openai_api_key)
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
    # 🔴🔴🔴 هذا هو السطر الذي تم تعديله 🔴🔴🔴
    db_manager.get_or_create_user(user.id, user.username, user.first_name)
    await update.message.reply_text(WELCOME_MESSAGE)

def check_request_limit(user_id: int) -> tuple[bool, int]:
    user_data = db_manager.get_user_by_telegram_id(user_id) # هذا السطر يسبب مشكلة. دالة get_user_by_telegram_id غير موجودة. يجب استخدام get_user
    if not user_data:
        return False, 0

    last_date = user_data.last_request_date
    count = user_data.requests_count

    if last_date.date() != datetime.utcnow().date():
        db_manager.update_user_requests(user_id, 0, datetime.utcnow()) # هذا السطر يسبب مشكلة. دالة update_user_requests غير موجودة
        return True, MAX_FREE_REQUESTS
    return (count < MAX_FREE_REQUESTS), (MAX_FREE_REQUESTS - count)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_allowed, remaining = check_request_limit(user_id)

    if not is_allowed:
        await update.message.reply_text("لقد استنفدت طلباتك المجانية لهذا اليوم. حاول غدًا.")
        return

    db_manager.increment_user_requests(user_id) # هذا السطر يسبب مشكلة. دالة increment_user_requests غير موجودة.
    await update.message.reply_text("تلقيت الصورة، جارٍ التحليل...")

    photo = await update.message.photo[-1].get_file()
    bio = BytesIO()
    await photo.download_to_memory(bio)
    bio.seek(0)
    base64_image = base64.b64encode(bio.read()).decode("utf-8")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "ما هذا النقش؟ صفه بالتفصيل، وما هي الحضارة التي ينتمي إليها؟ وما هو معناه؟ وهل يوجد كنوز حوله؟ أجب بصيغة JSON فقط، مع حقول (وصف_النقش، الحضارة، المعنى، هل_يوجد_كنوز، نصائح_إضافية)."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ],
                }
            ],
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[len("```json"):].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        data = json.loads(content)
        msg = (
            f"✨ **تحليل النقش:** ✨\n\n"
            f"📜 **وصف النقش:** {data.get('وصف_النقش', 'غير متوفر')}\n\n"
            f"🏛️ **الحضارة:** {data.get('الحضارة', 'غير معروفة')}\n\n"
            f"🔍 **المعنى:** {data.get('المعنى', 'لا يمكن تحديده')}\n\n"
            f"💰 **هل يوجد كنوز:** {data.get('هل_يوجد_كنوز', 'غير مؤكد')}\n\n"
            f"💡 **نصائح إضافية:** {data.get('نصائح_إضافية', 'لا شيء')}"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"AI error: {e}")
        await update.message.reply_text("حدث خطأ أثناء تحليل الصورة، يرجى المحاولة مجددًا.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_allowed, remaining = check_request_limit(user_id)

    if not is_allowed:
        await update.message.reply_text("لقد استنفدت طلباتك المجانية لهذا اليوم. حاول غدًا.")
        return

    db_manager.increment_user_requests(user_id) # هذا السطر يسبب مشكلة. دالة increment_user_requests غير موجودة.
    await update.message.reply_text("جارٍ معالجة سؤالك...")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "أنت خبير في الحضارات القديمة والآثار."},
                {"role": "user", "content": update.message.text}
            ],
            max_tokens=500,
        )
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"Text AI error: {e}")
        await update.message.reply_text("حدث خطأ أثناء الإجابة، حاول لاحقًا.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error: {context.error}")
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("حدث خطأ غير متوقع. حاول لاحقًا.")

def main() -> None:
    application = Application.builder().token(telegram_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)

    logger.info(f"Running bot with webhook at {WEBHOOK_URL}/{telegram_token} on port {PORT}")
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=telegram_token,
        webhook_url=f"{WEBHOOK_URL}/{telegram_token}"
    )

if __name__ == "__main__":
    main()

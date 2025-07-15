import logging
import os
import json
from datetime import datetime, timedelta
from telegram import Update, InputMediaPhoto
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

from database import DatabaseManager  # تأكد من وجود ملف database.py

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# إعدادات التسجيل (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# تهيئة OpenAI API
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.critical("OPENAI_API_KEY environment variable is not set. Exiting.")
    exit(1) # إنهاء التطبيق إذا لم يكن المفتاح موجوداً
openai_client = OpenAI(api_key=openai_api_key)

# تهيئة مدير قاعدة البيانات
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.critical("DATABASE_URL environment variable is not set. Exiting.")
    exit(1) # إنهاء التطبيق إذا لم يكن الرابط موجوداً
# DEBUG: لطباعة رابط قاعدة البيانات للتأكد من أنه صحيح
logger.info(f"DEBUG: Attempting to connect to DB: {DATABASE_URL.split('@')[-1]}") # لا تطبع كلمة المرور كاملة

db_manager = DatabaseManager(DATABASE_URL)

# رسالة الترحيب الأولى للمستخدمين الجدد
WELCOME_MESSAGE = (
    "أهلاً بك أمير الحروف 👑!\n"
    "أنا هنا لأساعدك في رحلة البحث عن الكنوز. 🔎💰\n"
    "أرسل لي صورة للنقش الذي وجدته وسأقوم بتحليله لك.\n"
    "ويمكنك أيضًا أن تسألني عن أي شيء يخص الحضارات والآثار القديمة!"
)

# الحد الأقصى لعدد طلبات المستخدم المجانية
MAX_FREE_REQUESTS = 5

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name if update.effective_user.last_name else None

    # استخدام get_or_create_user لضمان وجود المستخدم
    user_data = db_manager.get_or_create_user(user_id, username, first_name, last_name)

    await update.message.reply_text(WELCOME_MESSAGE)
    logger.info(f"User {user_id} accessed: (newly created or existing)")

# دالة للتحقق من عدد الطلبات المجانية المتبقية
def check_request_limit(user_id: int) -> tuple[bool, int]:
    # استخدام get_user_by_telegram_id لأننا نتوقع أن المستخدم موجود بالفعل
    user_data = db_manager.get_user_by_telegram_id(user_id)
    if not user_data:
        logger.error(f"User {user_id} not found in database during request limit check.")
        # يمكن هنا توجيه المستخدم إلى /start إذا لم يتم العثور عليه
        return False, 0

    last_request_date = user_data.last_request_date
    requests_count = user_data.requests_count

    # إذا كان اليوم مختلفًا عن آخر طلب، أعد تعيين العدد
    # استخدام datetime.utcnow() للحصول على الوقت العالمي المنسق (UTC)
    # ليتوافق مع طريقة تخزين التاريخ في قاعدة البيانات (func.now())
    if last_request_date.date() != datetime.utcnow().date():
        requests_count = 0
        db_manager.update_user_requests(user_id, requests_count, datetime.utcnow())
        logger.info(f"User {user_id} daily request count reset.")

    if requests_count < MAX_FREE_REQUESTS:
        return True, MAX_FREE_REQUESTS - requests_count
    else:
        return False, 0


# دالة للتعامل مع الصور
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_allowed, remaining_requests = check_request_limit(user_id)

    if not is_allowed:
        await update.message.reply_text(
            f"عذرًا، لقد استنفدت عدد الطلبات المجانية ({MAX_FREE_REQUESTS}) لهذا اليوم. "
            "يرجى المحاولة مرة أخرى غدًا."
        )
        return

    # زيادة عدد الطلبات
    db_manager.increment_user_requests(user_id)

    logger.info(f"Received photo from user {user_id}. Remaining free requests: {remaining_requests - 1}")

    await update.message.reply_text("تلقيت الصورة، جارٍ تحليل النقش...")

    # الحصول على أكبر صورة جودة
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0) # ارجع للمبتدأ قبل القراءة

    # تحويل الصورة إلى Base64
    base64_image = base64.b64encode(photo_bytes.read()).decode("utf-8")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o", # أو gpt-4-turbo-2024-04-09
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "ما هذا النقش؟ صفه بالتفصيل، وما هي الحضارة التي ينتمي إليها؟ وما هو معناه؟ وهل يوجد كنوز حوله؟ أجبني بالتفصيل الشديد، مع ذكر أي تفاصيل مهمة. أجب بصيغة JSON فقط، مع حقول (وصف_النقش، الحضارة، المعنى، هل_يوجد_كنوز، نصائح_إضافية)."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ],
                }
            ],
            max_tokens=1000,
        )

        # محاولة تحليل استجابة JSON
        try:
            json_response_str = response.choices[0].message.content
            # أحيانًا يضيف GPT محتوى قبل أو بعد JSON، لذا نحاول استخراج JSON
            json_response_str = json_response_str.strip()
            if json_response_str.startswith("```json"):
                json_response_str = json_response_str[len("```json"):].strip()
            if json_response_str.endswith("```"):
                json_response_str = json_response_str[:-len("```")].strip()

            parsed_response = json.loads(json_response_str)

            # بناء رسالة الرد من حقول JSON
            reply_text = (
                f"✨ **تحليل النقش:** ✨\n\n"
                f"📜 **وصف النقش:** {parsed_response.get('وصف_النقش', 'لا يوجد وصف.')}\n\n"
                f"🏛️ **الحضارة:** {parsed_response.get('الحضارة', 'غير معروفة.')}\n\n"
                f"🔍 **المعنى:** {parsed_response.get('المعنى', 'لا يمكن تحديد المعنى.')}\n\n"
                f"💰 **هل يوجد كنوز:** {parsed_response.get('هل_يوجد_كنوز', 'غير مؤكد.')}\n\n"
                f"💡 **نصائح إضافية:** {parsed_response.get('نصائح_إضافية', 'لا توجد نصائح إضافية.')}"
            )
            await update.message.reply_text(reply_text, parse_mode='Markdown')

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from OpenAI response: {e}. Raw response: {response.choices[0].message.content}")
            await update.message.reply_text(
                "عذرًا، واجهت مشكلة في فهم استجابة الذكاء الاصطناعي. "
                "يرجى المحاولة مرة أخرى أو إرسال صورة أوضح."
            )
        except Exception as e:
            logger.error(f"Error processing parsed JSON response: {e}")
            await update.message.reply_text("حدث خطأ غير متوقع بعد تحليل استجابة الذكاء الاصطناعي.")


    except Exception as e:
        logger.error(f"Error with OpenAI API for photo: {e}")
        await update.message.reply_text("عذرًا، حدث خطأ أثناء معالجة صورتك بواسطة الذكاء الاصطناعي. يرجى المحاولة مرة أخرى لاحقًا.")

# دالة للتعامل مع الرسائل النصية
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text
    is_allowed, remaining_requests = check_request_limit(user_id)

    if not is_allowed:
        await update.message.reply_text(
            f"عذرًا، لقد استنفدت عدد الطلبات المجانية ({MAX_FREE_REQUESTS}) لهذا اليوم. "
            "يرجى المحاولة مرة أخرى غدًا."
        )
        return

    # زيادة عدد الطلبات
    db_manager.increment_user_requests(user_id)

    logger.info(f"Received text from user {user_id}: '{user_message}'. Remaining free requests: {remaining_requests - 1}")

    await update.message.reply_text("تلقيت سؤالك، جارٍ البحث عن الإجابة...")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo", # يمكن استخدام gpt-4o إذا كان متاحًا لحسابك وميزانيتك
            messages=[
                {"role": "system", "content": "أنت خبير في الحضارات القديمة والآثار، مهمتك هي الإجابة عن أسئلة المستخدمين بوضوح ودقة. أجب بأسلوب شيق ومفيد."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
        )
        ai_response = response.choices[0].message.content
        await update.message.reply_text(ai_response)
    except Exception as e:
        logger.error(f"Error with OpenAI API for text: {e}")
        await update.message.reply_text("عذرًا، حدث خطأ أثناء معالجة سؤالك بواسطة الذكاء الاصطناعي. يرجى المحاولة مرة أخرى لاحقًا.")

# دالة للتعامل مع الأخطاء
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("عذرًا، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")

def main() -> None:
    """تشغيل البوت."""
    # الحصول على التوكن من متغيرات البيئة
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables.")

    # تهيئة التطبيق
    application = Application.builder().token(TOKEN).build()

    # تهيئة قاعدة البيانات (إنشاء الجداول إذا لم تكن موجودة)
    # db_manager.create_tables() # يتم استدعاؤها في __init__ لـ DatabaseManager
    # logger.info("Database tables checked/created.") # تم نقل هذه الرسالة إلى DatabaseManager

    # إضافة المعالجات (Handlers)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)

    # تشغيل البوت باستخدام الويب هوكس أو الاستقصاء
    PORT = int(os.environ.get("PORT", "8080")) # Render.com يوفر هذا المتغير
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # رابط خدمة Render الخاص بك

    if not WEBHOOK_URL:
        logger.error("WEBHOOK_URL environment variable is not set. Attempting to run in Polling mode.")
        # تشغيل في وضع الاستقصاء (Polling) - قد لا يعمل بشكل جيد على Render.com
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    else:
        logger.info(f"Running in Webhook mode. WEBHOOK_URL: {WEBHOOK_URL}, PORT: {PORT}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN, # استخدم التوكن كمسار للويب هوك لزيادة الأمان
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
        )
        logger.info(f"Webhook set for {WEBHOOK_URL}/{TOKEN} on port {PORT}")


if __name__ == "__main__":
    main()

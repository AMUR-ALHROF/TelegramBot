import logging
import os
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
import json # لإضافة التعامل مع JSON
from datetime import datetime, timedelta

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
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# تهيئة مدير قاعدة البيانات
db_manager = DatabaseManager(os.getenv("DATABASE_URL"))

# قائمة المستخدمين المسجلين (لأغراض بسيطة، يمكن استبدالها بقاعدة بيانات لاحقًا)
# registered_users = set() # لم نعد نستخدم هذه القائمة بعد وجود قاعدة البيانات

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
    user_data = db_manager.get_user(user_id)

    if not user_data:
        # مستخدم جديد، قم بإضافته إلى قاعدة البيانات
        db_manager.add_user(user_id, update.effective_user.username or update.effective_user.first_name)
        await update.message.reply_text(WELCOME_MESSAGE)
        logger.info(f"New user registered: {user_id}")
    else:
        # مستخدم موجود، أرسل له رسالة ترحيبية
        await update.message.reply_text(WELCOME_MESSAGE)
        logger.info(f"Existing user accessed: {user_id}")

# دالة للتحقق من عدد الطلبات المجانية المتبقية
def check_request_limit(user_id: int) -> tuple[bool, int]:
    user_data = db_manager.get_user(user_id)
    if not user_data:
        return False, MAX_FREE_REQUESTS # يجب ألا يحدث هذا إذا كان المستخدم مسجلاً

    last_request_date = user_data.last_request_date
    requests_count = user_data.requests_count

    # إذا كان اليوم مختلفًا عن آخر طلب، أعد تعيين العدد
    if last_request_date.date() != datetime.now().date():
        requests_count = 0
        db_manager.update_user_requests(user_id, requests_count, datetime.now())

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

    # تهيئة التطبيق باستخدام الويب هوكس
    application = Application.builder().token(TOKEN).build()

    # تهيئة قاعدة البيانات (إنشاء الجداول إذا لم تكن موجودة)
    db_manager.create_tables()
    logger.info("Database tables checked/created.")

    # إضافة المعالجات (Handlers)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)

    # تشغيل البوت باستخدام الويب هوكس
    PORT = int(os.environ.get("PORT", "8080")) # يستخدم المنفذ 8080 افتراضياً أو المتوفر
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # هذا يجب أن يكون رابط خدمة Render الخاص بك

    if not WEBHOOK_URL:
        logger.error("WEBHOOK_URL environment variable is not set. Webhook will not be configured.")
        # إذا لم يتم تعيين WEBHOOK_URL، يمكنك محاولة التشغيل في وضع الاستقصاء (Polling)
        # لكن Render يتطلب Webhooks لتطبيقات الويب
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    else:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN, # استخدم التوكن كمسار للويب هوك لزيادة الأمان
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
        )
        logger.info(f"Webhook set for {WEBHOOK_URL}/{TOKEN} on port {PORT}")


if __name__ == "__main__":
    main()

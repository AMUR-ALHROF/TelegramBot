import logging
import asyncio
import os
from flask import Flask, request, abort
from bot import TreasureHunterBot  # تأكد أن اسم ملف البوت الخاص بك هو 'bot.py' وأن الكلاس هو 'TreasureHunterBot'

# -- إعدادات التسجيل (Logging) --
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -- إعدادات Flask --
app = Flask(__name__)

# احصل على توكن البوت من متغير البيئة الذي ستضيفه في Render
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
    exit(1)

# WEBHOOK_SECRET (مفتاح سري لتأمين الويب هوك، اختياري لكن موصى به)
# يجب أن يكون هذا أيضاً متغير بيئة في Render
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", None) # إذا لم يتم تعيينه، سيكون None

# مسار الويب هوك الذي ستستقبل عليه تحديثات تيليجرام
WEBHOOK_PATH = "/webhook"

# -- تهيئة البوت --
# هذا السطر ينشئ نسخة من كلاس البوت الخاص بك
# افترض أن TreasureHunterBot يأخذ التوكن عند التهيئة.
bot_instance = TreasureHunterBot(token=TELEGRAM_BOT_TOKEN)

# -- نقطة نهاية الويب هوك لتيليجرام --
@app.route(WEBHOOK_PATH, methods=['POST'])
async def telegram_webhook():
    # التحقق من مفتاح الويب هوك السري إذا تم تعيينه
    if WEBHOOK_SECRET and request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret token received.")
        abort(403) # Forbidden access

    update_json = request.get_json()
    if not update_json:
        logger.warning("Received empty or invalid JSON from webhook")
        return "OK"

    try:
        # **هنا الجزء الحاسم:**
        # يجب أن يكون لدى كلاس TreasureHunterBot (في ملف bot.py)
        # دالة اسمها `process_telegram_update` (أو ما شابه)
        # تستقبل تحديثات Telegram على شكل قاموس (JSON)
        # وتقوم بمعالجتها.

        # نحن نستخدم asyncio.create_task لجدولة معالجة التحديث
        # حتى لا يتسبب في حظر خادم الويب.
        asyncio.create_task(bot_instance.process_telegram_update(update_json))
        logger.info(f"Update {update_json.get('update_id')} received and processing.")

    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True) # exc_info=True لطبع تفاصيل الخطأ كاملة
        return "Error", 500
return "OK"

# -- نقطة نهاية أساسية للتحقق من عمل التطبيق --
@app.route('/', methods=['GET'])
def home():
    return "Bot is running and listening for webhooks."

# -- نقطة البدء الرئيسية لخادم Flask --
if __name__ == "__main__":
    # المنفذ الذي سيستمع عليه الخادم
    # Render سيوفر قيمة لـ PORT كمتغير بيئة. نستخدم 10000 كافتراضي للاختبار المحلي.
    port = int(os.environ.get("PORT", 10000))

    # تشغيل خادم Flask
    # host='0.0.0.0' ضروري جداً للاستضافة على Render.
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port)

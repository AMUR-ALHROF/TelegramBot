import os
import logging
from flask import Flask

# إعداد السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة تطبيق Flask
app = Flask(__name__)

@app.route('/')
def home():
    logger.info("Home route accessed. Flask is responding.")
    return "✅ خدمة الويب (Flask) تعمل بنجاح."

# هذا الجزء ضروري لتشغيل تطبيق Flask بواسطة Gunicorn
if __name__ != '__main__':
    logger.info("main.py is being imported by Gunicorn. Flask app is ready.")
else:
    # هذا الجزء للتشغيل المحلي المباشر (ليس ضرورياً لـ Render)
    logger.info("main.py is being run directly. Running Flask app locally.")
    app.run(host='0.0.0.0', port=os.getenv('PORT', 5000))


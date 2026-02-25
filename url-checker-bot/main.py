import telebot
import requests
import re
from urllib.parse import urlparse
import logging

# إعدادات Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# رمز البوت
TOKEN = "YOUR_BOT_TOKEN_HERE"

# مفتاح Google Safe Browsing API (اختياري)
GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY_HERE"

# إنشاء البوت
bot = telebot.TeleBot(TOKEN)

def is_valid_url(url: str) -> bool:
    """التحقق من صيغة الرابط"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|
        r'localhost|
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def check_url_with_requests(url: str) -> dict:
    """فحص الرابط باستخدام مكتبة requests"""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        
        if response.status_code < 400:
            return {
                "status": "safe",
                "message": "✅ الرابط آمن",
                "details": f"رمز الحالة: {response.status_code}",
                "code": response.status_code
            }
        elif 400 <= response.status_code < 500:
            return {
                "status": "warning",
                "message": "⚠️ مشكلة في الوصول للرابط",
                "details": f"رمز الخطأ: {response.status_code}",
                "code": response.status_code
            }
        else:
            return {
                "status": "danger",
                "message": "❌ الرابط قد يكون غير آمن",
                "details": f"رمز الخطأ من الخادم: {response.status_code}",
                "code": response.status_code
            }
    except requests.exceptions.Timeout:
        return {
            "status": "warning",
            "message": "⚠️ انتهت مهلة الوقت - الرابط بطيء جداً",
            "details": "لم نتمكن من الوصول للرابط في الوقت المحدد"
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "danger",
            "message": "❌ خطأ في الاتصال - الرابط قد لا يكون حقيقياً",
            "details": "لم نتمكن من الاتصال بالخادم"
        }
    except Exception as e:
        return {
            "status": "warning",
            "message": "⚠️ حدث خطأ أثناء الفحص",
            "details": str(e)
        }

def check_url_with_google(url: str) -> dict:
    """فحص الرابط باستخدام Google Safe Browsing API"""
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY_HERE":
        return None
    
    try:
        api_url = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
        payload = {
            "client": {
                "clientId": "hasen-api-bot",
                "clientVersion": "1.0.0"
            },
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION"
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}]
            }
        }
        
        response = requests.post(f"{api_url}?key={GOOGLE_API_KEY}", json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            if "matches" in result and result["matches"]:
                return {
                    "status": "danger",
                    "message": "❌ الرابط خطير جداً - تم رصده في Google Safe Browsing",
                    "details": f"نوع التهديد: {result['matches'][0]['threatType']}"
                }
            else:
                return {
                    "status": "safe",
                    "message": "✅ الرابط آمن حسب Google Safe Browsing",
                    "details": "لم يتم رصد أي تهديدات"
                }
        return None
    except Exception as e:
        logger.error(f"Google Safe Browsing error: {e}")
        return None

def extract_domain(url: str) -> str:
    """استخراج اسم النطاق من الرابط"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return "Unknown"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """رسالة البداية"""
    user_name = message.from_user.first_name
    welcome_text = f"""
مرحباً {user_name}! 👋

أنا بوت فحص الروابط الآمنة 🔒

كيفية الاستخدام:
• أرسل لي أي رابط (URL)
• سأفحصه وأخبرك إذا كان آمن ✅ أم خطير ❌

مثال:
https://google.com

/help - للمساعدة
/about - معلومات عني
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['help'])
def send_help(message):
    """رسالة المساعدة"""
    help_text = """
📖 معلومات عن البوت:

🔍 كيفية فحص الروابط:
1. أرسل الرابط مباشرة (https://example.com)
2. سأفحصه ضد قواعد الأمان
3. ستتلقى النتيجة مع التفاصيل

⚙️ الفحوصات المستخدمة:
✓ التحقق من صيغة الرابط
✓ فحص الاتصال بالخادم
✓ التحقق من رمز الحالة HTTP
✓ Google Safe Browsing (إن توفر)

⚠️ ملاحظات مهمة:
• الفحص قد لا يكون دقيق بنسبة 100%
• استخدم الحذر مع الروابط المريبة
• لا تنقر على روابط خطيرة!

/start - العودة للبداية
/about - معلومات عن البوت
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['about'])
def send_about(message):
    """معلومات عن البوت"""
    about_text = """
ℹ️ معلومات عن البوت:

📱 اسم البوت: URL Safety Checker Bot
🤖 الإصدار: 1.0.0
🔧 المكتبة: telebot (pyTelegramBotAPI)

👨‍💻 المطور: Hasen API
📧 البريد: your-email@example.com

🌟 الميزات:
✅ فحص فوري للروابط
✅ كشف التهديدات
✅ معلومات التفصيل الكامل
✅ واجهة سهلة الاستخدام
✅ دعم Google Safe Browsing

📚 روابط مهمة:
• GitHub: github.com/uug405528-dev/Hasen-api

شكراً لاستخدامك البوت! 🙏
    """
    bot.reply_to(message, about_text)

@bot.message_handler(func=lambda message: True)
def check_url(message):
    """فحص الرابط المرسل من المستخدم"""
    url = message.text.strip()
    
    if not url.startswith("http://") and not url.startswith("https://"):
        bot.reply_to(message, 
            "⚠️ الرجاء إرسال رابط يبدأ بـ http:// أو https://\n\n"
            "مثال: https://google.com")
        return
    
    if not is_valid_url(url):
        bot.reply_to(message,
            "❌ صيغة الرابط غير صحيحة\n\n"
            "الرجاء إرسال رابط صحيح مثل: https://example.com")
        return
    
    status_msg = bot.reply_to(message, "🔍 جارٍ فحص الرابط...")
    
    result = None
    
    if GOOGLE_API_KEY and GOOGLE_API_KEY != "YOUR_GOOGLE_API_KEY_HERE":
        result = check_url_with_google(url)
    
    if result is None:
        result = check_url_with_requests(url)
    
    domain = extract_domain(url)
    
    reply_text = f"""
🔗 الرابط: {url}
🌐 النطاق: {domain}

{result['message']}
📝 التفاصيل: {result['details']}
    """
    
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        text=reply_text
    )
    
    if result['status'] == 'safe':
        bot.send_message(message.chat.id, "✅ يمكنك الدخول للرابط بأمان!")
    elif result['status'] == 'warning':
        bot.send_message(message.chat.id, "⚠️ كن حذراً عند فتح هذا الرابط!")
    elif result['status'] == 'danger':
        bot.send_message(message.chat.id, "❌ ⛔ لا تفتح هذا الرابط - قد يكون خطيراً!")

def main():
    """تشغيل البوت"""
    print("🤖 البوت يعمل الآن...")
    print("اضغط Ctrl+C للإيقاف")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت")

if __name__ == '__main__':
    main()
import google.generativeai as genai
import json
import re
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

model = None

def setup_model():
    global model
    if not GEMINI_API_KEY:
        logger.error("❌ Chưa có GEMINI_API_KEY")
        return

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # --- THAY ĐỔI QUAN TRỌNG ---
        # Không dùng 'gemini-1.5-flash' nữa vì tài khoản bạn bị lỗi 404
        # Quay về dùng 'gemini-pro' (Bản ổn định nhất toàn cầu)
        model_name = 'gemini-pro'
        
        logger.info(f"🔄 Đang kết nối với model: {model_name}...")
        model = genai.GenerativeModel(model_name)
        
        # Gửi thử 1 tin test ngay khi khởi động để check lỗi
        response = model.generate_content("Hello")
        logger.info("✅ KẾT NỐI AI THÀNH CÔNG! (Model đang sống)")
        
    except Exception as e:
        logger.error(f"❌ LỖI KHỞI TẠO AI: {e}")
        model = None

# Khởi tạo ngay
setup_model()

def clean_json_response(text):
    """Hàm làm sạch JSON (Gemini Pro hay trả về markdown dư thừa)"""
    try:
        text = text.replace('```json', '').replace('```', '').strip()
        # Tìm đoạn bắt đầu bằng { và kết thúc bằng }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match: return json.loads(match.group())
        return json.loads(text)
    except: return None

def lookup_word(text):
    if not model: return None
    try:
        # Prompt cho Gemini Pro cần rõ ràng hơn
        prompt = f"""Bạn là từ điển. Hãy tra từ: "{text}".
        Chỉ trả về JSON duy nhất (không giải thích):
        {{"hanzi": "{text}", "pinyin": "phiên âm", "meaning": "nghĩa tiếng việt"}}
        Nếu không phải từ có nghĩa, trả về null."""
        
        response = model.generate_content(prompt)
        return clean_json_response(response.text)
    except Exception as e:
        logger.error(f"Lỗi tra từ: {e}")
        return None

def generate_example(word):
    hanzi = word.get('Hán tự','')
    meaning = word.get('Nghĩa','')
    backup = {"han": f"{hanzi}", "pinyin": "...", "viet": f"{meaning}"}
    if not model: return backup
    try:
        prompt = f"""Đặt câu ví dụ HSK 1 cực ngắn với: {hanzi} ({meaning}).
        Trả về JSON duy nhất:
        {{"han": "câu chữ hán", "pinyin": "phiên âm", "viet": "dịch tiếng việt"}}"""
        
        response = model.generate_content(prompt)
        res = clean_json_response(response.text)
        return res if res else backup
    except: return backup

def chat_reply(text):
    if not model: 
        # Nếu model = None thì báo lỗi cấu hình
        return "Lỗi kết nối AI (Vui lòng kiểm tra Log Server)."
    try:
        response = model.generate_content(f"Bạn là bot dạy tiếng Trung. User: '{text}'. Trả lời ngắn gọn bằng tiếng Việt.")
        return response.text.strip()
    except Exception as e:
        # Nếu vào đây nghĩa là Model bị lỗi khi đang chạy
        logger.error(f"Lỗi khi chat: {e}")
        return "Hệ thống đang bận (Lỗi xử lý AI)."

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
        
        # SỬ DỤNG GEMINI 1.5 FLASH (Bản mới nhất, nhanh, miễn phí)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        logger.info("✅ Đã kết nối thành công: Gemini 1.5 Flash")
    except Exception as e:
        logger.error(f"❌ Lỗi cấu hình Gemini: {e}")
        model = None

# Khởi tạo ngay khi import
setup_model()

def clean_json_response(text):
    """Hàm làm sạch chuỗi JSON do AI trả về"""
    try:
        # Xóa các ký tự markdown như ```json và ```
        text = text.replace('```json', '').replace('```', '').strip()
        # Tìm đoạn JSON hợp lệ trong chuỗi (nếu AI nói nhảm thêm bên ngoài)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text) # Thử parse trực tiếp nếu không tìm thấy pattern
    except:
        return None

def lookup_word(text):
    if not model: return None
    try:
        prompt = f"""
        Bạn là từ điển tiếng Trung. Hãy tra từ: "{text}".
        Yêu cầu trả về JSON chuẩn (không giải thích thêm):
        {{"hanzi": "{text}", "pinyin": "phiên âm", "meaning": "nghĩa tiếng việt"}}
        Nếu không phải từ có nghĩa, trả về null.
        """
        response = model.generate_content(prompt)
        return clean_json_response(response.text)
    except Exception as e:
        logger.error(f"❌ Lỗi tra từ: {e}")
        return None

def generate_example(word):
    hanzi = word.get('Hán tự','')
    meaning = word.get('Nghĩa','')
    backup = {"han": f"{hanzi}", "pinyin": "...", "viet": f"{meaning}"}
    
    if not model: return backup
    try:
        prompt = f"""
        Đặt 1 câu ví dụ tiếng Trung CỰC ĐƠN GIẢN (HSK 1, <10 từ) dùng từ: {hanzi} ({meaning}).
        Trả về JSON chuẩn:
        {{"han": "câu chữ hán", "pinyin": "phiên âm", "viet": "dịch tiếng việt"}}
        """
        response = model.generate_content(prompt)
        result = clean_json_response(response.text)
        return result if result else backup
    except: return backup

def chat_reply(text):
    if not model: return "Lỗi kết nối AI."
    try:
        response = model.generate_content(f"Bạn là bot dạy tiếng Trung. User: '{text}'. Trả lời ngắn gọn tiếng Việt.")
        return response.text.strip()
    except Exception as e:
        logger.error(f"Chat Error: {e}")
        return "Hệ thống đang bận."

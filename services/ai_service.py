import google.generativeai as genai
import json
import re
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

model = None

def setup_model():
    """Hàm khởi tạo model an toàn với cơ chế Fallback"""
    global model
    if not GEMINI_API_KEY:
        logger.error("❌ Chưa có GEMINI_API_KEY trong config")
        return None

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Ưu tiên dùng Flash (Nhanh và nhẹ)
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Test thử model xem có sống không
            model.generate_content("test")
            logger.info("✅ Đã kết nối Gemini 1.5 Flash")
        except:
            # Nếu lỗi (do thư viện cũ), chuyển sang bản Pro truyền thống
            logger.warning("⚠️ Không tìm thấy 1.5 Flash, chuyển sang Gemini Pro")
            model = genai.GenerativeModel('gemini-pro')
            
    except Exception as e:
        logger.error(f"❌ Cấu hình Gemini thất bại: {e}")
        model = None

# Gọi hàm khởi tạo ngay khi import
setup_model()

def lookup_word(text):
    if not model: return None
    try:
        # Prompt được tối ưu để tránh lỗi JSON
        prompt = f"""
        Bạn là từ điển tiếng Trung. Hãy tra từ: "{text}".
        Yêu cầu trả về JSON thuần túy theo định dạng sau (không markdown, không giải thích thêm):
        {{"hanzi": "{text}", "pinyin": "phiên âm", "meaning": "nghĩa tiếng việt"}}
        Nếu từ này không phải tiếng Trung hoặc không có nghĩa, hãy trả về null.
        """
        res = model.generate_content(prompt).text.strip()
        # Làm sạch JSON (xóa ```json và ``` nếu có)
        res = res.replace('```json', '').replace('```', '').strip()
        return json.loads(res)
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
        Đặt 1 câu tiếng Trung CỰC KỲ ĐƠN GIẢN (HSK 1, dưới 10 từ) có sử dụng từ: {hanzi} ({meaning}).
        Trả về JSON thuần túy:
        {{"han": "câu chữ hán", "pinyin": "phiên âm", "viet": "dịch tiếng việt"}}
        """
        res = model.generate_content(prompt).text.strip()
        res = res.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', res, re.DOTALL)
        return json.loads(match.group()) if match else backup
    except Exception as e:
        logger.error(f"❌ Lỗi tạo ví dụ: {e}")
        return backup

def chat_reply(text):
    if not model: return "Bot đang gặp lỗi kết nối AI. Vui lòng thử lại sau."
    try: 
        return model.generate_content(f"Bạn là trợ lý học tiếng Trung thân thiện. User nói: '{text}'. Hãy trả lời ngắn gọn bằng tiếng Việt.").text.strip()
    except Exception as e:
        logger.error(f"❌ Lỗi Chat AI: {e}")
        return "Hệ thống đang bận, thử lại sau nhé."

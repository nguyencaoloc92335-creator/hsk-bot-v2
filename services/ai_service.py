import google.generativeai as genai
import json
import re
import logging
import os
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

model = None

def setup_ai():
    global model
    # Lấy key từ biến môi trường cho an toàn
    api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    
    if not api_key:
        logger.error("❌ Chưa có API Key.")
        return

    try:
        genai.configure(api_key=api_key)
        # Sử dụng model 'gemini-pro' cho ổn định nhất
        model = genai.GenerativeModel('gemini-pro')
        logger.info("✅ AI Connected: Gemini Pro")
    except Exception as e:
        logger.error(f"❌ AI Init Error: {e}")

setup_ai()

def clean_json(text):
    """Làm sạch dữ liệu JSON từ AI bất chấp định dạng"""
    try:
        # Xóa các ký tự markdown thừa
        text = text.replace('```json', '').replace('```', '').strip()
        
        # Dùng Regex tìm đoạn bắt đầu bằng { và kết thúc bằng } xa nhất
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)
    except:
        return None

def generate_sentence_with_annotation(word):
    hanzi = word.get('Hán tự', '')
    meaning = word.get('Nghĩa', '')
    
    # Dữ liệu dự phòng (Fallback) nếu AI hỏng
    backup = {
        "sentence_han": f"{hanzi}", 
        "sentence_pinyin": "", 
        "sentence_viet": f"(Nghĩa: {meaning})", 
        "new_words": []
    }
    
    if not model: return backup
    
    try:
        prompt = f"""
        Nhiệm vụ: Tạo ví dụ cho từ tiếng Trung.
        Từ khóa: "{hanzi}" (Nghĩa: {meaning}).
        
        Yêu cầu:
        1. Đặt 1 câu tiếng Trung đơn giản (HSK 1-2).
        2. Trả về đúng định dạng JSON bên dưới. KHÔNG giải thích gì thêm.
        
        JSON mẫu:
        {{
            "sentence_han": "câu chữ hán",
            "sentence_pinyin": "phiên âm",
            "sentence_viet": "dịch tiếng việt",
            "new_words": []
        }}
        """
        response = model.generate_content(prompt)
        data = clean_json(response.text)
        
        # Kiểm tra xem JSON có đủ trường không, nếu thiếu thì dùng backup
        if data and 'sentence_han' in data:
            return data
        return backup
        
    except Exception as e:
        logger.error(f"⚠️ Lỗi tạo ví dụ: {e}")
        return backup

def chat_reply(text):
    if not model: return "Hệ thống AI đang bảo trì."
    try:
        res = model.generate_content(f"Bạn là trợ lý tiếng Trung. User: '{text}'. Trả lời ngắn gọn tiếng Việt.")
        return res.text.strip()
    except:
        return "Máy chủ đang bận, thử lại sau nhé."

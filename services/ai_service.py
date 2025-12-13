import google.generativeai as genai
import json
import re
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

model = None

def setup_model():
    """Hàm tự động quét và chọn Model có sẵn"""
    global model
    if not GEMINI_API_KEY:
        logger.error("❌ Chưa có GEMINI_API_KEY")
        return

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        selected_model_name = None
        
        logger.info("🔍 Đang quét danh sách Model từ Google...")
        
        # 1. Lấy danh sách thực tế từ Google
        try:
            available_models = []
            for m in genai.list_models():
                # Chỉ lấy model hỗ trợ chat/tạo nội dung
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            logger.info(f"📋 Danh sách Model tìm thấy: {available_models}")
            
            # 2. Thuật toán chọn Model (Ưu tiên Flash -> Pro -> 1.0)
            # Tìm model nào có chữ 'flash'
            for m in available_models:
                if 'flash' in m and '1.5' in m:
                    selected_model_name = m
                    break
            
            # Nếu không có Flash, tìm Pro 1.5
            if not selected_model_name:
                for m in available_models:
                    if 'pro' in m and '1.5' in m:
                        selected_model_name = m
                        break
            
            # Nếu vẫn không có, tìm Pro 1.0 (bản cũ)
            if not selected_model_name:
                for m in available_models:
                    if 'gemini-pro' in m:
                        selected_model_name = m
                        break
                        
        except Exception as scan_error:
            logger.error(f"⚠️ Lỗi khi quét model: {scan_error}")
            # Fallback cứng nếu không quét được
            selected_model_name = 'gemini-pro'

        if selected_model_name:
            logger.info(f"✅ CHỐT DÙNG MODEL: {selected_model_name}")
            model = genai.GenerativeModel(selected_model_name)
        else:
            logger.error("❌ Không tìm thấy bất kỳ model nào khả dụng!")

    except Exception as e:
        logger.error(f"❌ Lỗi cấu hình Gemini: {e}")
        model = None

# Gọi hàm khởi tạo ngay
setup_model()

def clean_json_response(text):
    try:
        text = text.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match: return json.loads(match.group())
        return json.loads(text)
    except: return None

def lookup_word(text):
    if not model: return None
    try:
        prompt = f"""Tra từ: "{text}". Trả JSON: {{\"hanzi\": \"{text}\", \"pinyin\": \"...\", \"meaning\": \"...\"}}. Nếu ko phải tiếng Trung trả null."""
        response = model.generate_content(prompt)
        return clean_json_response(response.text)
    except Exception as e:
        logger.error(f"Tra từ lỗi: {e}")
        return None

def generate_example(word):
    hanzi = word.get('Hán tự','')
    meaning = word.get('Nghĩa','')
    backup = {"han": f"{hanzi}", "pinyin": "...", "viet": f"{meaning}"}
    if not model: return backup
    try:
        prompt = f"Đặt câu ví dụ HSK 1 với: {hanzi} ({meaning}). Trả JSON: {{\"han\": \"...\", \"pinyin\": \"...\", \"viet\": \"...\"}}"
        response = model.generate_content(prompt)
        res = clean_json_response(response.text)
        return res if res else backup
    except: return backup

def chat_reply(text):
    if not model: return "Lỗi kết nối AI."
    try:
        response = model.generate_content(f"Bạn là bot tiếng Trung. User: '{text}'. Trả lời ngắn gọn tiếng Việt.")
        return response.text.strip()
    except: return "Hệ thống bận."

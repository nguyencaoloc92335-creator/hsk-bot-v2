import google.generativeai as genai
import json
import re
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

model = None

def setup_and_auto_pick_model():
    """
    Hàm này KHÔNG đoán tên model.
    Nó hỏi Google danh sách và lấy cái đầu tiên dùng được.
    """
    global model
    if not GEMINI_API_KEY:
        logger.error("❌ Chưa có GEMINI_API_KEY")
        return

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        logger.info("🔍 ĐANG QUÉT DANH SÁCH MODEL TỪ TÀI KHOẢN CỦA BẠN...")
        
        found_model_name = None
        
        # Gọi hàm ListModels như gợi ý của Google
        for m in genai.list_models():
            # In ra log để bạn xem có những cái gì
            logger.info(f"👉 Tìm thấy: {m.name} | Method: {m.supported_generation_methods}")
            
            # Chỉ lấy model hỗ trợ tạo nội dung (generateContent)
            if 'generateContent' in m.supported_generation_methods:
                # Ưu tiên lấy bản Flash hoặc Pro nếu thấy
                if 'flash' in m.name:
                    found_model_name = m.name
                    break # Tìm thấy Flash là chốt luôn
                
                # Nếu chưa có Flash, tạm lưu cái này lại (ví dụ gemini-pro)
                if not found_model_name:
                    found_model_name = m.name

        if found_model_name:
            logger.info(f"✅ CHỐT DÙNG MODEL: {found_model_name}")
            # Khởi tạo model với cái tên chính xác vừa tìm được
            model = genai.GenerativeModel(found_model_name)
            
            # Test ngay lập tức
            try:
                model.generate_content("Test connection")
                logger.info("🎉 KẾT NỐI AI THÀNH CÔNG RỰC RỠ!")
            except Exception as e:
                logger.error(f"⚠️ Model {found_model_name} khởi tạo được nhưng lỗi khi gọi: {e}")
        else:
            logger.error("❌ KHÔNG TÌM THẤY BẤT KỲ MODEL NÀO CHO PHÉP GENERATE CONTENT.")

    except Exception as e:
        logger.error(f"❌ LỖI NGHIÊM TRỌNG KHI QUÉT MODEL: {e}")
        model = None

# Chạy hàm này ngay khi khởi động
setup_and_auto_pick_model()

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
        # Prompt đơn giản
        prompt = f"""Tra từ: "{text}". Trả JSON: {{\"hanzi\": \"{text}\", \"pinyin\": \"...\", \"meaning\": \"...\"}}. Nếu ko phải từ có nghĩa trả null."""
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
    if not model: return "Hệ thống AI đang bảo trì (Lỗi Model)."
    try:
        response = model.generate_content(f"Bạn là bot tiếng Trung. User: '{text}'. Trả lời ngắn gọn tiếng Việt.")
        return response.text.strip()
    except: return "Hệ thống bận."

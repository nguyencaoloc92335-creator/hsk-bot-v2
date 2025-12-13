import google.generativeai as genai
import json
import re
import logging
import os # Import os để lấy key từ biến môi trường

logger = logging.getLogger(__name__)

# LẤY KEY TỪ BIẾN MÔI TRƯỜNG (AN TOÀN TUYỆT ĐỐI)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

model = None

def setup_and_auto_pick_model():
    global model
    if not GEMINI_API_KEY:
        logger.error("❌ Chưa cấu hình GEMINI_API_KEY trong Environment Variables!")
        return

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Ưu tiên tìm Flash hoặc Pro
        target_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        # Lấy danh sách thực tế
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        logger.info(f"📋 Các model khả dụng: {available}")

        chosen_model = None
        # Thuật toán tìm model:
        for target in target_models:
            for real in available:
                if target in real:
                    chosen_model = real
                    break
            if chosen_model: break
        
        # Fallback nếu không khớp tên nào (lấy cái đầu tiên)
        if not chosen_model and available:
            chosen_model = available[0]

        if chosen_model:
            logger.info(f"✅ Đã chọn Model: {chosen_model}")
            model = genai.GenerativeModel(chosen_model)
        else:
            logger.error("❌ Không tìm thấy Model nào dùng được!")

    except Exception as e:
        logger.error(f"❌ Lỗi khởi tạo AI: {e}")

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
        prompt = f"""Tra từ: "{text}". Trả JSON: {{\"hanzi\": \"{text}\", \"pinyin\": \"...\", \"meaning\": \"...\"}}. Nếu ko phải từ có nghĩa trả null."""
        response = model.generate_content(prompt)
        return clean_json_response(response.text)
    except: return None

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
    if not model: return "Bot đang bảo trì AI."
    try:
        # Prompt đơn giản để tiết kiệm token
        response = model.generate_content(f"User: '{text}'. Trả lời ngắn gọn tiếng Việt.")
        return response.text.strip()
    except: return "Hệ thống bận."

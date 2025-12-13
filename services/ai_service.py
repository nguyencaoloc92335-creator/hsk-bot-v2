import google.generativeai as genai
import json
import re
import logging
from config import GEMINI_API_KEY

# Cấu hình log để soi lỗi
logger = logging.getLogger(__name__)

model = None
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    logger.error(f"❌ Cấu hình Gemini thất bại: {e}")

def lookup_word(text):
    if not model: return None
    try:
        prompt = f"Tra từ điển từ: '{text}'. Trả JSON: {{\"hanzi\": \"{text}\", \"pinyin\": \"...\", \"meaning\": \"...\"}}. Nếu không phải tiếng Trung trả null."
        res = model.generate_content(prompt).text.strip()
        res = res.replace('```json', '').replace('```', '')
        return json.loads(res)
    except Exception as e:
        logger.error(f"❌ Lỗi tra từ: {e}") # In lỗi ra log
        return None

def generate_example(word):
    hanzi, meaning = word.get('Hán tự',''), word.get('Nghĩa','')
    backup = {"han": f"{hanzi}", "pinyin": "...", "viet": f"{meaning}"}
    if not model: return backup
    try:
        prompt = f"Đặt 1 câu tiếng Trung CỰC KỲ ĐƠN GIẢN (HSK 1, <10 từ) dùng từ: {hanzi} ({meaning}). Trả JSON: {{\"han\": \"...\", \"pinyin\": \"...\", \"viet\": \"...\"}}"
        res = model.generate_content(prompt).text.strip()
        match = re.search(r'\{.*\}', res, re.DOTALL)
        return json.loads(match.group()) if match else backup
    except Exception as e:
        logger.error(f"❌ Lỗi tạo ví dụ: {e}")
        return backup

def chat_reply(text):
    if not model: return "Gõ 'Menu' để xem hướng dẫn (Lỗi cấu hình AI)."
    try: 
        return model.generate_content(f"Bạn là trợ lý học tiếng Trung. User: '{text}'. Trả lời ngắn gọn tiếng Việt.").text.strip()
    except Exception as e:
        logger.error(f"❌ GEMINI ERROR: {e}") # Quan trọng: In lỗi cụ thể ra đây
        return "Bot đang bị lỗi kết nối AI. Vui lòng thử lại sau."

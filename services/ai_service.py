import google.generativeai as genai
import json
import re
import logging
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

model = None

# --- KHỞI TẠO MODEL CŨ (GEMINI PRO) ---
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        # Dùng model 'gemini-pro' chuẩn, không dùng Flash nữa
        model = genai.GenerativeModel('gemini-pro')
        logger.info("✅ Đã kết nối Gemini Pro (Bản cũ)")
except Exception as e:
    logger.error(f"❌ Cấu hình Gemini thất bại: {e}")

def lookup_word(text):
    if not model: return None
    try:
        # Prompt cũ đơn giản
        prompt = f"""Tra từ điển: "{text}". Trả JSON: {{\"hanzi\": \"{text}\", \"pinyin\": \"...\", \"meaning\": \"...\"}}. Nếu ko phải tiếng Trung trả null."""
        res = model.generate_content(prompt).text.strip()
        # Xử lý chuỗi JSON trả về (Gemini Pro hay trả về markdown)
        if '```' in res:
            res = res.replace('```json', '').replace('```', '')
        return json.loads(res.strip())
    except Exception as e:
        logger.error(f"❌ Lỗi tra từ: {e}")
        return None

def generate_example(word):
    hanzi = word.get('Hán tự','')
    meaning = word.get('Nghĩa','')
    backup = {"han": f"{hanzi}", "pinyin": "...", "viet": f"{meaning}"}
    if not model: return backup
    try:
        prompt = f"Đặt 1 câu tiếng Trung CỰC ĐƠN GIẢN (HSK 1) dùng: {hanzi} ({meaning}). Trả JSON: {{\"han\": \"...\", \"pinyin\": \"...\", \"viet\": \"...\"}}"
        res = model.generate_content(prompt).text.strip()
        if '```' in res:
            res = res.replace('```json', '').replace('```', '')
        match = re.search(r'\{.*\}', res.strip(), re.DOTALL)
        return json.loads(match.group()) if match else backup
    except: return backup

def chat_reply(text):
    if not model: return "Lỗi kết nối AI."
    try: 
        return model.generate_content(f"Bạn là trợ lý học tiếng Trung. User: '{text}'. Trả lời ngắn gọn tiếng Việt.").text.strip()
    except Exception as e:
        logger.error(f"Chat Error: {e}")
        return "AI đang bận, thử lại sau."

import google.generativeai as genai
import json
import re
from config import GEMINI_API_KEY

model = None
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
except: pass

def lookup_word(text):
    if not model: return None
    try:
        prompt = f"Tra từ điển từ: '{text}'. Trả JSON: {{\"hanzi\": \"{text}\", \"pinyin\": \"...\", \"meaning\": \"...\"}}. Nếu không phải tiếng Trung trả null."
        res = model.generate_content(prompt).text.strip()
        res = res.replace('```json', '').replace('```', '')
        return json.loads(res)
    except: return None

def generate_example(word):
    hanzi, meaning = word.get('Hán tự',''), word.get('Nghĩa','')
    backup = {"han": f"{hanzi}", "pinyin": "...", "viet": f"{meaning}"}
    if not model: return backup
    try:
        prompt = f"Đặt 1 câu tiếng Trung CỰC KỲ ĐƠN GIẢN (HSK 1, <10 từ) dùng từ: {hanzi} ({meaning}). Trả JSON: {{\"han\": \"...\", \"pinyin\": \"...\", \"viet\": \"...\"}}"
        res = model.generate_content(prompt).text.strip()
        match = re.search(r'\{.*\}', res, re.DOTALL)
        return json.loads(match.group()) if match else backup
    except: return backup

def chat_reply(text):
    if not model: return "Gõ 'Menu' để xem hướng dẫn."
    try: return model.generate_content(f"Bạn là trợ lý học tiếng Trung. User: '{text}'. Trả lời ngắn gọn tiếng Việt.").text.strip()
    except: return "Lỗi mạng."
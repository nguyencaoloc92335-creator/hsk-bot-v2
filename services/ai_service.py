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
    if not GEMINI_API_KEY: return
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Tự động chọn model như code cũ của bạn
        model = genai.GenerativeModel('gemini-pro') 
        # (Nếu bạn đang dùng 1.5 flash thì sửa lại tên ở đây nhé)
    except: pass

setup_ai()

def clean_json(text):
    try:
        text = text.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group()) if match else json.loads(text)
    except: return None

def generate_sentence_with_annotation(word):
    """
    Tạo câu ví dụ + Giải thích từ mới trong câu đó
    """
    hanzi = word.get('Hán tự','')
    meaning = word.get('Nghĩa','')
    backup = {
        "sentence_han": f"{hanzi}...", 
        "sentence_pinyin": "...", 
        "sentence_viet": "...", 
        "new_words": []
    }
    
    if not model: return backup
    
    try:
        prompt = f"""
        Bạn là giáo viên tiếng Trung. Hãy đặt 1 câu ví dụ ngắn (HSK 1-3) sử dụng từ: "{hanzi}" (nghĩa: {meaning}).
        
        Yêu cầu quan trọng:
        1. Câu ví dụ phải hoàn chỉnh, có nghĩa.
        2. Nếu trong câu ví dụ có sử dụng từ vựng nào khác (ngoài từ "{hanzi}" và các từ quá cơ bản như 我, 你, 是), hãy liệt kê nó vào danh sách "new_words" để giải thích cho học sinh.
        
        Trả về JSON định dạng sau (không markdown):
        {{
            "sentence_han": "câu chữ hán",
            "sentence_pinyin": "phiên âm của cả câu",
            "sentence_viet": "dịch nghĩa cả câu",
            "new_words": [
                {{"han": "từ lạ 1", "pinyin": "...", "viet": "..."}},
                {{"han": "từ lạ 2", "pinyin": "...", "viet": "..."}}
            ]
        }}
        """
        response = model.generate_content(prompt)
        data = clean_json(response.text)
        return data if data else backup
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return backup

def chat_reply(text):
    if not model: return "Lỗi AI."
    try: return model.generate_content(f"User: '{text}'. Trả lời tiếng Việt ngắn gọn.").text.strip()
    except: return "Bot bận."

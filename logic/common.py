import time
from datetime import datetime, timedelta, timezone
import unicodedata
import difflib

def get_ts(): return int(time.time())

def get_vn_time(): 
    return datetime.now(timezone(timedelta(hours=7)))

def get_today_str():
    return get_vn_time().strftime("%Y-%m-%d")

# [ĐÃ XÓA] Hàm is_sleep_mode()

# --- CÁC HÀM XỬ LÝ VĂN BẢN THÔNG MINH ---

def remove_accents(input_str):
    """Chuyển tiếng Việt/Trung có dấu thành không dấu"""
    if not input_str: return ""
    s1 = unicodedata.normalize('NFD', input_str)
    s2 = ''.join(c for c in s1 if unicodedata.category(c) != 'Mn')
    return s2.lower()

def normalize_text(text):
    """Chuẩn hóa: Viết thường + Không dấu + Viết liền (xóa khoảng trắng)"""
    if not text: return ""
    no_accent = remove_accents(text)
    clean_text = "".join(e for e in no_accent if e.isalnum())
    return clean_text

def check_answer_smart(user_ans, correct_ans):
    """
    So sánh đáp án thông minh
    """
    u = normalize_text(user_ans)
    c = normalize_text(correct_ans)
    
    if u == c: return True
    if abs(len(u) - len(c)) > 2: return False
    
    matcher = difflib.SequenceMatcher(None, u, c)
    match_len = sum(triple[-1] for triple in matcher.get_matching_blocks())
    errors = max(len(u), len(c)) - match_len
    
    return errors <= 2

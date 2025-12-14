import time
from datetime import datetime, timedelta, timezone
import unicodedata
import difflib

def get_ts(): return int(time.time())

def get_vn_time(): 
    return datetime.now(timezone(timedelta(hours=7)))

def is_sleep_mode():
    return 0 <= get_vn_time().hour < 6

def get_today_str():
    return get_vn_time().strftime("%Y-%m-%d")

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
    # 1. Xóa dấu
    no_accent = remove_accents(text)
    # 2. Xóa khoảng trắng và ký tự lạ, chỉ giữ lại chữ cái và số
    clean_text = "".join(e for e in no_accent if e.isalnum())
    return clean_text

def check_answer_smart(user_ans, correct_ans):
    """
    So sánh đáp án thông minh:
    1. Chuẩn hóa cả 2 về dạng không dấu, viết liền.
    2. Chấp nhận sai số <= 2 ký tự (thừa, thiếu, sai khác).
    """
    u = normalize_text(user_ans)
    c = normalize_text(correct_ans)
    
    # Nếu khớp hoàn toàn sau khi chuẩn hóa
    if u == c: return True
    
    # Kiểm tra độ dài chênh lệch quá lớn thì loại luôn
    if abs(len(u) - len(c)) > 2: return False
    
    # Dùng SequenceMatcher để đếm số lượng chỉnh sửa cần thiết
    # Tuy nhiên, để đơn giản và hiệu quả cho độ lệch nhỏ, ta dùng difflib
    matcher = difflib.SequenceMatcher(None, u, c)
    # Tính số ký tự giống nhau
    match_len = sum(triple[-1] for triple in matcher.get_matching_blocks())
    
    # Số lỗi = Độ dài chuỗi dài nhất - Số ký tự giống nhau
    errors = max(len(u), len(c)) - match_len
    
    return errors <= 2

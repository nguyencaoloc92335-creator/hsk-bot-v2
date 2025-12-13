import re
import time
from services import fb_service
import database
from logic import common

def handle_pause(uid, text, state, cache):
    msg = text.lower().strip()
    
    # Mặc định là nghỉ không giới hạn (Indefinite)
    pause_type = "INDEFINITE"
    duration = 0
    reply_msg = "😴 Ok, bạn nghỉ ngơi đi.\nMỗi 30 phút mình sẽ hỏi thăm xem bạn học tiếp được chưa nhé."

    # Kiểm tra xem có con số nào trong câu không (VD: nghỉ 15p, nghỉ 1 tiếng)
    # Regex tìm số + đơn vị (p, phút, h, giờ, tiếng)
    match = re.search(r'(\d+)\s*(p|phút|m|h|giờ|tiếng)', msg)
    
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        
        # Quy đổi ra giây
        if unit in ['h', 'giờ', 'tiếng']:
            duration = amount * 3600
            time_str = f"{amount} tiếng"
        else:
            duration = amount * 60
            time_str = f"{amount} phút"
            
        pause_type = "FIXED"
        reply_msg = f"👌 Ok, nghỉ giải lao **{time_str}** nhé.\nHết giờ mình sẽ gọi."

    # Cập nhật trạng thái
    state["mode"] = "PAUSED"
    state["pause_info"] = {
        "type": pause_type,
        "start_at": common.get_ts(),
        "end_at": common.get_ts() + duration if pause_type == "FIXED" else 0,
        "last_remind": common.get_ts() # Mốc thời gian nhắc gần nhất
    }
    
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, reply_msg)

def resume(uid, state, cache):
    # Quay lại trạng thái trước đó hoặc về Menu
    state["mode"] = "AUTO" # Hoặc IDLE tùy bạn, ở đây cho về AUTO để học luôn
    state["pause_info"] = None
    state["waiting"] = False # Reset chờ đợi cũ
    
    # Reset timer để học ngay
    state["next_time"] = 0 
    
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, "👋 Mừng bạn quay lại! Chúng ta học tiếp nhé.")
    
    # Gọi module learning để gửi từ ngay (nếu muốn)
    from logic import learning
    learning.send_next_word(uid, state, cache)

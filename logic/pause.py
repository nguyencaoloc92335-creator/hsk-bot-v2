import re
import time
from services import fb_service
import database
from logic import common

# Định nghĩa các loại nghỉ
TYPE_INDEFINITE = "INDEFINITE" # Không thời hạn
TYPE_FIXED = "FIXED"           # Có thời hạn
TYPE_DND = "DND"               # Không làm phiền

def show_pause_menu(uid, state, cache):
    """Hiển thị Menu 3 chế độ nghỉ"""
    msg = (
        "😴 **CHỌN CHẾ ĐỘ NGHỈ**\n\n"
        "1️⃣ **Nghỉ tự do**: Mình sẽ nhắc bạn quay lại mỗi 30 phút.\n"
        "2️⃣ **Nghỉ giải lao**: Bạn đặt giờ (VD: 20p). Mình sẽ nhắc lúc giữa giờ (10p) và khi hết giờ.\n"
        "3️⃣ **Không làm phiền**: Im lặng tuyệt đối trong thời gian bạn chọn.\n\n"
        "👇 Chọn bên dưới hoặc gõ `Hủy` để học tiếp."
    )
    buttons = ["Nghỉ tự do", "Nghỉ giải lao", "Không làm phiền"]
    
    # Đặt trạng thái để router biết đang ở menu nghỉ
    state["mode"] = "PAUSE_MENU" 
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, msg, buttons=buttons)

def handle_pause_input(uid, text, state, cache):
    """
    Xử lý đầu vào khi user đang ở trong Menu Nghỉ hoặc 
    đang được yêu cầu nhập thời gian.
    """
    msg = text.lower().strip()
    
    # 1. Xử lý lệnh Hủy / Tiếp tục
    if msg in ["hủy", "tiếp", "học tiếp", "cancel", "resume"]:
        resume(uid, state, cache)
        return

    # 2. Xử lý các nút bấm Menu
    if "tự do" in msg or "không thời hạn" in msg:
        start_indefinite_pause(uid, state, cache)
        return

    if "giải lao" in msg or "có thời hạn" in msg:
        # Chuyển sang trạng thái chờ nhập thời gian cho FIXED
        state["mode"] = "PAUSE_WAIT_TIME_FIXED"
        database.save_user_state(uid, state, cache)
        fb_service.send_text(uid, "⏳ Bạn muốn nghỉ bao lâu?\n(Gõ VD: `15p`, `30 phút`, `1 tiếng`...)")
        return

    if "không làm phiền" in msg or "dnd" in msg:
        # Chuyển sang trạng thái chờ nhập thời gian cho DND
        state["mode"] = "PAUSE_WAIT_TIME_DND"
        database.save_user_state(uid, state, cache)
        fb_service.send_text(uid, "🤫 Chế độ Không làm phiền.\nBạn muốn mình im lặng trong bao lâu?\n(Gõ VD: `30p`, `2h`...)")
        return

    # 3. Xử lý nhập thời gian (Khi đang chờ)
    if state["mode"] in ["PAUSE_WAIT_TIME_FIXED", "PAUSE_WAIT_TIME_DND"]:
        duration = parse_duration(msg)
        if duration > 0:
            if state["mode"] == "PAUSE_WAIT_TIME_FIXED":
                start_fixed_pause(uid, state, cache, duration, msg)
            else:
                start_dnd_pause(uid, state, cache, duration, msg)
        else:
            fb_service.send_text(uid, "⚠️ Định dạng thời gian chưa đúng.\nHãy gõ số + đơn vị (VD: 15p, 1h).")
        return

    # Nếu gõ linh tinh khi đang ở Menu
    fb_service.send_text(uid, "Vui lòng chọn chế độ nghỉ hoặc gõ thời gian.", 
                         buttons=["Nghỉ tự do", "Nghỉ giải lao", "Không làm phiền"])

# --- CÁC HÀM KHỞI ĐỘNG CHẾ ĐỘ NGHỈ ---

def start_indefinite_pause(uid, state, cache):
    """Chế độ 1: Nghỉ không thời hạn (Nhắc mỗi 30p)"""
    state["mode"] = "PAUSED"
    state["pause_info"] = {
        "type": TYPE_INDEFINITE,
        "start_at": common.get_ts(),
        "last_remind": common.get_ts()
    }
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, "👌 Ok, nghỉ thoải mái nhé.\nMỗi 30 phút mình sẽ hỏi thăm bạn một lần.", buttons=["Học tiếp"])

def start_fixed_pause(uid, state, cache, duration, time_str):
    """Chế độ 2: Nghỉ có thời hạn (Nhắc tại n/2)"""
    state["mode"] = "PAUSED"
    state["pause_info"] = {
        "type": TYPE_FIXED,
        "start_at": common.get_ts(),
        "duration": duration,
        "end_at": common.get_ts() + duration,
        "halfway_reminded": False # Cờ đánh dấu đã nhắc giữa giờ chưa
    }
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, f"⏳ Ok, nghỉ giải lao **{time_str}**.\nMình sẽ gọi khi được một nửa thời gian nhé.", buttons=["Học tiếp"])

def start_dnd_pause(uid, state, cache, duration, time_str):
    """Chế độ 3: Không làm phiền (Im lặng tuyệt đối)"""
    state["mode"] = "PAUSED"
    state["pause_info"] = {
        "type": TYPE_DND,
        "start_at": common.get_ts(),
        "end_at": common.get_ts() + duration
    }
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, f"🤫 Đã bật DND trong **{time_str}**.\nMình sẽ không làm phiền cho đến khi hết giờ.", buttons=["Hủy DND"])

def resume(uid, state, cache):
    """Hủy nghỉ, quay lại học"""
    if state.get("mode") == "IDLE":
        fb_service.send_text(uid, "Gõ 'Bắt đầu' để học nhé.", buttons=["Bắt đầu"])
        return

    state["mode"] = "AUTO" 
    state["pause_info"] = None
    state["waiting"] = False 
    
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, "👋 Welcome back! Học tiếp thôi nào.")
    
    from logic import learning
    learning.send_next_word(uid, state, cache)

# --- UTILS ---
def parse_duration(text):
    """Chuyển đổi text (15p, 1h) thành giây"""
    match = re.search(r'(\d+)\s*(p|phút|m|h|giờ|tiếng)', text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit in ['h', 'giờ', 'tiếng']:
            return amount * 3600
        else: # p, phút, m
            return amount * 60
    return 0

import time
from services import fb_service
import database
from logic import common

# Các hằng số định danh loại nghỉ
PAUSE_TYPE_FIXED = "FIXED"         # Nghỉ có hẹn giờ (30p)
PAUSE_TYPE_DND = "DND"             # Không làm phiền (Im lặng tuyệt đối)

def show_pause_menu(uid, state, cache):
    """Hiển thị 3 nút chọn chế độ nghỉ"""
    msg = (
        "😴 **CHẾ ĐỘ NGHỈ NGƠI**\n"
        "Bạn muốn nghỉ theo cách nào?\n\n"
        "1️⃣ **Nghỉ 30 phút**: Mình sẽ canh giờ và gọi bạn dậy.\n"
        "2️⃣ **Không làm phiền**: Mình sẽ im lặng cho đến khi bạn gọi.\n"
        "3️⃣ **Học tiếp**: Quay lại bài học ngay."
    )
    # 3 Nút chức năng
    buttons = ["Nghỉ 30p", "Không làm phiền", "Học tiếp"]
    
    # Không đổi mode ngay, chỉ gửi menu để user chọn
    fb_service.send_text(uid, msg, buttons=buttons)

def handle_pause_selection(uid, text, state, cache):
    """Xử lý sự kiện khi người dùng bấm nút trong menu nghỉ"""
    msg = text.lower().strip()
    
    # 1. XỬ LÝ NGHỈ 30 PHÚT
    if "30" in msg or "ngắn" in msg:
        duration = 1800 # 30 phút = 1800s
        state["mode"] = "PAUSED"
        state["pause_info"] = {
            "type": PAUSE_TYPE_FIXED,
            "start_at": common.get_ts(),
            "end_at": common.get_ts() + duration,
            "last_remind": common.get_ts()
        }
        database.save_user_state(uid, state, cache)
        fb_service.send_text(uid, "👌 Ok, nghỉ 30 phút nhé. 30p nữa mình gọi!", buttons=["Học tiếp"])
        return

    # 2. XỬ LÝ KHÔNG LÀM PHIỀN (DND)
    if "không làm phiền" in msg or "dnd" in msg or "im lặng" in msg:
        state["mode"] = "PAUSED"
        state["pause_info"] = {
            "type": PAUSE_TYPE_DND,
            "start_at": common.get_ts(),
            "end_at": 0, # Không có thời gian kết thúc
            "last_remind": common.get_ts()
        }
        database.save_user_state(uid, state, cache)
        fb_service.send_text(uid, "🤫 Ok, chế độ **Không làm phiền** đã bật.\nKhi nào rảnh, hãy gõ **'Tiếp'** để học lại nhé.", buttons=["Học tiếp"])
        return

    # 3. XỬ LÝ HỌC TIẾP (Resume)
    if msg in ["học tiếp", "tiếp", "resume", "hủy"]:
        resume(uid, state, cache)
        return

    # Nếu không khớp nút nào -> Hiện lại menu
    show_pause_menu(uid, state, cache)

def resume(uid, state, cache):
    """Hàm quay lại học (Dùng chung cho cả Router và Main)"""
    # Nếu đang IDLE thì chỉ báo bắt đầu
    if state.get("mode") == "IDLE":
        fb_service.send_text(uid, "👋 Bạn đang rảnh mà. Gõ 'Bắt đầu' để học nhé.", buttons=["Bắt đầu"])
        return

    # Khôi phục trạng thái
    state["mode"] = "AUTO" 
    state["pause_info"] = None
    state["waiting"] = False 
    state["next_time"] = 0 
    
    database.save_user_state(uid, state, cache)
    fb_service.send_text(uid, "👋 Mừng bạn quay lại! Chiến tiếp nào.")
    
    # Gọi ngay từ vựng tiếp theo
    from logic import learning
    learning.send_next_word(uid, state, cache)

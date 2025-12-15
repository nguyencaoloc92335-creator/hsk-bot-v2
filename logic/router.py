# Import đầy đủ các module chức năng
from logic import common, learning, quiz, pause, guide, selection, menu
from services import ai_service, fb_service
import database

# ĐỊNH NGHĨA LỆNH
CMD_START = ["bắt đầu", "start", "học"]
CMD_RESET = ["reset", "học lại", "xóa"]
CMD_PAUSE = ["nghỉ", "stop", "pause"]
CMD_RESUME = ["tiếp", "tiếp tục", "học tiếp"]
CMD_LIST = ["danh sách", "kho", "list", "thống kê"] # Lệnh gọi Menu
CMD_MENU = ["menu", "help", "hướng dẫn", "hdsd", "lệnh"]
CMD_CREATE_LIST = ["tạo kho", "lọc từ", "chọn từ"]

def process_message(uid, text, cache):
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot đang ngủ (0h-6h).")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    
    # Cập nhật thời gian tương tác
    state["last_interaction"] = common.get_ts()
    database.save_user_state(uid, state, cache) 

    mode = state.get("mode", "IDLE")

    # --- 1. ƯU TIÊN: ĐIỀU HƯỚNG THEO TRẠNG THÁI (MODE) ---
    # Nếu đang trong quy trình Tạo Kho (Selection)
    if mode.startswith("SELECT_"):
        if mode == selection.STATE_ASK_SOURCE:
            selection.handle_source_selection(uid, text, state, cache); return
        if mode == selection.STATE_BROWSING:
            selection.handle_browsing_decision(uid, text, state, cache); return
        if mode == selection.STATE_NAMING:
            selection.handle_naming(uid, text, state, cache); return
        if mode == selection.STATE_CONFIRM_SAVE:
            selection.handle_save_confirmation(uid, text, state, cache); return

    # Nếu đang học (Auto Reply)
    if mode == "AUTO" and state.get("waiting"): 
        learning.handle_auto_reply(uid, text, state, cache); return
    
    # Nếu đang thi (Quiz)
    if mode == "QUIZ": 
        quiz.handle_answer(uid, text, state, cache); return

    # --- 2. XỬ LÝ LỆNH ĐIỀU KHIỂN (COMMANDS) ---
    
    # Nhóm lệnh Menu & Hướng dẫn
    if msg in CMD_MENU:
        guide_content = guide.get_full_guide() 
        fb_service.send_text(uid, guide_content, buttons=["Bắt đầu", "Danh sách", "Tạo kho"])
        return

    # Nhóm lệnh Danh sách & Chọn kho (GỌI MODULE MENU)
    if msg in CMD_LIST:
        menu.handle_show_stats(uid, state, cache); return
        
    if msg.startswith("chọn") and "từ" not in msg: # Tránh nhầm lệnh "chọn từ"
        menu.handle_select_source(uid, text, state, cache); return

    # Nhóm lệnh Tạo kho (GỌI MODULE SELECTION)
    if msg in CMD_CREATE_LIST:
        selection.start_creation_flow(uid, state, cache); return

    # Nhóm lệnh Học tập
    if msg in CMD_START:
        state["mode"] = "AUTO"; state["session"] = []
        learning.send_next_word(uid, state, cache); return

    if msg in CMD_RESUME:
        if mode == "PAUSED": pause.resume(uid, state, cache); return
        if mode == "IDLE": fb_service.send_text(uid, "Gõ 'Bắt đầu' để học nhé.", buttons=["Bắt đầu"]); return

    # Nhóm lệnh Tiện ích (Pause, Reset)
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20:
        pause.handle_pause(uid, text, state, cache); return

    if msg in CMD_RESET:
        # Reset nhưng giữ lại các fields đã chọn
        s_new = {
            "user_id": uid, 
            "mode": "IDLE", 
            "learned": [], 
            "session": [], 
            "fields": state.get("fields", ["HSK1"]), 
            "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0},
            "custom_learn": {"active": False, "queue": []}
        }
        database.save_user_state(uid, s_new, cache)
        fb_service.send_text(uid, "🔄 Đã Reset toàn bộ tiến độ.", buttons=["Bắt đầu"]); return

    # --- 3. CHAT BOT (FALLBACK) ---
    # Nếu không trúng lệnh nào -> Chat AI
    fb_service.send_text(uid, ai_service.chat_reply(text), buttons=["Menu"])

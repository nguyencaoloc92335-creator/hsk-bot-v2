# Import tất cả các module chức năng đã tách biệt
from logic import common, learning, quiz, pause, selection, menu, system
from services import ai_service, fb_service
import database

# ĐỊNH NGHĨA DANH SÁCH LỆNH
CMD_START = ["bắt đầu", "start", "học"]
CMD_RESUME = ["tiếp", "tiếp tục", "học tiếp"]
CMD_PAUSE = ["nghỉ", "stop", "pause"]
CMD_RESET = ["reset", "học lại", "xóa"]
CMD_MENU = ["menu", "help", "hướng dẫn", "hdsd", "lệnh"]
CMD_LIST = ["danh sách", "kho", "list", "thống kê"]
CMD_CREATE_LIST = ["tạo kho", "lọc từ", "chọn từ"]

def process_message(uid, text, cache):
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot đang ngủ (0h-6h).")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    
    # Cập nhật thời gian tương tác cuối
    state["last_interaction"] = common.get_ts()
    database.save_user_state(uid, state, cache) 

    mode = state.get("mode", "IDLE")

    # ======================================================
    # PHẦN 1: ƯU TIÊN ĐIỀU HƯỚNG THEO TRẠNG THÁI (MODE)
    # ======================================================
    
    # 1. Đang trong quy trình Tạo Kho (Module Selection)
    if mode.startswith("SELECT_"):
        if mode == selection.STATE_ASK_SOURCE:
            selection.handle_source_selection(uid, text, state, cache); return
        if mode == selection.STATE_BROWSING:
            selection.handle_browsing_decision(uid, text, state, cache); return
        if mode == selection.STATE_NAMING:
            selection.handle_naming(uid, text, state, cache); return
        if mode == selection.STATE_CONFIRM_SAVE:
            selection.handle_save_confirmation(uid, text, state, cache); return

    # 2. Đang Học (Module Learning)
    if mode == "AUTO" and state.get("waiting"): 
        learning.handle_auto_reply(uid, text, state, cache); return
    
    # 3. Đang Thi (Module Quiz)
    if mode == "QUIZ": 
        quiz.handle_answer(uid, text, state, cache); return

    # ======================================================
    # PHẦN 2: XỬ LÝ LỆNH ĐIỀU KHIỂN (COMMANDS)
    # ======================================================

    # Nhóm: Menu & Hướng dẫn (Module System)
    if msg in CMD_MENU:
        system.handle_menu_guide(uid, text, state, cache); return

    # Nhóm: Danh sách & Chọn kho (Module Menu)
    if msg in CMD_LIST:
        menu.handle_show_stats(uid, state, cache); return
        
    if msg.startswith("chọn") and "từ" not in msg:
        menu.handle_select_source(uid, text, state, cache); return

    # Nhóm: Tạo kho riêng (Module Selection)
    if msg in CMD_CREATE_LIST:
        selection.start_creation_flow(uid, state, cache); return

    # Nhóm: Reset (Module System)
    if msg in CMD_RESET:
        system.handle_reset(uid, state, cache); return

    # Nhóm: Học tập (Module Learning)
    if msg in CMD_START:
        state["mode"] = "AUTO"; state["session"] = []
        learning.send_next_word(uid, state, cache); return

    # Nhóm: Tiếp tục / Tạm dừng (Module Pause)
    if msg in CMD_RESUME:
        if mode == "PAUSED": pause.resume(uid, state, cache); return
        if mode == "IDLE": fb_service.send_text(uid, "Gõ 'Bắt đầu' để học nhé.", buttons=["Bắt đầu"]); return

    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20:
        pause.handle_pause(uid, text, state, cache); return

    # ======================================================
    # PHẦN 3: FALLBACK (CHAT AI)
    # ======================================================
    fb_service.send_text(uid, ai_service.chat_reply(text), buttons=["Menu"])

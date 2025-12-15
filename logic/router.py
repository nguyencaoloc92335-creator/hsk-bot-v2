from logic import common, learning, quiz, pause, selection, menu, system
from services import ai_service, fb_service
import database

CMD_START = ["bắt đầu", "start", "học"]
CMD_RESUME = ["tiếp", "tiếp tục", "học tiếp", "hủy"]
CMD_PAUSE = ["nghỉ", "stop", "pause", "bận"]
CMD_RESET = ["reset", "học lại", "xóa"]
CMD_MENU = ["menu", "help", "hướng dẫn", "hdsd", "lệnh"]
CMD_LIST = ["danh sách", "kho", "list", "thống kê"]
CMD_CREATE_LIST = ["tạo kho", "lọc từ", "chọn từ"]

def process_message(uid, text, cache):
    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    
    state["last_interaction"] = common.get_ts()
    database.save_user_state(uid, state, cache) 

    mode = state.get("mode", "IDLE")

    # ======================================================
    # PHẦN 1: ƯU TIÊN ĐIỀU HƯỚNG THEO TRẠNG THÁI
    # ======================================================
    
    # 1. Đang tương tác với Menu Nghỉ hoặc Đang chờ nhập thời gian nghỉ
    if mode.startswith("PAUSE_"): 
        pause.handle_pause_input(uid, text, state, cache); return

    # 2. Đang chọn kho (Selection)
    if mode.startswith("SELECT_"):
        if mode == selection.STATE_ASK_SOURCE:
            selection.handle_source_selection(uid, text, state, cache); return
        if mode == selection.STATE_BROWSING:
            selection.handle_browsing_decision(uid, text, state, cache); return
        if mode == selection.STATE_NAMING:
            selection.handle_naming(uid, text, state, cache); return
        if mode == selection.STATE_CONFIRM_SAVE:
            selection.handle_save_confirmation(uid, text, state, cache); return

    # 3. Đang Học
    if mode == "AUTO" and state.get("waiting"): 
        learning.handle_auto_reply(uid, text, state, cache); return
    
    # 4. Đang Thi
    if mode == "QUIZ": 
        quiz.handle_answer(uid, text, state, cache); return

    # ======================================================
    # PHẦN 2: XỬ LÝ LỆNH
    # ======================================================

    if msg in CMD_MENU:
        system.handle_menu_guide(uid, text, state, cache); return

    if msg in CMD_LIST:
        menu.handle_show_stats(uid, state, cache); return
        
    if msg.startswith("chọn") and "từ" not in msg:
        menu.handle_select_source(uid, text, state, cache); return

    if msg in CMD_CREATE_LIST:
        selection.start_creation_flow(uid, state, cache); return

    if msg in CMD_RESET:
        system.handle_reset(uid, state, cache); return

    if msg in CMD_START:
        state["mode"] = "AUTO"; state["session"] = []
        learning.send_next_word(uid, state, cache); return

    if msg in CMD_RESUME:
        pause.resume(uid, state, cache); return

    # Lệnh "Nghỉ" -> Hiện Menu
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20:
        pause.show_pause_menu(uid, state, cache); return

    # ======================================================
    # PHẦN 3: FALLBACK
    # ======================================================
    fb_service.send_text(uid, ai_service.chat_reply(text), buttons=["Menu"])

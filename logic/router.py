from logic import common, learning, quiz, pause, guide, selection # Import thêm selection
from services import ai_service, fb_service
import database

CMD_START = ["bắt đầu", "start", "học"]
CMD_RESET = ["reset", "học lại", "xóa"]
CMD_PAUSE = ["nghỉ", "stop", "pause"]
CMD_RESUME = ["tiếp", "tiếp tục", "học tiếp"]
CMD_LIST = ["danh sách", "kho", "list", "thống kê"]
CMD_MENU = ["menu", "help", "hướng dẫn", "hdsd", "lệnh"]
CMD_CREATE_LIST = ["tạo kho", "lọc từ", "chọn từ"] # Lệnh mới

def process_message(uid, text, cache):
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot đang ngủ (0h-6h).")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    
    state["last_interaction"] = common.get_ts()
    database.save_user_state(uid, state, cache) 

    mode = state.get("mode", "IDLE")

    # --- 1. ĐIỀU HƯỚNG CÁC TRẠNG THÁI "TẠO KHO" ---
    if mode == selection.STATE_ASK_SOURCE:
        selection.handle_source_selection(uid, text, state, cache); return
    if mode == selection.STATE_BROWSING:
        selection.handle_browsing_decision(uid, text, state, cache); return
    if mode == selection.STATE_NAMING:
        selection.handle_naming(uid, text, state, cache); return
    if mode == selection.STATE_CONFIRM_SAVE:
        selection.handle_save_confirmation(uid, text, state, cache); return
    # -----------------------------------------------

    if msg in CMD_MENU:
        # (Giữ nguyên logic menu cũ)
        guide_content = guide.get_full_guide() 
        fb_service.send_text(uid, guide_content, buttons=["Bắt đầu", "Tạo kho"])
        return
        
    if msg in CMD_CREATE_LIST:
        selection.start_creation_flow(uid, state, cache); return

    if msg.startswith("chọn") and "từ" not in msg: # Tránh nhầm lệnh "chọn từ"
        arg = msg.replace("chọn", "").strip() # KHÔNG upper() ngay để giữ case
        
        # --- FIX LỖI CHUYÊN NGÀNH TẠI ĐÂY ---
        # Chuẩn hóa đầu vào: thay khoảng trắng bằng gạch dưới nếu cần
        # Ví dụ: "Chuyên ngành" -> "Chuyên_ngành"
        # Logic: Tìm field trong DB gần giống nhất
        
        stats = database.get_all_fields_stats()
        real_fields = {s[0].lower().replace("_", " ").replace(" ", ""): s[0] for s in stats}
        
        # Xử lý input người dùng: lowercase + xóa dấu cách thừa
        raw_input = arg.lower().replace("_", " ").replace(" ", "")
        
        if raw_input == "tấtcả" or raw_input == "all":
             state["fields"] = [s[0] for s in stats]
             reply = "✅ Đã chọn TẤT CẢ."
        elif raw_input in real_fields:
             correct_field = real_fields[raw_input]
             state["fields"] = [correct_field]
             reply = f"✅ Đã chọn kho: {correct_field}."
        else:
             # Fallback cho trường hợp chọn nhiều (VD: Chọn HSK1 HSK2)
             # Logic cũ nhưng cải tiến
             args = arg.upper().replace(",", " ").split()
             # (Đoạn này bạn có thể làm kỹ hơn nếu cần, tạm thời để đơn giản)
             state["fields"] = args 
             reply = f"✅ Đã chọn: {arg}."
             
        # Tắt chế độ Custom Learn nếu người dùng chọn kho đại trà
        state["custom_learn"]["active"] = False
        
        database.save_user_state(uid, state, cache)
        fb_service.send_text(uid, f"{reply} Tiến độ giữ nguyên.", buttons=["Tiếp tục"])
        return

    # ... (Giữ nguyên các logic Start, Reset, Resume, Pause...)
    if msg in CMD_START:
        state["mode"] = "AUTO"; state["session"] = []
        learning.send_next_word(uid, state, cache); return

    # ... (Giữ nguyên phần xử lý logic học)
    if mode == "AUTO" and state.get("waiting"): learning.handle_auto_reply(uid, text, state, cache); return
    if mode == "REVIEWING": learning.handle_review_confirm(uid, text, state, cache); return
    
    # ... (Giữ nguyên phần Quiz và Chat AI)
    if mode == "QUIZ": from logic import quiz; quiz.handle_answer(uid, text, state, cache); return

    fb_service.send_text(uid, ai_service.chat_reply(text), buttons=["Menu"])

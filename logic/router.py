from logic import common, learning, quiz, pause, guide # <--- Nhớ import guide
from services import ai_service, fb_service
import database

# ... (Các danh sách lệnh giữ nguyên) ...
CMD_START = ["bắt đầu", "start", "học"]
CMD_RESET = ["reset", "học lại", "xóa"]
CMD_PAUSE = ["nghỉ", "stop", "pause"]
CMD_RESUME = ["tiếp", "tiếp tục", "học tiếp"]
CMD_LIST = ["danh sách", "kho", "list", "thống kê"]

def process_message(uid, text, cache):
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot đang ngủ (0h-6h).")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    mode = state.get("mode", "IDLE")

    # ===============================================
    # 1. GỌI HƯỚNG DẪN TỪ FILE RIÊNG (Clean Code)
    # ===============================================
    if msg in ["menu", "help", "hướng dẫn", "hdsd", "lệnh"]:
        # Gọi hàm lấy nội dung từ file logic/guide.py
        guide_content = guide.get_full_guide() 
        fb_service.send_text(uid, guide_content)
        return
    # ===============================================

    # ... (Các phần logic bên dưới giữ nguyên như code cũ) ...
    
    # Lệnh Pause/Resume
    if msg in CMD_RESUME:
        if mode == "PAUSED": pause.resume(uid, state, cache); return
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20:
        pause.handle_pause(uid, text, state, cache); return

    # Lệnh Danh sách
    if msg in CMD_LIST:
        stats = database.get_all_fields_stats()
        if not stats: fb_service.send_text(uid, "📭 Kho trống."); return
        reply = "📚 **KHO TỪ:**\n" + "\n".join([f"- {f}: {c}" for f,c in stats])
        fb_service.send_text(uid, reply); return

    # Lệnh Chọn trường
    if msg.startswith("chọn"):
        arg = msg.replace("chọn", "").strip().upper()
        if arg in ["ALL", "TẤT CẢ"]:
            stats = database.get_all_fields_stats()
            state["fields"] = [row[0] for row in stats]
            state["session"]=[]; state["mode"]="IDLE"
            database.save_user_state(uid, state, cache)
            fb_service.send_text(uid, "✅ Đã chọn TẤT CẢ. Gõ 'Bắt đầu'.")
            return

        arg_list = arg.replace(",", " ").split()
        if arg_list: 
            state["fields"]=arg_list; state["session"]=[]; state["mode"]="IDLE"
            database.save_user_state(uid, state, cache)
            fb_service.send_text(uid, "✅ Đã chọn kho. Gõ 'Bắt đầu'.")
            return

    # Lệnh Start / Reset
    if msg in CMD_START:
        state["mode"] = "AUTO"; state["session"] = []
        learning.send_next_word(uid, state, cache); return

    if msg in CMD_RESET:
        s_new = {"user_id": uid, "mode": "IDLE", "learned": [], "session": [], "fields": state.get("fields", ["HSK1"]), "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}}
        database.save_user_state(uid, s_new, cache)
        fb_service.send_text(uid, "🔄 Đã Reset."); return

    # Xử lý State Machine
    if mode == "AUTO" and state.get("waiting"): learning.handle_auto_reply(uid, text, state, cache); return
    if mode == "REVIEWING": learning.handle_review_confirm(uid, text, state, cache); return
    if mode == "PRE_QUIZ":
        rem = state.get("next_time",0) - common.get_ts()
        if rem > 0: fb_service.send_text(uid, f"⏳ Còn {int(rem/60)} phút nữa là kiểm tra."); return
        from logic import quiz; quiz.start_quiz_level(uid, state, cache, 1); return
    if mode == "QUIZ": from logic import quiz; quiz.handle_answer(uid, text, state, cache); return

    # Chat
    fb_service.send_text(uid, ai_service.chat_reply(text))

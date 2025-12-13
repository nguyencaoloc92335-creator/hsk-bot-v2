from logic import common, learning, quiz, pause, guide
from services import ai_service, fb_service
import database

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

    # 1. HƯỚNG DẪN
    if msg in ["menu", "help", "hướng dẫn", "hdsd", "lệnh"]:
        guide_content = guide.get_full_guide() 
        fb_service.send_text(uid, guide_content)
        return

    # 2. XỬ LÝ LỆNH CƠ BẢN
    if msg in CMD_RESUME:
        if mode == "PAUSED": pause.resume(uid, state, cache); return
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20:
        pause.handle_pause(uid, text, state, cache); return

    if msg in CMD_LIST:
        stats = database.get_all_fields_stats()
        if not stats: fb_service.send_text(uid, "📭 Kho trống."); return
        reply = "📚 **KHO TỪ:**\n" + "\n".join([f"- {f}: {c}" for f,c in stats])
        fb_service.send_text(uid, reply); return

    if msg.startswith("chọn"):
        arg = msg.replace("chọn", "").strip().upper()
        if arg in ["ALL", "TẤT CẢ"]:
            stats = database.get_all_fields_stats()
            state["fields"] = [row[0] for row in stats]
            database.save_user_state(uid, state, cache)
            fb_service.send_text(uid, "✅ Đã chọn TẤT CẢ. Tiến độ được giữ nguyên.")
            return

        arg_list = arg.replace(",", " ").split()
        if arg_list: 
            state["fields"] = arg_list
            database.save_user_state(uid, state, cache)
            fb_service.send_text(uid, f"✅ Đã chọn: {', '.join(arg_list)}. Tiến độ được giữ nguyên.")
            return

    if msg in CMD_START:
        state["mode"] = "AUTO"; state["session"] = []
        learning.send_next_word(uid, state, cache); return

    if msg in CMD_RESET:
        s_new = {"user_id": uid, "mode": "IDLE", "learned": [], "session": [], "fields": state.get("fields", ["HSK1"]), "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}}
        database.save_user_state(uid, s_new, cache)
        fb_service.send_text(uid, "🔄 Đã Reset."); return

    # 3. XỬ LÝ TRẠNG THÁI HỌC (AUTO/REVIEW)
    if mode == "AUTO" and state.get("waiting"): learning.handle_auto_reply(uid, text, state, cache); return
    if mode == "REVIEWING": learning.handle_review_confirm(uid, text, state, cache); return
    
    # 4. XỬ LÝ NGHỈ GIẢI LAO (PRE_QUIZ / SHORT_BREAK)
    # Đây là đoạn logic quan trọng giúp Bot "tự tỉnh" khi bạn nhắn tin
    if mode in ["PRE_QUIZ", "SHORT_BREAK"]:
        rem = state.get("next_time",0) - common.get_ts()
        
        # Nếu chưa hết giờ
        if rem > 0: 
            fb_service.send_text(uid, f"⏳ Còn {int(rem/60)+1} phút nữa là học tiếp nha.")
            return
            
        # Nếu ĐÃ HẾT GIỜ (rem <= 0) mà Bot chưa tự gọi -> Kích hoạt luôn
        else:
            if mode == "SHORT_BREAK":
                fb_service.send_text(uid, "🔔 **HẾT GIỜ NGHỈ!**\nHọc tiếp luôn nhé.")
                state["mode"] = "AUTO"
                state["waiting"] = False
                database.save_user_state(uid, state, cache)
                learning.send_next_word(uid, state, cache)
                return
                
            if mode == "PRE_QUIZ":
                fb_service.send_text(uid, "🔔 **VÀO THI THÔI!**")
                quiz.start_quiz_level(uid, state, cache, 1)
                return
        
    if mode == "QUIZ": from logic import quiz; quiz.handle_answer(uid, text, state, cache); return

    fb_service.send_text(uid, ai_service.chat_reply(text))

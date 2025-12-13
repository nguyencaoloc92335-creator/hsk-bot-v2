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

    # Lệnh Chọn trường (ĐÃ SỬA: KHÔNG RESET TIẾN ĐỘ)
    if msg.startswith("chọn"):
        arg = msg.replace("chọn", "").strip().upper()
        
        # Trường hợp 1: Chọn TẤT CẢ
        if arg in ["ALL", "TẤT CẢ"]:
            stats = database.get_all_fields_stats()
            state["fields"] = [row[0] for row in stats]
            # Lưu ý: Đã bỏ dòng reset session để giữ tiến độ học
            database.save_user_state(uid, state, cache)
            fb_service.send_text(uid, "✅ Đã chọn TẤT CẢ kho.\nTiến độ học hiện tại được GIỮ NGUYÊN. Bot sẽ lấy từ mới từ tất cả các kho.")
            return

        # Trường hợp 2: Chọn kho cụ thể (VD: Chọn HSK1 Chuyên_Ngành)
        arg_list = arg.replace(",", " ").split()
        if arg_list: 
            state["fields"] = arg_list
            # Lưu ý: Đã bỏ dòng reset session để giữ tiến độ học
            database.save_user_state(uid, state, cache)
            fields_str = ", ".join(arg_list)
            fb_service.send_text(uid, f"✅ Đã cập nhật kho: {fields_str}.\nTiến độ học hiện tại được GIỮ NGUYÊN.")
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
    
    # Xử lý PRE_QUIZ và SHORT_BREAK (nếu người dùng chat trong lúc nghỉ)
    if mode in ["PRE_QUIZ", "SHORT_BREAK"]:
        rem = state.get("next_time",0) - common.get_ts()
        if rem > 0: 
            # Có thể báo thời gian còn lại hoặc để Bot im lặng (ở đây để báo giờ cho tiện theo dõi)
            fb_service.send_text(uid, f"⏳ Còn {int(rem/60)} phút nữa là học tiếp nha.")
            return
        # Nếu hết giờ mà Cronjob chưa quét tới thì có thể kích hoạt luôn tại đây (tùy chọn)
        
    if mode == "QUIZ": from logic import quiz; quiz.handle_answer(uid, text, state, cache); return

    # Chat xã giao (khi không lọt vào các lệnh trên)
    fb_service.send_text(uid, ai_service.chat_reply(text))

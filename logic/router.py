from logic import common, learning, quiz, pause
from services import ai_service, fb_service
import database

# Danh sách lệnh
CMD_START = ["bắt đầu", "start", "học"]
CMD_RESET = ["reset", "học lại", "xóa"]
CMD_PAUSE = ["nghỉ", "stop", "pause"]
CMD_RESUME = ["tiếp", "tiếp tục", "học tiếp"]
CMD_LIST = ["danh sách", "kho", "list", "thống kê"]

def process_message(uid, text, cache):
    if common.is_sleep_mode():
        fb_service.send_text(uid, "💤 Bot đang ngủ (0h-6h). Mai quay lại nhé!")
        return

    msg = text.lower().strip()
    state = database.get_user_state(uid, cache)
    mode = state.get("mode", "IDLE")

    # 1. MENU HƯỚNG DẪN CHI TIẾT
    if msg in ["menu", "help", "hướng dẫn", "lệnh"]:
        guide_msg = (
            "📘 **HƯỚNG DẪN SỬ DỤNG BOT** 📘\n"
            "──────────────────\n\n"
            "1️⃣ **CHỌN KHO TỪ**\n"
            "• Gõ `Danh sách`: Xem các kho từ hiện có (HSK1, HSK2...).\n"
            "• Gõ `Chọn HSK1`: Để học kho HSK1.\n"
            "• Gõ `Chọn Tất cả`: Để học trộn tất cả các kho.\n\n"
            "2️⃣ **HỌC TẬP**\n"
            "• Gõ `Bắt đầu`: Bot sẽ gửi thẻ từ vựng + Audio.\n"
            "• Gõ lại từ đó (hoặc `OK`) để xác nhận đã nhớ.\n"
            "• Bot sẽ tự ôn lại cho bạn sau **9 phút**.\n\n"
            "3️⃣ **KIỂM TRA (QUIZ)**\n"
            "• Học đủ **6 từ**, Bot sẽ tự động mở bài kiểm tra.\n"
            "• Phải trả lời đúng hết mới được qua màn!\n\n"
            "4️⃣ **TIỆN ÍCH KHÁC**\n"
            "• `Nghỉ`: Tạm dừng Bot (Bot sẽ nhắc bạn sau).\n"
            "• `Tiếp`: Quay lại học sau khi nghỉ.\n"
            "• `Reset`: Xóa hết dữ liệu để học lại từ đầu.\n"
            "──────────────────\n"
            "👉 Gõ **'Bắt đầu'** để thử ngay nhé!"
        )
        fb_service.send_text(uid, guide_msg)
        return

    # 2. CÁC LỆNH KHÁC (Giữ nguyên logic cũ)
    
    # Lệnh Danh sách
    if msg in CMD_LIST:
        stats = database.get_all_fields_stats()
        if not stats:
            fb_service.send_text(uid, "📭 Kho từ vựng đang trống.")
            return
        reply = "📚 **KHO TỪ VỰNG:**\n"
        total = 0
        for field, count in stats:
            reply += f"- **{field}**: {count} từ\n"
            total += count
        reply += f"\n∑ Tổng: {total} từ.\n👉 Gõ **'Chọn [Tên]'** hoặc **'Chọn Tất cả'**."
        fb_service.send_text(uid, reply)
        return

    # Lệnh Chọn trường
    if msg.startswith("chọn") or msg.startswith("select"):
        arg = msg.replace("chọn", "").replace("select", "").strip().upper()
        if arg in ["ALL", "TẤT CẢ", "HẾT", "TOÀN BỘ"]:
            stats = database.get_all_fields_stats()
            all_fields = [row[0] for row in stats]
            state["fields"] = all_fields; state["learned"] = []; state["session"] = []; state["mode"] = "IDLE"
            database.save_user_state(uid, state, cache)
            fb_service.send_text(uid, f"✅ Đã chọn **TẤT CẢ** ({sum(r[1] for r in stats)} từ).\nGõ 'Bắt đầu' để học.")
            return

        requested_fields = arg.replace(",", " ").split()
        if not requested_fields:
            fb_service.send_text(uid, "⚠️ Cú pháp sai. Ví dụ: **Chọn HSK1**")
            return
        state["fields"] = requested_fields; state["learned"] = []; state["session"] = []; state["mode"] = "IDLE"
        database.save_user_state(uid, state, cache)
        fb_service.send_text(uid, f"✅ Đã chọn: **{', '.join(requested_fields)}**.\nGõ 'Bắt đầu' để học.")
        return

    # Lệnh Nghỉ/Tiếp
    if msg in CMD_RESUME:
        if mode == "PAUSED": pause.resume(uid, state, cache); return
    if any(k in msg for k in CMD_PAUSE) and len(msg) < 20:
        pause.handle_pause(uid, text, state, cache); return

    if msg in CMD_START:
        state["mode"] = "AUTO"; state["session"] = []
        learning.send_next_word(uid, state, cache); return

    if msg in CMD_RESET:
        current_fields = state.get("fields", ["HSK1"])
        new_s = {
            "user_id": uid, "mode": "IDLE", "learned": [], "session": [], 
            "next_time": 0, "waiting": False, "fields": current_fields,
            "quiz": {"level": 1, "queue": [], "failed": [], "idx": 0}
        }
        database.save_user_state(uid, new_s, cache)
        fb_service.send_text(uid, "🔄 Đã Reset dữ liệu.")
        return

    # Xử lý State Machine
    if mode == "QUIZ": quiz.handle_answer(uid, text, state, cache); return
    if mode == "AUTO" and state.get("waiting"): learning.handle_auto_reply(uid, text, state, cache); return

    # Chat vui vẻ (Rule Based)
    fb_service.send_text(uid, ai_service.chat_reply(text))
